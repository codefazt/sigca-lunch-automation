"""
Sistema de notificaciones de SiGCABot.
Funciones independientes para enviar alertas de escritorio (Windows Toast)
y mensajes/fotos a Telegram vía la API HTTP directa.
"""

import os
import logging
import urllib.request
import urllib.parse
import uuid

logger = logging.getLogger("SiGCABot")

# ---------------------------------------------------------------------------
# Notificaciones de Escritorio — Windows Toast
# ---------------------------------------------------------------------------

def send_windows_toast(title, message):
    """
    Envía una notificación Toast nativa de Windows 10/11 usando la librería plyer.
    Evita abrir subprocesos de powershell.exe que levantan alarmas en antivirus (heurística).
    """
    logger.info(f"Enviando notificación Toast de Windows (plyer): {title} - {message}")
    try:
        from plyer import notification
        
        # Determinar icono (.ico)
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        icon_path = os.path.join(base_dir, "robot_hamburger_icon.ico")
        if not os.path.exists(icon_path):
            icon_path = None
            
        notification.notify(
            title=title,
            message=message,
            app_name="SiGCABot",
            app_icon=icon_path,
            timeout=7
        )
    except Exception as e:
        logger.warning(f"Fallo al enviar notificación con plyer: {e}")

# ---------------------------------------------------------------------------
# Notificaciones por Telegram — Mensajes de texto
# ---------------------------------------------------------------------------

def send_telegram_message(token, chat_id, message):
    """
    Envía un mensaje de texto (HTML) a un chat de Telegram.

    Args:
        token: Bot API Token de Telegram.
        chat_id: ID del chat destino.
        message: Texto del mensaje (puede incluir tags HTML).

    Returns:
        True si se envió con éxito, False en caso contrario.
    """
    if not token or not chat_id:
        logger.warning("Token o Chat ID de Telegram no configurados. Omitiendo notificación.")
        return False

    logger.info("Enviando mensaje de texto a Telegram...")
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = urllib.parse.urlencode({
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML"
    }).encode("utf-8")

    try:
        req = urllib.request.Request(url, data=data)
        with urllib.request.urlopen(req, timeout=10) as response:
            response.read()
            logger.info("Mensaje de Telegram enviado con éxito.")
            return True
    except Exception as e:
        if "getaddrinfo" in str(e) or "11001" in str(e) or "11002" in str(e):
            logger.error("Error al enviar mensaje a Telegram: Fallo de resolución DNS (verifica tu conexión a internet o si api.telegram.org está bloqueado)")
        else:
            logger.error(f"Error al enviar mensaje a Telegram: {e}")
        return False

# ---------------------------------------------------------------------------
# Notificaciones por Telegram — Fotos / Capturas de Pantalla
# ---------------------------------------------------------------------------

def send_telegram_photo(token, chat_id, photo_path, caption=None):
    """
    Envía una imagen (foto/captura de pantalla) a un chat de Telegram.

    Args:
        token: Bot API Token de Telegram.
        chat_id: ID del chat destino.
        photo_path: Ruta absoluta a la imagen PNG.
        caption: Texto opcional que acompaña la imagen.

    Returns:
        True si se envió con éxito, False en caso contrario.
    """
    if not token or not chat_id or not photo_path or not os.path.exists(photo_path):
        return False

    logger.info(f"Enviando captura de pantalla {photo_path} a Telegram...")
    url = f"https://api.telegram.org/bot{token}/sendPhoto"

    boundary = f"Boundary-{uuid.uuid4().hex}"
    parts = []

    # Campo: chat_id
    parts.append(f"--{boundary}\r\n".encode("utf-8"))
    parts.append(f'Content-Disposition: form-data; name="chat_id"\r\n\r\n{chat_id}\r\n'.encode("utf-8"))

    # Campo: caption (opcional)
    if caption:
        parts.append(f"--{boundary}\r\n".encode("utf-8"))
        parts.append(f'Content-Disposition: form-data; name="caption"\r\n\r\n{caption}\r\n'.encode("utf-8"))

    # Campo: photo (archivo binario)
    parts.append(f"--{boundary}\r\n".encode("utf-8"))
    filename = os.path.basename(photo_path)
    parts.append(
        f'Content-Disposition: form-data; name="photo"; filename="{filename}"\r\n'
        f'Content-Type: image/png\r\n\r\n'.encode("utf-8")
    )

    try:
        with open(photo_path, "rb") as f:
            parts.append(f.read())
        parts.append(f"\r\n--{boundary}--\r\n".encode("utf-8"))
        body = b"".join(parts)

        req = urllib.request.Request(url, data=body)
        req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
        req.add_header("Content-Length", str(len(body)))

        with urllib.request.urlopen(req, timeout=20) as response:
            response.read()
            logger.info("Foto de Telegram enviada con éxito.")
            return True
    except Exception as e:
        if "getaddrinfo" in str(e) or "11001" in str(e) or "11002" in str(e):
            logger.error("Error al enviar foto a Telegram: Fallo de resolución DNS (verifica tu conexión a internet o si api.telegram.org está bloqueado)")
        else:
            logger.error(f"Error al enviar foto a Telegram: {e}")
        return False

