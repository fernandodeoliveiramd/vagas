import os
import re
import unicodedata
from typing import Dict, Any, List, Optional, Tuple

try:
    import yaml
except ImportError:
    yaml = None

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CONFIG_DIR = os.path.join(ROOT_DIR, "config")

DEFAULT_CATEGORIES = {
    "industrial_eletrica": {
        "name": "Industrial, Elétrica & Eletrônica",
        "color": "#2563eb",
        "roles": [
            {
                "name": "Eletricista",
                "search_terms": [
                    "eletricista",
                    "eletricista industrial",
                    "eletricista predial",
                    "eletricista de manutencao",
                    "eletricista montador",
                    "eletricista forca e controle"
                ],
                "positive_keywords": [
                    "eletricista", "eletricidade", "alta tensao", "baixa tensao",
                    "nr10", "nr-10", "painel eletrico", "instalacoes eletricas", "comandos eletricos"
                ]
            },
            {
                "name": "Eletroinstrumentista",
                "search_terms": [
                    "eletroinstrumentista",
                    "instrumentista",
                    "tecnico instrumentacao",
                    "instrumentista industrial",
                    "instrumentacao industrial"
                ],
                "positive_keywords": [
                    "eletroinstrumentista", "instrumentacao", "calibracao", "transmissores",
                    "valvulas de controle", "sensores", "malhas de controle", "clp", "plc"
                ]
            },
            {
                "name": "Técnico em Eletrônica / Automação",
                "search_terms": [
                    "tecnico em eletronica",
                    "tecnico eletronico",
                    "tecnico em eletrotecnica",
                    "tecnico eletrotecnico",
                    "tecnico automacao",
                    "tecnico mecatronica"
                ],
                "positive_keywords": [
                    "eletronica", "eletrotecnica", "automacao", "placas de circuito",
                    "manutencao eletronica", "componentes", "soldagem eletronica", "inversores"
                ]
            }
        ]
    },
    "tecnologia_jr": {
        "name": "Tecnologia & Dados (Júnior)",
        "color": "#10b981",
        "roles": [
            {
                "name": "Desenvolvedor / Programador Júnior",
                "search_terms": [
                    "desenvolvedor junior",
                    "programador junior",
                    "dev junior",
                    "desenvolvedor jr",
                    "programador jr",
                    "desenvolvedor python",
                    "desenvolvedor frontend junior",
                    "desenvolvedor backend junior",
                    "desenvolvedor fullstack junior",
                    "software engineer junior"
                ],
                "positive_keywords": [
                    "desenvolvedor", "programador", "software", "python", "javascript",
                    "typescript", "react", "node", "sql", "git", "junior", "jr", "trainee", "estagio"
                ]
            },
            {
                "name": "Analista de Dados Júnior",
                "search_terms": [
                    "analista de dados junior",
                    "analista de dados jr",
                    "data analyst junior",
                    "analista de bi junior",
                    "analista de bi jr",
                    "business intelligence junior"
                ],
                "positive_keywords": [
                    "dados", "bi", "power bi", "sql", "excel", "dashboard",
                    "python", "etl", "analytics", "tableau", "junior", "jr"
                ]
            }
        ]
    },
    "gestao_projetos": {
        "name": "Gestão & Projetos",
        "color": "#8b5cf6",
        "roles": [
            {
                "name": "Analista de Projetos",
                "search_terms": [
                    "analista de projetos",
                    "analista de projetos junior",
                    "analista de projetos jr",
                    "analista pmo",
                    "analista de planejamento"
                ],
                "positive_keywords": [
                    "projetos", "pmo", "cronograma", "scrum", "agil", "ms project",
                    "planejamento", "indicadores", "gestao de projetos"
                ]
            },
            {
                "name": "Assistente de Projetos",
                "search_terms": [
                    "assistente de projetos",
                    "auxiliar de projetos",
                    "assistente pmo",
                    "assistente de planejamento"
                ],
                "positive_keywords": [
                    "assistente", "auxiliar", "projetos", "documentacao",
                    "acompanhamento", "relatorios", "suporte a projetos"
                ]
            }
        ]
    }
}

