from abc import ABC, abstractmethod
from typing import List, Dict, Any
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BaseScraper(ABC):
    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    async def scrape(self) -> List[Dict[str, Any]]:
        """
        Executa a coleta de vagas e retorna uma lista de dicionários no formato padronizado:
        {
            "title": str,
            "company": str,
            "location": str,
            "city": Optional[str],
            "state": Optional[str],
            "work_model": str,
            "description": str,
            "salary": str,
            "url": str,
            "source": str,
            "external_id": Optional[str],
            "published_at": Optional[str]
        }
        """
        pass
