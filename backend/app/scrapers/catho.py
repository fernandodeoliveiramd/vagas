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

class CathoScraper(BaseScraper):
    def __init__(self):
        super().__init__(name="Catho")
        self.base_url = "https://www.catho.com.br"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
        }

    def _fetch_cargo_sync(self, target_cidade: Dict[str, str], cargo: str) -> List[Dict[str, Any]]:
        url = f"{self.base_url}/vagas/{cargo}/rs/{target_cidade['slug']}/"
        req = urllib.request.Request(url, headers=self.headers)
        ctx = ssl.create_default_context()

        jobs = []
        try:
            with urllib.request.urlopen(req, context=ctx, timeout=10) as response:
                html = response.read().decode('utf-8', errors='ignore')
                soup = BeautifulSoup(html, 'html.parser')

                for item in soup.select('li[data-offer-item]'):
                    offer_id = item.get('data-offer-item')
                    if not offer_id:
                        continue

                    link = item.select_one('h2.title_offer a, a[data-navigation-offer]')
                    if not link or not link.has_attr('href'):
                        continue

                    title = link.get_text(strip=True)
                    if not title:
                        continue

                    href = link['href']
                    full_url = href if href.startswith('http') else f"{self.base_url}{href}"

                    company_elem = item.select_one('.text-12')
                    company = company_elem.get_text(strip=True) if company_elem else ""
                    if not company or set(company) == {"*"}:
                        company = "Empresa Confidencial"

                    loc_icon = item.select_one('.i_job_location')
                    loc_text = loc_icon.find_parent('p').get_text(' ', strip=True) if loc_icon else ""
                    city_name = loc_text.split(' - ')[-1].strip() if ' - ' in loc_text else target_cidade['name']

                    salary_icon = item.select_one('.i_salary')
                    salary_text = salary_icon.find_parent('p').get_text(' ', strip=True) if salary_icon else ""
                    salary = re.sub(r'^\s*', '', salary_text) or "A combinar / Não informado"

                    norm_city = normalize_text(city_name)
                    if 'pelotas' in norm_city:
                        resolved_city = "Pelotas"
                    elif 'rio grande' in norm_city or 'povo novo' in norm_city:
                        # Povo Novo e um distrito do municipio de Rio Grande
                        resolved_city = "Rio Grande"
                    else:
                        resolved_city = target_cidade['name']

                    published_elem = item.select_one('.tag')
                    published_at = published_elem.get_text(strip=True) if published_elem else "Recente"

                    job_dict = {
                        "external_id": f"catho_{offer_id}",
                        "title": title,
                        "company": company,
                        "location": f"{resolved_city} - RS",
                        "city": resolved_city,
                        "state": "RS",
                        "work_model": "Presencial",
                        "description": f"Vaga de {title} em {resolved_city}/RS divulgada via Catho.",
                        "salary": salary,
                        "url": full_url,
                        "source": "Catho",
                        "published_at": published_at
                    }
                    jobs.append(job_dict)
        except Exception as e:
            logger.debug(f"[Catho] {target_cidade['name']}/{cargo}: {e}")
        return jobs

    async def scrape(self) -> List[Dict[str, Any]]:
        cargos = [
            "eletricista",
            "eletroinstrumentista",
            "instrumentista",
            "tecnico-em-eletronica",
            "tecnico-em-eletrotecnica",
            "programador",
            "desenvolvedor",
            "analista-de-dados",
            "analista-de-projetos",
            "assistente-de-projetos"
        ]

        cidades = [
            {"slug": "pelotas", "name": "Pelotas", "state": "RS"},
            {"slug": "rio-grande", "name": "Rio Grande", "state": "RS"}
        ]

        tasks = []
        for cidade in cidades:
            for cargo in cargos:
                tasks.append(asyncio.to_thread(self._fetch_cargo_sync, cidade, cargo))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_jobs = []
        for r in results:
            if isinstance(r, list):
                all_jobs.extend(r)

        deduped: Dict[str, Dict[str, Any]] = {}
        for job in all_jobs:
            deduped.setdefault(job["external_id"], job)
        unique_jobs = list(deduped.values())

        logger.info(f"[Catho] Total de vagas regionais coletadas: {len(unique_jobs)}")
        return unique_jobs
