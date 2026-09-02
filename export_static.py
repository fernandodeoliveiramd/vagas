import os
import sys
import json
import asyncio

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.join(BASE_DIR, "backend"))

from backend.app.database.db import init_db, get_jobs, get_stats
from backend.app.scrapers.manager import scraper_manager

async def main():
    print("=" * 60)
    print("   EXPORTANDO DADOS DE VAGAS PARA GITHUB PAGES (/vagas)")
    print("=" * 60)

    # 1. Inicializar banco
    init_db()

    # 2. Executar varredura
    print("[1/3] Executando varredura nos portais (LinkedIn, Trabalha Brasil, Gupy, Polos)...")
    res = await scraper_manager.run_all()
    print(f"      -> {res.get('total_jobs_found', 0)} encontradas | {res.get('new_jobs_inserted', 0)} novas salvas.")

    # 3. Extrair dados consolidados
    print("[2/3] Gerando arquivos estáticos JSON...")
    jobs = get_jobs(limit=500)
    stats = get_stats()

    # 4. Salvar data/jobs.json e data/stats.json
    data_dir = os.path.join(BASE_DIR, "data")
    os.makedirs(data_dir, exist_ok=True)

    jobs_path = os.path.join(data_dir, "jobs.json")
    stats_path = os.path.join(data_dir, "stats.json")

    with open(jobs_path, "w", encoding="utf-8") as f:
        json.dump({"success": True, "count": len(jobs), "jobs": jobs}, f, ensure_ascii=False, indent=2)

    with open(stats_path, "w", encoding="utf-8") as f:
        json.dump({"success": True, "stats": stats}, f, ensure_ascii=False, indent=2)

    print(f"[3/3] Exportação concluída com sucesso!")
    print(f"      - {jobs_path} ({len(jobs)} vagas)")
    print(f"      - {stats_path}")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
