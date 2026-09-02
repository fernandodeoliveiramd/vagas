import urllib.request
import urllib.parse
import ssl
import logging
import re
import asyncio
from typing import List, Dict, Any
from bs4 import BeautifulSoup
from .base import BaseScraper
from ..core.config import normalize_text

logger = logging.getLogger(__name__)

class LinkedInScraper(BaseScraper):
    """
    Coletor de vagas públicas do LinkedIn para Pelotas e Rio Grande (RS)
    """
    def __init__(self):
        super().__init__(name="LinkedIn")
        self.base_url = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
            "Referer": "https://www.google.com/"
        }

    def _fetch_linkedin_sync(self, keyword: str, location_str: str, default_city: str) -> List[Dict[str, Any]]:
        jobs = []
        try:
            encoded_kw = urllib.parse.quote(keyword)
            encoded_loc = urllib.parse.quote(location_str)
            url = f"{self.base_url}?keywords={encoded_kw}&location={encoded_loc}&start=0"
            
            req = urllib.request.Request(url, headers=self.headers)
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            
            with urllib.request.urlopen(req, context=ctx, timeout=10) as response:
                html = response.read().decode('utf-8', errors='ignore')
                soup = BeautifulSoup(html, 'html.parser')
                cards = soup.select('li')
                
                for card in cards:
                    title_elem = card.select_one('.base-search-card__title, h3')
                    company_elem = card.select_one('.base-search-card__subtitle, h4')
                    loc_elem = card.select_one('.job-search-card__location')
                    link_elem = card.select_one('a.base-card__full-link, a[href*="/jobs/view/"]')
                    date_elem = card.select_one('time')
                    
                    if not title_elem or not link_elem:
                        continue
                        
                    title = title_elem.get_text(strip=True)
                    company = company_elem.get_text(strip=True) if company_elem else "Empresa LinkedIn"
                    raw_loc = loc_elem.get_text(strip=True) if loc_elem else location_str
                    full_url = link_elem['href'].split('?')[0] if 'href' in link_elem.attrs else ""
                    
                    if not full_url:
                        continue

                    norm_loc = normalize_text(raw_loc)
                    norm_title = normalize_text(title)

                    # Filtrar localização: apenas Pelotas, Rio Grande, RS ou Remoto
                    is_pelotas = "pelotas" in norm_loc or "pelotas" in norm_title
                    is_rio_grande = "rio grande" in norm_loc or "rio grande" in norm_title
                    is_region = any(c in norm_loc for c in ["capao do leao", "sao jose do norte"])
                    is_remote = any(r in norm_loc or r in norm_title for r in ["remoto", "remote", "home office"])
                    
                    # Se não for da região nem remoto, descarta vagas de outros estados
                    if not (is_pelotas or is_rio_grande or is_region or is_remote):
                        continue

                    city = "Pelotas" if is_pelotas else ("Rio Grande" if (is_rio_grande or is_region) else ("Remoto" if is_remote else default_city))
                    
                    work_model = "Presencial"
                    if is_remote:
                        work_model = "Remoto"
                    elif "hibrid" in norm_loc or "hybrid" in norm_loc:
                        work_model = "Híbrido"

                    # Extrair ID numérico da URL do LinkedIn
                    id_match = re.search(r'-(\d+)$', full_url)
                    job_id = id_match.group(1) if id_match else str(abs(hash(full_url)) % 10000000)

                    published_at = date_elem.get_text(strip=True) if date_elem else None

                    job_dict = {
                        "external_id": f"linkedin_{job_id}",
                        "title": title,
                        "company": company,
                        "location": f"{city} - RS" if city != "Remoto" else "Remoto (Brasil)",
                        "city": city,
                        "state": "RS",
                        "work_model": work_model,
                        "description": f"Vaga de {title} na empresa {company} em {city}. Publicada no LinkedIn.",
                        "salary": "A combinar / Não informado",
                        "url": full_url,
                        "source": "LinkedIn",
                        "published_at": published_at
                    }
                    jobs.append(job_dict)

        except Exception as e:
            logger.debug(f"[LinkedIn] Erro ao buscar '{keyword}' em '{location_str}': {e}")
        return jobs

    async def scrape(self) -> List[Dict[str, Any]]:
        search_configs = [
            # Pelotas
            ("eletricista", "Pelotas, Rio Grande do Sul, Brasil", "Pelotas"),
            ("instrumentista", "Pelotas, Rio Grande do Sul, Brasil", "Pelotas"),
            ("eletronica", "Pelotas, Rio Grande do Sul, Brasil", "Pelotas"),
            ("desenvolvedor", "Pelotas, Rio Grande do Sul, Brasil", "Pelotas"),
            ("analista de dados", "Pelotas, Rio Grande do Sul, Brasil", "Pelotas"),
            ("analista de projetos", "Pelotas, Rio Grande do Sul, Brasil", "Pelotas"),
            ("assistente de projetos", "Pelotas, Rio Grande do Sul, Brasil", "Pelotas"),
            
            # Rio Grande
            ("eletricista", "Rio Grande, Rio Grande do Sul, Brasil", "Rio Grande"),
            ("instrumentista", "Rio Grande, Rio Grande do Sul, Brasil", "Rio Grande"),
            ("eletronica", "Rio Grande, Rio Grande do Sul, Brasil", "Rio Grande"),
            ("automacao", "Rio Grande, Rio Grande do Sul, Brasil", "Rio Grande"),
            ("desenvolvedor", "Rio Grande, Rio Grande do Sul, Brasil", "Rio Grande"),
            ("analista de dados", "Rio Grande, Rio Grande do Sul, Brasil", "Rio Grande"),
            ("analista de projetos", "Rio Grande, Rio Grande do Sul, Brasil", "Rio Grande"),
            ("assistente de projetos", "Rio Grande, Rio Grande do Sul, Brasil", "Rio Grande"),
        ]

        tasks = [
            asyncio.to_thread(self._fetch_linkedin_sync, kw, loc, default_city)
            for kw, loc, default_city in search_configs
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        all_jobs = []
        for r in results:
            if isinstance(r, list):
                all_jobs.extend(r)

        logger.info(f"[LinkedIn] Total de vagas regionais coletadas: {len(all_jobs)}")
        return all_jobs
