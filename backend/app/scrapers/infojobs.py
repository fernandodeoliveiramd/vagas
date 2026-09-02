import httpx
from bs4 import BeautifulSoup
import logging
from typing import List, Dict, Any
from .base import BaseScraper
from ..core.config import normalize_text

logger = logging.getLogger(__name__)

class InfoJobsScraper(BaseScraper):
    def __init__(self):
        super().__init__(name="InfoJobs")
        self.base_url = "https://www.infojobs.com.br"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "pt-BR,pt;q=0.9",
        }

    async def scrape(self) -> List[Dict[str, Any]]:
        jobs = []
        cargos = [
            "eletricista",
            "instrumentista",
            "eletronica",
            "desenvolvedor",
            "dados",
            "projetos"
        ]
        
        cidades = [
            {"name": "Pelotas", "query": "pelotas-rs"},
            {"name": "Rio Grande", "query": "rio-grande-rs"}
        ]

        async with httpx.AsyncClient(headers=self.headers, timeout=15.0, follow_redirects=True) as client:
            for cidade in cidades:
                for cargo in cargos:
                    url = f"{self.base_url}/empregos-em-{cidade['query']}.aspx?palavra={cargo}"
                    try:
                        resp = await client.get(url)
                        if resp.status_code != 200:
                            continue
                            
                        soup = BeautifulSoup(resp.text, 'html.parser')
                        cards = soup.select(".js_vacancy, .element-vaga, [data-id]")
                        
                        for card in cards:
                            title_elem = card.select_one(".js_vacancyTitle, .title-vaga, h2 a, h3 a, h2")
                            title = title_elem.get_text(strip=True) if title_elem else ""
                            
                            link_elem = card.select_one("a[href*='/vaga-de-']") or title_elem
                            href = link_elem['href'] if link_elem and hasattr(link_elem, 'attrs') and 'href' in link_elem.attrs else ""
                            
                            if not title or not href:
                                continue

                            full_url = href if href.startswith("http") else f"{self.base_url}{href}"
                            company_elem = card.select_one(".js_vacancyCompany, .company-name, .small")
                            company = company_elem.get_text(strip=True) if company_elem else "Empresa InfoJobs"
                            
                            desc_elem = card.select_one(".js_vacancyDescription, .desc-vaga, p")
                            desc = desc_elem.get_text(strip=True) if desc_elem else f"Vaga de {title} em {cidade['name']}"

                            salary_elem = card.select_one(".js_vacancySalary, .salary")
                            salary = salary_elem.get_text(strip=True) if salary_elem else "A combinar / Não informado"

                            external_id = f"infojobs_{abs(hash(full_url)) % 10000000}"

                            job_dict = {
                                "external_id": external_id,
                                "title": title,
                                "company": company,
                                "location": f"{cidade['name']} - RS",
                                "city": cidade['name'],
                                "state": "RS",
                                "work_model": "Presencial",
                                "description": desc,
                                "salary": salary,
                                "url": full_url,
                                "source": "InfoJobs",
                                "published_at": None
                            }
                            jobs.append(job_dict)
                    except Exception as e:
                        logger.error(f"[InfoJobs] Erro em {cidade['name']} / {cargo}: {e}")

        logger.info(f"[InfoJobs] Total de vagas coletadas: {len(jobs)}")
        return jobs