# ---------------------------------------------------------------------------
# Notificaciones por Correo Electrónico — SMTP (Gmail)
# ---------------------------------------------------------------------------

def send_email_notification(to_email, subject, body_html, image_path=None, sender_email=None, sender_password=None):
    """
    Envía un correo electrónico de notificación (HTML) usando SMTP de Gmail.

    Args:
        to_email: Correo destinatario (ej. correo corporativo).
        subject: Asunto del correo.
        body_html: Cuerpo del correo en formato HTML.
        image_path: Ruta a la captura de pantalla (.png) opcional.
        sender_email: Correo remitente (Gmail). Si no se pasa, se lee de .env.
        sender_password: Contraseña de aplicación de Gmail. Si no se pasa, se lee de .env.

    Returns:
        True si se envió con éxito, False en caso contrario.
    """
    import smtplib
    from email.message import EmailMessage

    if not sender_email or not sender_password:
        from src.config import load_env_dict
        env = load_env_dict()
        sender_email = sender_email or env.get("SMTP_SENDER_EMAIL", "johancarmino346@gmail.com")
        sender_password = sender_password or env.get("SMTP_SENDER_PASSWORD", "")

    # Limpiar espacios en blanco
    sender_email = (sender_email or "").strip()
    sender_password = (sender_password or "").strip()
    to_email = (to_email or "").strip()

    if not sender_email or not sender_password:
        logger.warning("Credenciales SMTP de correo remitente no configuradas (SMTP_SENDER_EMAIL / SMTP_SENDER_PASSWORD). Omitiendo correo.")
        return False

    if not to_email:
        logger.warning("Correo destinatario no proporcionado. Omitiendo notificación por correo.")
        return False

    logger.info(f"Enviando notificación por correo electrónico a {to_email}...")

    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = f"SiGCABot Notificaciones <{sender_email}>"
    msg['To'] = to_email

    msg.set_content("SiGCABot Notificación (habilite la vista HTML en su cliente de correo para ver detalles).")
    msg.add_alternative(body_html, subtype='html')

    # Adjuntar captura de pantalla si existe
    if image_path and os.path.exists(image_path):
        try:
            with open(image_path, 'rb') as f:
                img_data = f.read()
            filename = os.path.basename(image_path)
            msg.add_attachment(img_data, maintype='image', subtype='png', filename=filename)
            logger.info(f"Captura de pantalla adjuntada al correo: {filename}")
        except Exception as e:
            logger.warning(f"No se pudo adjuntar la imagen {image_path} al correo: {e}")

    try:
        # Usamos SMTP SSL en puerto 465 (Gmail)
        with smtplib.SMTP_SSL('smtp.gmail.com', 465, timeout=15) as server:
            server.login(sender_email, sender_password)
            server.send_message(msg)
        logger.info("✅ Correo electrónico de notificación enviado con éxito.")
        return True
    except Exception as e:
        logger.error(f"❌ Error al enviar correo electrónico por SMTP: {e}")
        return False

