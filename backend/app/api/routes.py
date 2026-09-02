from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from typing import Optional, List, Dict, Any
from pydantic import BaseModel

from ..models.job import JobStatus, WorkModel, JobCategory
from ..database.db import (
    get_jobs, get_job_by_id, update_job, delete_job, get_stats
)
from ..scrapers.manager import scraper_manager
from ..core.config import config
from ..services.telegram import telegram_notifier

router = APIRouter(prefix="/api")

class StatusUpdateRequest(BaseModel):
    status: JobStatus

class NotesUpdateRequest(BaseModel):
    notes: str

class FavoriteUpdateRequest(BaseModel):
    is_favorite: bool

class TelegramTestRequest(BaseModel):
    bot_token: Optional[str] = None
    chat_id: Optional[str] = None

@router.get("/jobs")
def list_jobs(
    category: Optional[str] = "todas",
    city: Optional[str] = "todas",
    status: Optional[str] = "todas",
    work_model: Optional[str] = "todos",
    search: Optional[str] = None,
    only_favorites: bool = False,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0)
):
    """
    Lista vagas com filtros flexíveis de categoria, cidade, status e busca de texto
    """
    jobs = get_jobs(
        category=category,
        city=city,
        status=status,
        work_model=work_model,
        search=search,
        only_favorites=only_favorites,
        limit=limit,
        offset=offset
    )
    return {
        "success": True,
        "count": len(jobs),
        "jobs": jobs
    }

@router.get("/jobs/{job_id}")
def get_job(job_id: int):
    job = get_job_by_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Vaga não encontrada")
    return {"success": True, "job": job}

@router.patch("/jobs/{job_id}/status")
def change_job_status(job_id: int, req: StatusUpdateRequest):
    success = update_job(job_id, {"status": req.status.value})
    if not success:
        raise HTTPException(status_code=404, detail="Não foi possível atualizar o status da vaga")
    return {"success": True, "status": req.status.value}

@router.patch("/jobs/{job_id}/notes")
def change_job_notes(job_id: int, req: NotesUpdateRequest):
    success = update_job(job_id, {"notes": req.notes})
    if not success:
        raise HTTPException(status_code=404, detail="Não foi possível atualizar as anotações")
    return {"success": True, "notes": req.notes}

@router.patch("/jobs/{job_id}/favorite")
def toggle_favorite(job_id: int, req: FavoriteUpdateRequest):
    success = update_job(job_id, {"is_favorite": req.is_favorite})
    if not success:
        raise HTTPException(status_code=404, detail="Não foi possível alterar favorito")
    return {"success": True, "is_favorite": req.is_favorite}

@router.delete("/jobs/{job_id}")
def remove_job(job_id: int):
    success = delete_job(job_id)
    if not success:
        raise HTTPException(status_code=404, detail="Vaga não encontrada")
    return {"success": True, "message": "Vaga excluída com sucesso"}

@router.post("/jobs/scrape")
async def trigger_scrape():
    """
    Dispara varredura imediata em todos os portais e retorna o resumo
    """
    result = await scraper_manager.run_all()
    return {
        "success": True,
        "result": result
    }

@router.get("/stats")
def get_dashboard_stats():
    """
    Retorna estatísticas consolidadas para os cards do painel
    """
    stats = get_stats()
    return {
        "success": True,
        "stats": stats
    }

@router.get("/config")
def get_config():
    """
    Retorna as categorias e termos de busca configurados
    """
    return {
        "success": True,
        "categories": config.get_categories(),
        "locations": config.get_locations(),
        "negative_keywords": config.get_negative_keywords()
    }

@router.post("/test-telegram")
async def test_telegram(req: Optional[TelegramTestRequest] = None):
    if req and req.bot_token and req.chat_id:
        telegram_notifier.bot_token = req.bot_token
        telegram_notifier.chat_id = req.chat_id
        
    test_msg = (
        "🤖 <b>Sistema de Vagas (Pelotas & Rio Grande)</b>\n\n"
        "✅ Conexão com Telegram realizada com sucesso!\n"
        "Você receberá alertas aqui sempre que novas vagas compatíveis forem encontradas."
    )
    sent = await telegram_notifier.send_message(test_msg)
    if not sent:
        raise HTTPException(status_code=400, detail="Não foi possível enviar mensagem pelo Telegram. Verifique Token e Chat ID.")
    return {"success": True, "message": "Mensagem enviada com sucesso no Telegram!"}
