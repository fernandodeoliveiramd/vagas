import os
import httpx
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

class TelegramNotifier:
    def __init__(self):
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
        
    def is_configured(self) -> bool:
        return bool(self.bot_token and self.chat_id)

    async def send_message(self, text: str) -> bool:
        if not self.is_configured():
            logger.warning("[Telegram] Bot token ou Chat ID não configurados. Pulando notificação.")
            return False
            
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": False
        }
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(url, json=payload)
                return resp.status_code == 200
        except Exception as e:
            logger.error(f"[Telegram] Erro ao enviar mensagem: {e}")
            return False

    async def notify_new_job(self, job: Dict[str, Any]) -> bool:
        """
        Formata uma mensagem elegante no Telegram para nova vaga encontrada
        """
        title = job.get("title", "Vaga")
        company = job.get("company", "Confidencial")
        location = job.get("location", "Pelotas / Rio Grande")
        work_model = job.get("work_model", "Presencial")
        salary = job.get("salary", "A combinar")
        url = job.get("url", "#")
        source = job.get("source", "Web")
        category = job.get("category", "")
        
        icon = "⚡" if "eletric" in category else "💻" if "tecno" in category else "📊"
        
        msg = (
            f"🔔 <b>NOVA OPORTUNIDADE ENCONTRADA!</b> {icon}\n\n"
            f"💼 <b>Cargo:</b> {title}\n"
            f"🏢 <b>Empresa:</b> {company}\n"
            f"📍 <b>Local:</b> {location} ({work_model})\n"
            f"💰 <b>Salário:</b> {salary}\n"
            f"🌐 <b>Origem:</b> {source}\n\n"
            f"🔗 <a href='{url}'>Clique aqui para ver a vaga e se candidatar</a>"
        )
        return await self.send_message(msg)

telegram_notifier = TelegramNotifier()
