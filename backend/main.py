import os
import sys
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import uvicorn
import logging

from app.database.db import init_db
from app.api.routes import router as api_router
from app.services.scheduler import start_scheduler, stop_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Vagas Pelotas & Rio Grande - RS",
    description="Sistema de Agregação, Monitoramento e Candidaturas de Vagas",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Routes
app.include_router(api_router)

# Static Files (Frontend UI)
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "frontend")

@app.on_event("startup")
def on_startup():
    logger.info("Inicializando banco de dados...")
    init_db()
    logger.info("Iniciando agendador de tarefas periódicas...")
    start_scheduler(interval_hours=3)
    logger.info("Sistema pronto para busca de vagas!")

@app.on_event("shutdown")
def on_shutdown():
    stop_scheduler()

if os.path.exists(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

    @app.get("/")
    def serve_frontend():
        index_path = os.path.join(FRONTEND_DIR, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
        return {"message": "API rodando! Adicione index.html em frontend/"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
