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

class TrabalhaBrasilScraper(BaseScraper):
    def __init__(self):
        super().__init__(name="Trabalha Brasil")
        self.base_url = "https://www.trabalhabrasil.com.br"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
        }

    def _fetch_cargo_sync(self, target_cidade: Dict[str, str], cargo: str) -> List[Dict[str, Any]]:
        url = f"{self.base_url}/vagas-de-emprego-em-{target_cidade['slug']}/{cargo}"
        req = urllib.request.Request(url, headers=self.headers)
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        
        jobs = []
        try:
            with urllib.request.urlopen(req, context=ctx, timeout=10) as response:
                html = response.read().decode('utf-8', errors='ignore')
                soup = BeautifulSoup(html, 'html.parser')
                
                for a in soup.find_all('a', href=True):
                    href = a['href']
                    parts = href.strip('/').split('/')
                    
                    if len(parts) >= 3 and parts[-1].isdigit():
                        # parts[0] = 'vagas-de-emprego-em-pelotas-rs'
                        loc_part = parts[0].replace('vagas-de-emprego-em-', '')
                        
                        # Extrair cidade real da URL
                        if 'pelotas' in loc_part:
                            city_name = "Pelotas"
                            state = "RS"
                        elif 'rio-grande' in loc_part:
                            city_name = "Rio Grande"
                            state = "RS"
                        else:
                            # Ignorar vagas sugeridas de outros estados/cidades distantes
                            continue

                        numeric_id = parts[-1]
                        external_id = f"tb_{numeric_id}"
                        clean_href = href.split('?')[0].split('#')[0].rstrip('/')
                        if clean_href.startswith("http"):
                            full_url = clean_href
                        else:
                            if not clean_href.startswith('/'):
                                clean_href = '/' + clean_href
                            full_url = f"{self.base_url}{clean_href}"
                        
                        strings = [t.strip() for t in a.stripped_strings if t.strip()]
                        if not strings:
                            continue

                        raw_title = strings[0]
                        title = re.sub(r'^vaga de\s+', '', raw_title, flags=re.IGNORECASE).strip()
                        if not title:
                            title = cargo.replace('-', ' ').title()

                        company = strings[1] if len(strings) > 1 else "Empresa Confidencial"
                        
                        work_model = "Presencial"
                        if len(strings) > 3:
                            if "remoto" in strings[3].lower() or "home" in strings[3].lower():
                                work_model = "Remoto"
                            elif "hibrid" in strings[3].lower():
                                work_model = "Híbrido"

                        job_dict = {
                            "external_id": external_id,
                            "title": title,
                            "company": company,
                            "location": f"{city_name} - {state}",
                            "city": city_name,
                            "state": state,
                            "work_model": work_model,
                            "description": f"Vaga de {title} em {city_name}/{state} divulgada via Trabalha Brasil / SINE.",
                            "salary": "A combinar / Não informado",
                            "url": full_url,
                            "source": "Trabalha Brasil",
                            "published_at": None
                        }
                        jobs.append(job_dict)
        except Exception as e:
            logger.debug(f"[TrabalhaBrasil] {target_cidade['name']}/{cargo}: {e}")
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
            {"slug": "pelotas-rs", "name": "Pelotas", "state": "RS"},
            {"slug": "rio-grande-rs", "name": "Rio Grande", "state": "RS"}
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

        logger.info(f"[TrabalhaBrasil] Total de vagas regionais coletadas: {len(all_jobs)}")
        return all_jobs
