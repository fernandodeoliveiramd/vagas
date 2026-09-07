import re
import urllib.request
import urllib.parse
import ssl
import logging
import asyncio
from typing import List, Dict, Any, Tuple
from ..database.db import get_jobs, delete_job, update_job, get_db_connection

logger = logging.getLogger(__name__)

# Vagas confirmadas como fechadas nao sao mais apagadas: viram status
# "expirada" (soft-delete). Apagar de verdade e irreversivel e a checagem
# roda sobre HTML de terceiros, sem garantia absoluta - um falso positivo
# some para sempre com o hard delete. Com soft-delete, o pior caso e uma
# vaga aparecer na aba de descartadas por engano, recuperavel com 1 clique.
EXPIRED_STATUS = "expirada"

# So checamos o titulo e os cabecalhos H1 pela frase de encerramento, nao
# a pagina inteira. Rodape, menu e scripts de portais grandes frequentemente
# citam frases como "vaga encerrada" em contextos genericos (ex: um link
# "Ver outras vagas encerradas"), o que gerava falso positivo e apagava
# vaga ativa. Titulo/H1 e onde o portal realmente anuncia que a vaga acabou.
_TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)
_H1_RE = re.compile(r"<h1[^>]*>(.*?)</h1>", re.IGNORECASE | re.DOTALL)
_TAG_RE = re.compile(r"<[^>]+>")

CLOSED_PHRASES = [
    "vaga encerrada",
    "vaga finalizada",
    "processo seletivo encerrado",
    "não aceita mais candidaturas",
    "nao aceita mais candidaturas",
    "esta vaga expirou",
    "vaga expirada",
    "vaga não encontrada",
    "vaga nao encontrada",
    "inscrições encerradas",
    "inscricoes encerradas",
    "no longer accepting applications",
    "oportunidade encerrada",
    "vaga desativada",
    "vaga pausada",
    "conteúdo não encontrado",
    "página não encontrada",
    "job expired",
    "esta vaga não está mais disponível",
    "esta vaga nao esta mais disponivel"
]

# No maximo 8 verificacoes de URL simultaneas. Sem limite, uma varredura
# com centenas de vagas dispara centenas de conexoes ao mesmo tempo contra
# os mesmos poucos portais (LinkedIn, Gupy, Trabalha Brasil...), o que lê
# como um ataque de negacao de servico e derruba a taxa de aceitacao do
# nosso proprio IP nesses sites.
_CONCURRENCY_LIMIT = 8


def _extract_headline_text(html: str) -> str:
    """Extrai apenas o texto de <title> e <h1> - onde o portal de fato
    anuncia que a vaga encerrou - em vez do HTML inteiro."""
    partes = []
    title_match = _TITLE_RE.search(html)
    if title_match:
        partes.append(title_match.group(1))
    partes.extend(_H1_RE.findall(html))
    texto = " ".join(partes)
    return _TAG_RE.sub(" ", texto).lower()


def check_job_url(job: Dict[str, Any]) -> Tuple[int, bool, str]:
    """
    Verifica se a URL da vaga está ativa e sem mensagem de encerramento.
    Retorna: (job_id, is_alive, reason)
    """
    job_id = job.get("id")
    url = job.get("url", "")
    source = job.get("source", "")

    if not url or url.startswith("#") or "example" in url:
        return job_id, False, "URL inválida"

    ctx = ssl.create_default_context()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer": "https://www.google.com/"
    }

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, context=ctx, timeout=8) as resp:
            status_code = resp.status
            if status_code in (404, 410):
                return job_id, False, f"HTTP {status_code}"

            # Ler apenas os primeiros 100KB (o <title>/<h1> ja aparecem bem cedo)
            html_snippet = resp.read(100000).decode('utf-8', errors='ignore')
            headline = _extract_headline_text(html_snippet)

            # Checar mensagens de vaga encerrada, so no titulo/cabecalho
            for phrase in CLOSED_PHRASES:
                if phrase in headline:
                    return job_id, False, f"Encerrada: '{phrase}'"

            return job_id, True, "Ativa"

    except urllib.error.HTTPError as e:
        # Se for 429 (Rate Limit) ou 403 (Cloudflare), mantemos como válida pois a URL existe
        if e.code in (429, 403):
            return job_id, True, f"Ativa (HTTP {e.code})"

        if e.code in (404, 410, 400):
            return job_id, False, f"HTTP {e.code}"

        return job_id, True, f"Ativa (HTTP {e.code})"
    except Exception as e:
        err_str = str(e).lower()
        if "getaddrinfo failed" in err_str:
            return job_id, False, f"Domínio inexistente ({e})"
        return job_id, True, f"Mantida ({e})"

async def verify_and_clean_all_jobs() -> Dict[str, Any]:
    """
    Verifica todas as vagas no banco de dados SQLite e marca como
    "expirada" as que parecem encerradas (soft-delete: nada e apagado
    de verdade, dá pra restaurar pela aba de Descartadas).
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM jobs")
    rows = cursor.fetchall()
    jobs = [dict(row) for row in rows]
    conn.close()

    logger.info(f"[Verifier] Iniciando validação de disponibilidade para {len(jobs)} vagas...")

    semaphore = asyncio.Semaphore(_CONCURRENCY_LIMIT)

    async def check_with_limit(job):
        async with semaphore:
            return await asyncio.to_thread(check_job_url, job)

    tasks = [check_with_limit(j) for j in jobs]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    removed_count = 0
    active_count = 0

    for res in results:
        if isinstance(res, Exception):
            continue
        job_id, is_alive, reason = res
        if not is_alive:
            logger.info(f"[Verifier] Marcando vaga expirada ID {job_id} ({reason})")
            update_job(job_id, {"status": EXPIRED_STATUS})
            removed_count += 1
        else:
            active_count += 1

    logger.info(f"[Verifier] Validação concluída: {active_count} ativas | {removed_count} marcadas como expiradas.")
    return {
        "total_checked": len(jobs),
        "active_jobs": active_count,
        "removed_jobs": removed_count
    }
