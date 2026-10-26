import html
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from urllib.parse import quote

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.secret_store import decrypt_secret
from app.models.setting import SystemSetting

logger = logging.getLogger(__name__)


def send_recovery_email(db: Session, recipient_email: str, token: str):
    settings_rows = db.query(SystemSetting).all()
    conf = {s.key: s.value for s in settings_rows}

    required = ["smtp_host", "smtp_port", "smtp_user", "smtp_pass", "school_name"]
    if not all(k in conf for k in required):
        logger.error("Configuración SMTP incompleta en la base de datos")
        return False

    try:
        smtp_password = decrypt_secret(conf["smtp_pass"])
    except ValueError:
        logger.exception("No se pudo descifrar smtp_pass")
        return False

    school_name = html.escape(conf["school_name"])
    link = f"{settings.FRONTEND_URL}/reset-password?token={quote(token)}"
    safe_link = html.escape(link, quote=True)

    msg = MIMEMultipart()
    msg["From"] = f"{conf.get('smtp_from_name', 'Soporte Escolar')} <{conf['smtp_user']}>"
    msg["To"] = recipient_email
    msg["Subject"] = f"Recuperación de Contraseña - {conf['school_name']}"

    body = f"""
    <html>
        <body style="font-family: sans-serif; border: 1px solid #eee; padding: 20px; border-radius: 10px;">
            <h2 style="color: #3b82f6;">{school_name}</h2>
            <p>Has solicitado restablecer tu contraseña.</p>
            <p>Haz clic en el siguiente botón para continuar (expira en {settings.PASSWORD_RESET_EXPIRE_MINUTES} minutos):</p>
            <a href="{safe_link}" style="background-color: #3b82f6; color: white; padding: 12px 24px; text-decoration: none; border-radius: 8px; font-weight: bold; display: inline-block;">
                Restablecer Contraseña
            </a>
            <p style="margin-top: 20px; font-size: 12px; color: #888;">
                Si no solicitaste este cambio, puedes ignorar este correo.
            </p>
        </body>
    </html>
    """
    msg.attach(MIMEText(body, "html"))

    try:
        with smtplib.SMTP(conf["smtp_host"], int(conf["smtp_port"]), timeout=15) as server:
            server.starttls()
            server.login(conf["smtp_user"], smtp_password)
            server.sendmail(conf["smtp_user"], recipient_email, msg.as_string())
        return True
    except Exception:
        logger.exception("Error enviando el correo de recuperación")
        return False