DEFAULT_LOCATIONS = [
    {"id": "pelotas", "name": "Pelotas", "state": "RS", "aliases": ["Pelotas", "Pelotas/RS", "Pelotas - RS"]},
    {"id": "rio_grande", "name": "Rio Grande", "state": "RS", "aliases": ["Rio Grande", "Rio Grande/RS", "Rio Grande - RS"]},
    {"id": "remoto", "name": "Remoto / Home Office", "state": "BR", "aliases": ["Remoto", "Home Office", "Teletrabalho"]}
]

DEFAULT_NEGATIVE_KEYWORDS = [
    "senior", "sr.", "especialista", "coordenador", "diretor", "gerente executivo",
    "vendedor de loja", "atendente de lanchonete", "corretor de imoveis"
]

def normalize_text(text: str) -> str:
    if not text:
        return ""
    text = unicodedata.normalize('NFKD', str(text)).encode('ASCII', 'ignore').decode('utf-8')
    text = re.sub(r'[^a-zA-Z0-9\s]', ' ', text.lower())
    return " ".join(text.split())

class AppConfig:
    _instance = None
    
    def __init__(self):
        self.keywords_config = self._load_yaml("keywords.yaml")
        self.locations_config = self._load_yaml("locations.yaml")
        
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = AppConfig()
        return cls._instance

    def _load_yaml(self, filename: str) -> Dict[str, Any]:
        if yaml is not None:
            filepath = os.path.join(CONFIG_DIR, filename)
            if os.path.exists(filepath):
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        return yaml.safe_load(f) or {}
                except Exception:
                    pass
        return {}

    def reload(self):
        self.keywords_config = self._load_yaml("keywords.yaml")
        self.locations_config = self._load_yaml("locations.yaml")

    def get_categories(self) -> Dict[str, Any]:
        return self.keywords_config.get("categories") or DEFAULT_CATEGORIES

    def get_locations(self) -> List[Dict[str, Any]]:
        return self.locations_config.get("locations") or DEFAULT_LOCATIONS

    def get_negative_keywords(self) -> List[str]:
        return self.keywords_config.get("negative_keywords") or DEFAULT_NEGATIVE_KEYWORDS

    def match_job(self, title: str, description: str = "", location_raw: str = "") -> Tuple[Optional[str], Optional[str], str, str, str, int]:
        norm_title = normalize_text(title)
        norm_desc = normalize_text(description)
        norm_loc = normalize_text(location_raw)
        full_text = f"{norm_title} {norm_desc}"

        is_jr_target = any(term in norm_title for term in ["junior", "jr", "estagio", "trainee", "assistente", "auxiliar"])
        for neg in self.get_negative_keywords():
            norm_neg = normalize_text(neg)
            if norm_neg in norm_title and not is_jr_target:
                return None, None, "Desconhecido", "RS", "Não Informado", 0

        best_category = None
        best_role = None
        best_score = 0

        categories = self.get_categories()
        for cat_key, cat_data in categories.items():
            roles = cat_data.get("roles", [])
            for role in roles:
                role_name = role.get("name")
                search_terms = role.get("search_terms", [])
                positive_keywords = role.get("positive_keywords", [])

                title_match = any(normalize_text(st) in norm_title for st in search_terms)
                body_matches = sum(1 for kw in positive_keywords if normalize_text(kw) in full_text)

                score = 0
                if title_match:
                    score += 65 + min(30, body_matches * 5)
                elif body_matches >= 2:
                    score += 30 + min(30, body_matches * 4)

                if score > best_score:
                    best_score = score
                    best_category = cat_key
                    best_role = role_name

        if best_score == 0:
            return None, None, "Desconhecido", "RS", "Não Informado", 0

        city = "Pelotas" if "pelotas" in norm_loc or "pelotas" in norm_title else "Rio Grande" if "rio grande" in norm_loc or "rio grande" in norm_title else None
        
        work_model = "Presencial"
        if any(w in full_text or w in norm_loc for w in ["remoto", "home office", "teletrabalho", "100 remoto"]):
            work_model = "Remoto"
            if not city:
                city = "Remoto"
        elif any(w in full_text or w in norm_loc for w in ["hibrido", "hybrid"]):
            work_model = "Híbrido"

        if not city:
            city = "Pelotas / Rio Grande" if ("pelotas" in norm_loc or "rio grande" in norm_loc) else "Pelotas"

        return best_category, best_role, city, "RS", work_model, min(100, max(40, best_score))

config = AppConfig.get_instance()
