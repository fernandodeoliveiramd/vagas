from datetime import datetime
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field

class JobCategory(str, Enum):
    INDUSTRIAL_ELETRICA = "industrial_eletrica"
    TECNOLOGIA_JR = "tecnologia_jr"
    GESTAO_PROJETOS = "gestao_projetos"
    OUTRO = "outro"

class WorkModel(str, Enum):
    PRESENCIAL = "Presencial"
    HIBRIDO = "Híbrido"
    REMOTO = "Remoto"
    NAO_INFORMADO = "Não Informado"

class JobStatus(str, Enum):
    NOVA = "nova"
    INTERESSE = "interesse"
    CANDIDATADO = "candidatado"
    ENTREVISTA = "entrevista"
    DESFECHO_POSITIVO = "aprovado"
    DESCARTADA = "descartada"

class JobBase(BaseModel):
    title: str
    company: str
    location: str
    city: Optional[str] = None
    state: Optional[str] = "RS"
    work_model: WorkModel = WorkModel.NAO_INFORMADO
    category: JobCategory = JobCategory.OUTRO
    role_matched: Optional[str] = None
    description: Optional[str] = ""
    salary: Optional[str] = "A combinar / Não informado"
    url: str
    source: str
    external_id: Optional[str] = None
    match_score: int = 50

class JobCreate(JobBase):
    pass

class JobUpdate(BaseModel):
    status: Optional[JobStatus] = None
    notes: Optional[str] = None
    is_favorite: Optional[bool] = None

class Job(JobBase):
    id: int
    status: JobStatus = JobStatus.NOVA
    notes: Optional[str] = ""
    is_favorite: bool = False
    published_at: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())

    class Config:
        from_attributes = True

class ScrapeStats(BaseModel):
    total_jobs: int
    new_jobs_found: int
    sources_scraped: List[str]
    duration_seconds: float
    timestamp: str
