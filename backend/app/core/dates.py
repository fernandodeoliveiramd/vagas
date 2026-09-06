"""
Normalizacao de datas de publicacao das vagas.

Os portais devolvem a data em texto relativo ("Ha 3 dias", "Ha 1 semana").
Guardar essa string crua congela a informacao: uma vaga capturada como
"Ha 3 dias" continua dizendo "Ha 3 dias" tres meses depois.

Aqui a string relativa e resolvida contra o instante da captura e
gravada como data absoluta (ISO, YYYY-MM-DD). O texto original nunca
volta a ser reinterpretado.
"""

import re
import unicodedata
from datetime import datetime, timedelta
from typing import Optional

# Textos que nao carregam data nenhuma - viram None e o app cai no
# fallback honesto ("encontrada em", a partir do created_at).
_SEM_DATA = {"", "recente", "none", "null", "nao informado", "n a"}

_UNIDADES = {
    "minuto": timedelta(minutes=1),
    "hora": timedelta(hours=1),
    "dia": timedelta(days=1),
    "semana": timedelta(weeks=1),
    "mes": timedelta(days=30),
    "ano": timedelta(days=365),
}


def _normalizar(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", str(texto)).encode("ASCII", "ignore").decode()
    return re.sub(r"\s+", " ", texto.strip().lower())


def parse_published_at(raw, reference: Optional[datetime] = None) -> Optional[str]:
    """
    Converte a data de publicacao informada pelo portal em ISO (YYYY-MM-DD).

    `reference` e o instante da captura - use datetime.now() na coleta e o
    created_at da vaga ao migrar dados ja gravados.

    Retorna None quando o portal nao informou data utilizavel.
    """
    if raw is None:
        return None

    ref = reference or datetime.now()
    texto = _normalizar(raw)

    if texto in _SEM_DATA:
        return None

    # Ja esta em ISO (YYYY-MM-DD, com ou sem hora)
    iso = re.match(r"^(\d{4})-(\d{2})-(\d{2})", texto)
    if iso:
        return f"{iso.group(1)}-{iso.group(2)}-{iso.group(3)}"

    if "hoje" in texto or "agora" in texto:
        return ref.date().isoformat()
    if "ontem" in texto:
        return (ref - timedelta(days=1)).date().isoformat()

    # "ha 3 dias", "ha 1 semana", "3 semanas atras", "ha cerca de 2 meses"
    relativo = re.search(r"(\d+)\s*(minuto|hora|dia|semana|mes|mese|ano)", texto)
    if relativo:
        quantidade = int(relativo.group(1))
        unidade = relativo.group(2).rstrip("e")  # "mese" -> "mes"
        # Minutos e horas nunca mudam o dia da publicacao na pratica:
        # "ha 2 horas" as 01h nao significa que a vaga saiu ontem.
        if unidade in ("minuto", "hora"):
            return ref.date().isoformat()
        delta = _UNIDADES.get(unidade)
        if delta:
            return (ref - delta * quantidade).date().isoformat()

    # "publicada em 15/06" ou "15/06/2026"
    br = re.search(r"(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?", texto)
    if br:
        dia, mes = int(br.group(1)), int(br.group(2))
        ano_txt = br.group(3)
        if ano_txt:
            ano = int(ano_txt)
            if ano < 100:
                ano += 2000
        else:
            ano = ref.year
        try:
            data = datetime(ano, mes, dia)
            # Sem ano explicito, uma data no futuro so pode ser do ano passado.
            if not ano_txt and data.date() > ref.date():
                data = datetime(ano - 1, mes, dia)
            return data.date().isoformat()
        except ValueError:
            return None

    return None
