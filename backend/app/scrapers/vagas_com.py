import httpx
from bs4 import BeautifulSoup
import logging
from typing import List, Dict, Any
from .base import BaseScraper
from ..core.config import normalize_text

logger = logging.getLogger(__name__)

class VagasComScraper(BaseScraper):
    def __init__(self):
        super().__init__(name="Vagas.com.br")
        self.base_url = "https://www.vagas.com.br"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }

    async def scrape(self) -> List[Dict[str, Any]]:
        jobs = []
        queries = [
            ("eletricista", "rio-grande-do-sul"),
            ("instrumentista", "rio-grande-do-sul"),
            ("eletronica", "rio-grande-do-sul"),
            ("desenvolvedor", "rio-grande-do-sul"),
            ("dados", "rio-grande-do-sul"),
            ("projetos", "rio-grande-do-sul"),
        ]

        async with httpx.AsyncClient(headers=self.headers, timeout=15.0, follow_redirects=True) as client:
            for cargo, regiao in queries:
                url = f"{self.base_url}/vagas-de-{cargo}-em-{regiao}"
                try:
                    resp = await client.get(url)
                    if resp.status_code != 200:
                        continue
                        
                    soup = BeautifulSoup(resp.text, 'html.parser')
                    cards = soup.select(".vaga, article.vaga")
                    
                    for card in cards:
                        title_elem = card.select_one(".link-detalhes-vaga, .cargo, h2 a")
                        title = title_elem.get_text(strip=True) if title_elem else ""
                        href = title_elem['href'] if title_elem and 'href' in title_elem.attrs else ""
                        
                        if not title or not href:
                            continue

                        full_url = href if href.startswith("http") else f"{self.base_url}{href}"
                        
                        company_elem = card.select_one(".empr, .empresa, .nome-empresa")
                        company = company_elem.get_text(strip=True) if company_elem else "Empresa Confidencial (Vagas.com)"
                        
                        loc_elem = card.select_one(".local, .cidade-estado")
                        location = loc_elem.get_text(strip=True) if loc_elem else "Rio Grande do Sul"
                        
                        norm_loc = normalize_text(location)
                        norm_title = normalize_text(title)

                        is_pelotas = "pelotas" in norm_loc or "pelotas" in norm_title
                        is_rio_grande = "rio grande" in norm_loc or "rio grande" in norm_title
                        is_remote = "remoto" in norm_loc or "home office" in norm_loc
                        
                        # Apenas aceita se for Pelotas, Rio Grande ou Remoto relevante
                        if not (is_pelotas or is_rio_grande or is_remote):
                            continue

                        city = "Pelotas" if is_pelotas else ("Rio Grande" if is_rio_grande else ("Remoto" if is_remote else "RS"))
                        work_model = "Remoto" if is_remote else "Presencial"

                        desc_elem = card.select_one(".detalhes, .descricao")
                        desc = desc_elem.get_text(strip=True) if desc_elem else f"Vaga de {title} em {location}"

                        external_id = f"vagas_{abs(hash(full_url)) % 10000000}"

                        job_dict = {
                            "external_id": external_id,
                            "title": title,
                            "company": company,
                            "location": location,
                            "city": city,
                            "state": "RS",
                            "work_model": work_model,
                            "description": desc,
                            "salary": "A combinar / Não informado",
                            "url": full_url,
                            "source": "Vagas.com.br",
                            "published_at": None
                        }
                        jobs.append(job_dict)

                except Exception as e:
                    logger.error(f"[VagasCom] Erro em {cargo}: {e}")

        logger.info(f"[VagasCom] Total de vagas coletadas: {len(jobs)}")
        return jobs
