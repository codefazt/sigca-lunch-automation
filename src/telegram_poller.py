"""
Escuchador de comandos de Telegram para SiGCABot.
Hace polling a la API de Telegram buscando comandos /status y /health
enviados por el usuario autorizado, y responde con el estado del bot.
"""

import json
import html
import time
import logging
import urllib.request

from src.config import load_status, load_env_dict
from src.notifications import send_telegram_message
from src import state

logger = logging.getLogger("SiGCABot")


def start_telegram_poller():
    """
    Loop de polling de Telegram para escuchar comandos de salud.
    Corre en un hilo secundario y verifica stop_threads para salir.
    """
    last_update_id = 0
    logger.info("Hilo Telegram Poller iniciado para escuchar comandos de salud (/status, /health).")

    while not state.stop_threads:
        env = load_env_dict()
        token = env.get("TELEGRAM_TOKEN")
        allowed_chat_id = env.get("TELEGRAM_CHAT_ID")

        if not token or not allowed_chat_id:
            time.sleep(10)
            continue

        url = f"https://api.telegram.org/bot{token}/getUpdates?offset={last_update_id + 1}&timeout=5"
        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=8) as response:
                data = json.loads(response.read().decode("utf-8"))
                if data.get("ok") and data.get("result"):
                    for update in data["result"]:
                        last_update_id = update["update_id"]
                        message = update.get("message")
                        if not message:
                            continue

                        chat = message.get("chat")
                        text = message.get("text", "").strip()

                        if chat and str(chat.get("id")) == str(allowed_chat_id):
                            if text in ["/status", "/health"]:
                                status_info = load_status()
                                bot_state = "ACTIVO ✅" if status_info.get("is_active", True) else "PAUSADO ⏸️"
                                last_run = status_info.get("last_run_timestamp", "Nunca")
                                last_status = status_info.get("last_run_status", "N/A").upper()

                                response_msg = (
                                    f"🤖 <b>SiGCA Bot - Estado Actual</b>:\n"
                                    f"- <b>Estatus de Automatización:</b> {html.escape(bot_state)}\n"
                                    f"- <b>Última ejecución:</b> {html.escape(last_run)}\n"
                                    f"- <b>Resultado:</b> {html.escape(last_status)}\n\n"
                                    f"Servidor Health Check disponible localmente."
                                )
                                send_telegram_message(token, allowed_chat_id, response_msg)
        except Exception:
            pass  # Silenciar fallos de conexión temporales

        time.sleep(4)
