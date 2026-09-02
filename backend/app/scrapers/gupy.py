import json
import logging
import urllib.request
import urllib.parse
import ssl
import asyncio
from typing import List, Dict, Any
from .base import BaseScraper
from ..core.config import config, normalize_text

logger = logging.getLogger(__name__)

class GupyScraper(BaseScraper):
    def __init__(self):
        super().__init__(name="Gupy")
        self.base_url = "https://portal.gupy.io/api/v1/jobs"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Origin": "https://portal.gupy.io",
            "Referer": "https://portal.gupy.io/"
        }

    def _fetch_term_sync(self, term: str) -> List[Dict[str, Any]]:
        jobs = []
        try:
            encoded_term = urllib.parse.quote(term)
            url = f"{self.base_url}?jobName={encoded_term}&limit=50&offset=0"
            req = urllib.request.Request(url, headers=self.headers)
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            
            with urllib.request.urlopen(req, context=ctx, timeout=8) as response:
                data = json.loads(response.read().decode('utf-8'))
                raw_jobs = data.get("data", []) if isinstance(data, dict) else []
                
                for item in raw_jobs:
                    job_id = str(item.get("id"))
                    title = item.get("name", "")
                    company = item.get("careerPageName", "Empresa Gupy")
                    city = item.get("city", "")
                    state = item.get("state", "")
                    workplace_type = item.get("workplaceType", "")
                    
                    work_model = "Presencial"
                    if workplace_type == "remote" or "remoto" in normalize_text(workplace_type):
                        work_model = "Remoto"
                    elif workplace_type == "hybrid" or "hibrido" in normalize_text(workplace_type):
                        work_model = "Híbrido"

                    location = f"{city} - {state}" if city and state else city or state or "Brasil"
                    norm_loc = normalize_text(location)
                    norm_title = normalize_text(title)

                    is_pelotas = "pelotas" in norm_loc or "pelotas" in norm_title
                    is_rio_grande = "rio grande" in norm_loc or "rio grande" in norm_title
                    is_remote = work_model == "Remoto"

                    if not (is_pelotas or is_rio_grande or (is_remote and any(k in norm_title for k in ["desenvolvedor", "programador", "dev", "dados", "projeto"]))):
                        continue

                    career_slug = item.get("careerPageName", "")
                    if item.get("jobUrl"):
                        job_url = item.get("jobUrl")
                    elif career_slug:
                        job_url = f"https://{career_slug}.gupy.io/job/{job_id}"
                    else:
                        job_url = f"https://portal.gupy.io/job/{job_id}"

                    job_dict = {
                        "external_id": f"gupy_{job_id}",
                        "title": title,
                        "company": company,
                        "location": location,
                        "city": "Pelotas" if is_pelotas else ("Rio Grande" if is_rio_grande else ("Remoto" if is_remote else city)),
                        "state": state or "RS",
                        "work_model": work_model,
                        "description": item.get("description", "") or f"Vaga de {title} na empresa {company}",
                        "salary": "A combinar / Não informado",
                        "url": job_url,
                        "source": "Gupy",
                        "published_at": item.get("publishedDate")
                    }
                    jobs.append(job_dict)
        except Exception as e:
            logger.debug(f"[Gupy] Erro no termo '{term}': {e}")
        return jobs

    async def scrape(self) -> List[Dict[str, Any]]:
        search_terms = [
            "eletricista",
            "eletroinstrumentista",
            "instrumentista",
            "eletrônica",
            "eletrotécnica",
            "desenvolvedor junior",
            "programador junior",
            "dados junior",
            "analista de projetos",
            "assistente de projetos"
        ]

        tasks = [asyncio.to_thread(self._fetch_term_sync, term) for term in search_terms]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        all_jobs = []
        for r in results:
            if isinstance(r, list):
                all_jobs.extend(r)

        logger.info(f"[Gupy] Total de vagas coletadas: {len(all_jobs)}")
        return all_jobs
