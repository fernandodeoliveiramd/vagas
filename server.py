import os
import sys
import json
import sqlite3
import asyncio
import threading
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# Configurar stdout para UTF-8 no Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Adicionar caminho do projeto ao sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.join(BASE_DIR, "backend"))

from backend.app.database.db import (
    init_db, get_jobs, get_job_by_id, update_job, delete_job, get_stats, sync_jobs_from_json
)
from backend.app.scrapers.manager import scraper_manager
from backend.app.core.config import config
from backend.app.services.telegram import telegram_notifier

FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")

def sync_static_files():
    try:
        jobs_all = get_jobs(limit=500)
        stats_all = get_stats()
        data_dir = os.path.join(BASE_DIR, "data")
        os.makedirs(data_dir, exist_ok=True)
        with open(os.path.join(data_dir, "jobs.json"), "w", encoding="utf-8") as f:
            json.dump({"success": True, "count": len(jobs_all), "jobs": jobs_all}, f, ensure_ascii=False, indent=2)
        with open(os.path.join(data_dir, "stats.json"), "w", encoding="utf-8") as f:
            json.dump({"success": True, "stats": stats_all}, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[Warning] Falha ao sincronizar arquivos estáticos: {e}")

class JobAggregatorHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=FRONTEND_DIR, **kwargs)

    def log_message(self, format, *args):
        # Suprimir logs verbosos de arquivos estáticos
        pass

    def _send_json(self, data, status_code=200):
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PATCH, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PATCH, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        qs = parse_qs(parsed.query)

        # Rota da página inicial
        if path == "/" or path == "/index.html":
            self.path = "/index.html"
            return super().do_GET()

        # Servir arquivos estáticos do frontend
        if not path.startswith("/api/"):
            return super().do_GET()

        # API: Listar vagas
        if path == "/api/jobs":
            category = qs.get("category", ["todas"])[0]
            city = qs.get("city", ["todas"])[0]
            status = qs.get("status", ["todas"])[0]
            work_model = qs.get("work_model", ["todos"])[0]
            search = qs.get("search", [None])[0]
            only_fav = qs.get("only_favorites", ["false"])[0].lower() == "true"
            limit = int(qs.get("limit", [100])[0])
            offset = int(qs.get("offset", [0])[0])

            jobs = get_jobs(
                category=category,
                city=city,
                status=status,
                work_model=work_model,
                search=search,
                only_favorites=only_fav,
                limit=limit,
                offset=offset
            )
            return self._send_json({"success": True, "count": len(jobs), "jobs": jobs})

        # API: Estatísticas do Dashboard
        elif path == "/api/stats":
            stats = get_stats()
            return self._send_json({"success": True, "stats": stats})

        # API: Configurações
        elif path == "/api/config":
            return self._send_json({
                "success": True,
                "categories": config.get_categories(),
                "locations": config.get_locations(),
                "negative_keywords": config.get_negative_keywords()
            })

        # API: Detalhes de vaga por ID
        elif path.startswith("/api/jobs/"):
            try:
                job_id = int(path.split("/api/jobs/")[1])
                job = get_job_by_id(job_id)
                if job:
                    return self._send_json({"success": True, "job": job})
                return self._send_json({"success": False, "error": "Vaga não encontrada"}, 404)
            except Exception:
                pass

        self._send_json({"error": "Rota não encontrada"}, 404)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        # API: Executar varredura
        if path == "/api/jobs/scrape":
            sync_jobs_from_json()
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(scraper_manager.run_all())
                sync_static_files()
                return self._send_json({"success": True, "result": result})
            except Exception as e:
                return self._send_json({"success": False, "error": str(e)}, 500)
            finally:
                loop.close()

        # API: Testar Telegram
        elif path == "/api/test-telegram":
            content_len = int(self.headers.get('Content-Length', 0))
            post_body = self.rfile.read(content_len) if content_len > 0 else b'{}'
            try:
                data = json.loads(post_body.decode('utf-8'))
                if data.get("bot_token") and data.get("chat_id"):
                    telegram_notifier.bot_token = data["bot_token"]
                    telegram_notifier.chat_id = data["chat_id"]
                
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                test_msg = (
                    "<b>Sistema de Vagas (Pelotas & Rio Grande)</b>\n\n"
                    "Conexao com Telegram realizada com sucesso!\n"
                    "Voce recebera alertas aqui sempre que novas vagas compativeis forem encontradas."
                )
                sent = loop.run_until_complete(telegram_notifier.send_message(test_msg))
                loop.close()
                if sent:
                    return self._send_json({"success": True, "message": "Alerta enviado no Telegram com sucesso!"})
                return self._send_json({"success": False, "detail": "Nao foi possivel enviar mensagem. Verifique Token e Chat ID."}, 400)
            except Exception as e:
                return self._send_json({"success": False, "error": str(e)}, 400)

        self._send_json({"error": "Rota não encontrada"}, 404)

    def do_PATCH(self):
        parsed = urlparse(self.path)
        path = parsed.path
        content_len = int(self.headers.get('Content-Length', 0))
        post_body = self.rfile.read(content_len) if content_len > 0 else b'{}'
        try:
            data = json.loads(post_body.decode('utf-8'))
        except Exception:
            data = {}

        if "/api/jobs/" in path and "/status" in path:
            try:
                job_id = int(path.split("/api/jobs/")[1].split("/status")[0])
                new_status = data.get("status")
                if new_status:
                    update_job(job_id, {"status": new_status})
                    sync_static_files()
                    return self._send_json({"success": True, "status": new_status})
            except Exception as e:
                return self._send_json({"success": False, "error": str(e)}, 400)

        elif "/api/jobs/" in path and "/notes" in path:
            try:
                job_id = int(path.split("/api/jobs/")[1].split("/notes")[0])
                notes = data.get("notes", "")
                update_job(job_id, {"notes": notes})
                sync_static_files()
                return self._send_json({"success": True, "notes": notes})
            except Exception as e:
                return self._send_json({"success": False, "error": str(e)}, 400)

        self._send_json({"error": "Rota não encontrada"}, 404)

    def do_DELETE(self):
        parsed = urlparse(self.path)
        path = parsed.path
        if path.startswith("/api/jobs/"):
            try:
                job_id = int(path.split("/api/jobs/")[1])
                success = delete_job(job_id)
                if success:
                    return self._send_json({"success": True, "message": "Vaga excluída"})
                return self._send_json({"success": False, "error": "Vaga não encontrada"}, 404)
            except Exception as e:
                return self._send_json({"success": False, "error": str(e)}, 400)
        self._send_json({"error": "Rota não encontrada"}, 404)

def run_server(port=8000):
    print("=" * 60)
    print("   [VAGAS RS] SISTEMA DE VAGAS (PELOTAS & RIO GRANDE)")
    print("=" * 60)
    print("1. Inicializando banco de dados SQLite...")
    init_db()
    sync_jobs_from_json()

    server_address = ("", port)
    httpd = HTTPServer(server_address, JobAggregatorHandler)
    print(f"\n[OK] Servidor ativo e pronto!")
    print(f"[LINK] Acesse no navegador: http://localhost:{port}")
    print("=" * 60)
    print("Pressione CTRL+C para encerrar o servidor.\n")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nEncerrando servidor...")
        httpd.server_close()

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    run_server(port)
