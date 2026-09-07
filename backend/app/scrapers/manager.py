import asyncio
import time
import logging
from typing import List, Dict, Any
from datetime import datetime

from .gupy import GupyScraper
from .trabalha_brasil import TrabalhaBrasilScraper
from .linkedin import LinkedInScraper
from .catho import CathoScraper
from ..core.config import config
from ..core.dates import parse_published_at
from ..database.db import insert_job, log_scrape, get_stats, normalize_url
from ..services.telegram import telegram_notifier

logger = logging.getLogger(__name__)

class ScraperManager:
    def __init__(self):
        self.scrapers = [
            LinkedInScraper(),
            TrabalhaBrasilScraper(),
            GupyScraper(),
            CathoScraper()
        ]

    async def run_all(self) -> Dict[str, Any]:
        start_time = time.time()
        logger.info("Iniciando coleta em todos os portais de vagas (LinkedIn, Trabalha Brasil, Gupy, Catho)...")
        
        # Executar scrapers em paralelo
        tasks = [scraper.scrape() for scraper in self.scrapers]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        total_found = 0
        new_inserted = 0
        sources_scraped = []
        
        for scraper, result in zip(self.scrapers, results):
            source_name = scraper.name
            sources_scraped.append(source_name)
            
            if isinstance(result, Exception):
                logger.error(f"Erro no coletor '{source_name}': {result}")
                log_scrape(source_name, 0, 0, "error", str(result))
                continue
                
            raw_jobs = result if isinstance(result, list) else []
            source_found = len(raw_jobs)
            source_new = 0
            
            for item in raw_jobs:
                title = item.get("title", "")
                description = item.get("description", "")
                loc_raw = item.get("location", "")
                
                # Inteligência de classificação & matching
                category, role_matched, city, state, work_model, match_score = config.match_job(
                    title=title,
                    description=description,
                    location_raw=loc_raw
                )
                
                # Se não pertencer a nenhuma das categorias solicitadas, descarta
                if not category:
                    continue
                    
                total_found += 1
                
                # Montar objeto padronizado
                job_payload = {
                    "external_id": item.get("external_id"),
                    "source": item.get("source", source_name),
                    "title": title,
                    "company": item.get("company", "Confidencial"),
                    "location": item.get("location") or f"{city} - {state}",
                    "city": item.get("city") or city,
                    "state": item.get("state") or state,
                    "work_model": item.get("work_model") or work_model,
                    "category": category,
                    "role_matched": role_matched,
                    "description": description,
                    "salary": item.get("salary", "A combinar / Não informado"),
                    "url": normalize_url(item.get("url", "")),
                    "match_score": match_score,
                    "status": "nova",
                    "notes": "",
                    "is_favorite": False,
                    # Resolvido contra o instante da captura: o texto relativo
                    # do portal ("Ha 3 dias") vira data absoluta e para de mentir
                    # conforme o tempo passa.
                    "published_at": parse_published_at(item.get("published_at"))
                }
                
                inserted_id = insert_job(job_payload)
                if inserted_id:
                    source_new += 1
                    new_inserted += 1

                    # notify_new_job existia como metodo pronto no
                    # TelegramNotifier mas nunca era chamado - a UI
                    # prometia "alertas em tempo real" e so o botao de
                    # teste funcionava de fato. is_configured() evita o
                    # log de aviso repetido quando o bot nao esta setado.
                    if telegram_notifier.is_configured():
                        try:
                            await telegram_notifier.notify_new_job({**job_payload, "id": inserted_id})
                        except Exception as tg_err:
                            logger.warning(f"[Telegram] Falha ao notificar nova vaga: {tg_err}")


            log_scrape(source_name, source_found, source_new, "success")
            logger.info(f"[{source_name}] Vagas encontradas: {source_found}, Novas salvas: {source_new}")

        duration = round(time.time() - start_time, 2)
        stats = get_stats()
        
        logger.info(f"Varredura concluída em {duration}s! Total de vagas válidas: {total_found}, Novas no banco: {new_inserted}")
        
        return {
            "total_jobs_found": total_found,
            "new_jobs_inserted": new_inserted,
            "sources_scraped": sources_scraped,
            "duration_seconds": duration,
            "timestamp": datetime.now().isoformat(),
            "stats": stats
        }

scraper_manager = ScraperManager()
