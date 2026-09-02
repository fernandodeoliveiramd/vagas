import json
import urllib.request
import ssl
import asyncio
from bs4 import BeautifulSoup

CLOSED_PHRASES = [
    "vaga encerrada", "vaga finalizada", "processo seletivo encerrado",
    "não aceita mais candidaturas", "nao aceita mais candidaturas",
    "esta vaga expirou", "vaga expirada", "vaga não encontrada", "vaga nao encontrada",
    "inscrições encerradas", "inscricoes encerradas", "no longer accepting applications",
    "oportunidade encerrada", "vaga desativada", "vaga pausada", "conteúdo não encontrado",
    "página não encontrada", "404 not found"
]

def check_single_job(job):
    url = job.get("url", "")
    if not url or url.startswith("#") or "example" in url:
        return {"id": job["id"], "title": job["title"], "status": "invalid_url", "is_alive": False}
        
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "pt-BR,pt;q=0.9"
    }

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, context=ctx, timeout=8) as resp:
            status_code = resp.status
            if status_code in (404, 410):
                return {"id": job["id"], "title": job["title"], "status": f"http_{status_code}", "is_alive": False}
                
            html = resp.read().decode('utf-8', errors='ignore').lower()
            
            # Checar frases de vaga encerrada
            for phrase in CLOSED_PHRASES:
                if phrase in html:
                    return {"id": job["id"], "title": job["title"], "status": f"closed_phrase: {phrase}", "is_alive": False}

            return {"id": job["id"], "title": job["title"], "status": "active", "is_alive": True}

    except urllib.error.HTTPError as e:
        return {"id": job["id"], "title": job["title"], "status": f"http_{e.code}", "is_alive": False}
    except Exception as e:
        return {"id": job["id"], "title": job["title"], "status": f"error: {e}", "is_alive": False}

async def main():
    with open('data/jobs.json', 'r', encoding='utf-8') as f:
        data = json.load(f)

    jobs = data.get('jobs', [])
    print(f"Iniciando verificação de {len(jobs)} vagas...")

    tasks = [asyncio.to_thread(check_single_job, j) for j in jobs]
    results = await asyncio.gather(*tasks)

    alive = [r for r in results if r["is_alive"]]
    dead = [r for r in results if not r["is_alive"]]

    print(f"\n==========================================")
    print(f"RELATÓRIO DE DISPONIBILIDADE:")
    print(f"Total Verificado: {len(results)}")
    print(f"Vagas Ativas/Válidas: {len(alive)}")
    print(f"Vagas Expiradas/Inválidas: {len(dead)}")
    print(f"==========================================\n")

    print("Amostra de vagas encerradas detectadas:")
    for d in dead[:10]:
        print(f" - [ID {d['id']}] {d['title']}: {d['status']}")

if __name__ == "__main__":
    asyncio.run(main())
