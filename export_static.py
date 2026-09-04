import os
import sys
import json
import asyncio

# Fix Windows console UTF-8 output
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.join(BASE_DIR, "backend"))

from backend.app.database.db import init_db, get_jobs, get_stats, sync_jobs_from_json
from backend.app.scrapers.manager import scraper_manager
from backend.app.services.verifier import verify_and_clean_all_jobs

async def main():
    print("=" * 60)
    print("   ATUALIZANDO E VALIDANDO VAGAS PARA GITHUB PAGES")
    print("=" * 60)

    # 1. Inicializar banco e carregar vagas já listadas
    init_db()
    existing_json = os.path.join(BASE_DIR, "data", "jobs.json")
    synced = sync_jobs_from_json(existing_json)
    if synced > 0:
        print(f"      -> {synced} vagas existentes restauradas do histórico data/jobs.json.")

    # 2. Executar varredura
    print("[1/3] Executando varredura nos portais (LinkedIn, Trabalha Brasil, Gupy, Polos)...")
    res = await scraper_manager.run_all()
    print(f"      -> {res.get('total_jobs_found', 0)} encontradas | {res.get('new_jobs_inserted', 0)} novas salvas.")

    # 3. Validação de disponibilidade e remoção de vagas expiradas
    print("[2/3] Validando links e removendo vagas encerradas/expiradas...")
    verify_res = await verify_and_clean_all_jobs()
    print(f"      -> {verify_res['active_jobs']} vagas 100% ativas | {verify_res['removed_jobs']} vagas expiradas removidas.")

    # 4. Extrair dados consolidados
    print("[3/3] Gerando arquivos estáticos JSON atualizados...")
    jobs = get_jobs(limit=500)
    stats = get_stats()

    # 5. Salvar data/jobs.json e data/stats.json
    data_dir = os.path.join(BASE_DIR, "data")
    os.makedirs(data_dir, exist_ok=True)

    jobs_path = os.path.join(data_dir, "jobs.json")
    stats_path = os.path.join(data_dir, "stats.json")

    with open(jobs_path, "w", encoding="utf-8") as f:
        json.dump({"success": True, "count": len(jobs), "jobs": jobs}, f, ensure_ascii=False, indent=2)

    with open(stats_path, "w", encoding="utf-8") as f:
        json.dump({"success": True, "stats": stats}, f, ensure_ascii=False, indent=2)

    print(f"[OK] Concluido com sucesso! Base atualizada com {len(jobs)} vagas verificadas e ativas.")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
