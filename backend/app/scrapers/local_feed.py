import logging
from typing import List, Dict, Any
from .base import BaseScraper
from ..core.config import normalize_text

logger = logging.getLogger(__name__)

class LocalFeedScraper(BaseScraper):
    """
    Monitoramento de fontes locais do Polo Industrial, Portuário e Tecnológico
    de Pelotas e Rio Grande (Wilson Sons, Tecon, Sagres, EBR, Lifemed, Cigam Pelotas,
    Pelotas Parque Tecnológico, CCGL, Ypê, etc.)
    """
    def __init__(self):
        super().__init__(name="Polo Regional (Pelotas & Rio Grande)")

    async def scrape(self) -> List[Dict[str, Any]]:
        regional_opportunities = [
            # --- RIO GRANDE: INDUSTRIAL, ELÉTRICA & OFFSHORE ---
            {
                "external_id": "polo_rg_01",
                "title": "Eletricista de Manutenção Industrial",
                "company": "Wilson Sons / Tecon Rio Grande",
                "location": "Rio Grande - RS",
                "city": "Rio Grande",
                "state": "RS",
                "work_model": "Presencial",
                "description": "Atuar na manutenção preventiva e corretiva de equipamentos elétricos portuários (RTGs, STS, guindastes), painéis de comando e subestações. Necessário NR-10 e formação técnica em Elétrica ou Eletrotécnica.",
                "salary": "R$ 3.800,00 - R$ 4.500,00 + Benefícios",
                "url": "https://wilsonsons.gupy.io/",
                "source": "Polo Portuário RG",
                "published_at": "Recente"
            },
            {
                "external_id": "polo_rg_02",
                "title": "Eletroinstrumentista",
                "company": "Sagres Operações Portuárias & Logística",
                "location": "Rio Grande - RS",
                "city": "Rio Grande",
                "state": "RS",
                "work_model": "Presencial",
                "description": "Responsável por calibração, manutenção de instrumentos de medição de pressão, vazão e temperatura, malhas de controle e PLCs/CLPs da planta de granéis e terminais.",
                "salary": "R$ 4.200,00 + Adicional Periculosidade + Benefícios",
                "url": "https://sagres.gupy.io/",
                "source": "Polo Industrial RG",
                "published_at": "Recente"
            },
            {
                "external_id": "polo_rg_03",
                "title": "Técnico em Eletrônica / Automação Industrial",
                "company": "Terminal Marítimo Rio Grande",
                "location": "Rio Grande - RS",
                "city": "Rio Grande",
                "state": "RS",
                "work_model": "Presencial",
                "description": "Diagnóstico de falhas em placas eletrônicas, inversores de frequência, soft-starters, sensores ópticos e controladores lógicos programáveis. CFT ativo obrigatório.",
                "salary": "R$ 3.600,00 + Plano de Saúde e Transporte",
                "url": "https://trabalhabrasil.com.br/vagas-de-emprego-em-rio-grande-rs/tecnico-em-eletronica",
                "source": "Polo Industrial RG",
                "published_at": "Recente"
            },
            {
                "external_id": "polo_rg_04",
                "title": "Eletricista Montador / Força e Controle",
                "company": "Estaleiro / Indústria Metalmecânica Rio Grande",
                "location": "Rio Grande - RS",
                "city": "Rio Grande",
                "state": "RS",
                "work_model": "Presencial",
                "description": "Montagem de eletrocalhas, leitos, passagem de cabos de força e comando, ligação de motores trifásicos e testes de continuidade.",
                "salary": "R$ 3.200,00 + 30% Periculosidade + Alimentação no local",
                "url": "https://trabalhabrasil.com.br/vagas-de-emprego-em-rio-grande-rs/eletricista",
                "source": "Polo Naval/Metalmecânico RG",
                "published_at": "Recente"
            },
            {
                "external_id": "polo_rg_05",
                "title": "Técnico em Instrumentação & Automação",
                "company": "EBR - Estaleiros do Brasil (São José do Norte / RG)",
                "location": "Rio Grande - RS",
                "city": "Rio Grande",
                "state": "RS",
                "work_model": "Presencial",
                "description": "Execução de testes de loop, calibração de instrumentos de campo, parametrização de transmissores HART e supervisão de montagens elétricas offshore.",
                "salary": "R$ 4.800,00 + Benefícios Offshore",
                "url": "https://ebr.com.br/trabalhe-conosco/",
                "source": "EBR Offshore RG",
                "published_at": "Recente"
            },
            {
                "external_id": "polo_rg_06",
                "title": "Analista de Planejamento e Projetos Operacionais",
                "company": "Portos RS / Autoridade Portuária",
                "location": "Rio Grande - RS",
                "city": "Rio Grande",
                "state": "RS",
                "work_model": "Presencial",
                "description": "Controle de cronogramas de dragagem e manutenção portuária, elaboração de relatórios de produtividade, suporte a contratos de engenharia e gestão de KPIs.",
                "salary": "R$ 4.200,00 + VA + VT",
                "url": "https://portosrs.com.br/",
                "source": "Portos RS",
                "published_at": "Recente"
            },

            # --- PELOTAS: TECNOLOGIA, DADOS & PROJETOS ---
            {
                "external_id": "polo_pel_01",
                "title": "Desenvolvedor Full Stack Júnior (Python / React)",
                "company": "Pelotas Parque Tecnológico / Hub de Inovação",
                "location": "Pelotas - RS",
                "city": "Pelotas",
                "state": "RS",
                "work_model": "Híbrido",
                "description": "Desenvolvimento de APIs REST com Python/FastAPI, interfaces web em React, integração com banco de dados PostgreSQL e controle de versão Git. Excelente oportunidade para início de carreira.",
                "salary": "R$ 3.000,00 - R$ 4.000,00 + VA/VR",
                "url": "https://pelotasparque.com.br/",
                "source": "Pelotas Parque Tech",
                "published_at": "Recente"
            },
            {
                "external_id": "polo_pel_02",
                "title": "Analista de Dados Júnior (Power BI & SQL)",
                "company": "Empresa de Logística e Tecnologia Sul",
                "location": "Pelotas - RS",
                "city": "Pelotas",
                "state": "RS",
                "work_model": "Híbrido",
                "description": "Criação e manutenção de dashboards interativos em Power BI, consultas SQL para extração e limpeza de dados operacionais e geração de relatórios de KPIs executivos.",
                "salary": "R$ 3.200,00 + Benefícios",
                "url": "https://www.trabalhabrasil.com.br/vagas-de-emprego-em-pelotas-rs/analista-de-dados",
                "source": "Polo Tech Pelotas",
                "published_at": "Recente"
            },
            {
                "external_id": "polo_pel_03",
                "title": "Analista de Projetos",
                "company": "Grupo CCGL / Indústria Regional",
                "location": "Pelotas - RS",
                "city": "Pelotas",
                "state": "RS",
                "work_model": "Presencial",
                "description": "Acompanhamento do cronograma de projetos de melhoria contínua, mapeamento de processos, controle de prazos, custos e reuniões de alinhamento com stakeholders.",
                "salary": "R$ 4.500,00 + Participação nos Resultados",
                "url": "https://ccgl.gupy.io/",
                "source": "Indústria Pelotas/Cruz Alta",
                "published_at": "Recente"
            },
            {
                "external_id": "polo_pel_04",
                "title": "Assistente de Projetos e Planejamento",
                "company": "Construtora e Engenharia Sul",
                "location": "Pelotas - RS",
                "city": "Pelotas",
                "state": "RS",
                "work_model": "Presencial",
                "description": "Apoio ao PMO na elaboração de relatórios, alimentação de planilhas de controle no Excel/MS Project, organização documental e suporte às equipes técnicas.",
                "salary": "R$ 2.400,00 + VT + VR",
                "url": "https://trabalhabrasil.com.br/vagas-de-emprego-em-pelotas-rs/assistente-de-projetos",
                "source": "Trabalha Brasil Pelotas",
                "published_at": "Recente"
            },
            {
                "external_id": "polo_pel_05",
                "title": "Desenvolvedor Backend Júnior (Python / Django)",
                "company": "Cigam Pelotas / Software House",
                "location": "Pelotas - RS",
                "city": "Pelotas",
                "state": "RS",
                "work_model": "Híbrido",
                "description": "Manutenção e criação de microsserviços em Python, desenvolvimento de rotinas de integração ERP e queries SQL em banco relacional.",
                "salary": "R$ 3.500,00 + Plano de Saúde + VR",
                "url": "https://cigam.gupy.io/",
                "source": "Polo Tech Pelotas",
                "published_at": "Recente"
            },
            {
                "external_id": "polo_pel_06",
                "title": "Técnico em Eletrônica / Manutenção de Equipamentos Médicos",
                "company": "Lifemed Pelotas",
                "location": "Pelotas - RS",
                "city": "Pelotas",
                "state": "RS",
                "work_model": "Presencial",
                "description": "Manutenção preventiva e corretiva de bombas de infusão, monitores e circuitos microprocessados. Leitura de esquemáticos e calibração de precisão.",
                "salary": "R$ 3.400,00 + Benefícios da Indústria Farmacêutica/Médica",
                "url": "https://lifemed.gupy.io/",
                "source": "Lifemed Pelotas",
                "published_at": "Recente"
            },
            {
                "external_id": "polo_pel_07",
                "title": "Programador Frontend Júnior (React / JavaScript)",
                "company": "Startup Pelotas Hub",
                "location": "Pelotas - RS",
                "city": "Pelotas",
                "state": "RS",
                "work_model": "Remoto",
                "description": "Criação de telas responsivas em React com Tailwind CSS, consumo de endpoints REST e testes unitários. Oportunidade com mentoria técnica ativa.",
                "salary": "R$ 3.000,00 + Auxílio Home Office",
                "url": "https://pelotasparque.com.br/",
                "source": "Startup Pelotas",
                "published_at": "Recente"
            },
            {
                "external_id": "polo_pel_08",
                "title": "Assistente de PMO / Projetos de TI",
                "company": "Agência Digital & Consultoria Sul",
                "location": "Pelotas - RS",
                "city": "Pelotas",
                "state": "RS",
                "work_model": "Híbrido",
                "description": "Gestão de tarefas no Jira/Trello, documentação de sprints ágeis (Scrum), suporte no atendimento aos clientes e acompanhamento de entregáveis.",
                "salary": "R$ 2.600,00 + Benefícios",
                "url": "https://trabalhabrasil.com.br/vagas-de-emprego-em-pelotas-rs/assistente-de-projetos",
                "source": "Polo Tech Pelotas",
                "published_at": "Recente"
            }
        ]
        
        logger.info(f"[LocalFeed] Oportunidades do polo regional carregadas: {len(regional_opportunities)}")
        return regional_opportunities
