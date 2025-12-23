import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from sqlalchemy.orm import Session
from app.models.setting import SystemSetting

def send_recovery_email(db: Session, recipient_email: str, token: str):
    # 1. Obtener configuración SMTP de la base de datos
    settings = db.query(SystemSetting).all()
    conf = {s.key: s.value for s in settings}

    # Validar que existan los datos necesarios
    required = ['smtp_host', 'smtp_port', 'smtp_user', 'smtp_pass', 'school_name']
    if not all(k in conf for k in required):
        print("Error: Configuración SMTP incompleta en la base de datos")
        return False

    # 2. Configurar el mensaje
    msg = MIMEMultipart()
    msg['From'] = f"{conf.get('smtp_from_name', 'Soporte Escolar')} <{conf['smtp_user']}>"
    msg['To'] = recipient_email
    msg['Subject'] = f"Recuperación de Contraseña - {conf['school_name']}"

    # Enlace al frontend (Asegúrate de que el puerto coincida con tu frontend)
    # En producción esto vendría de una variable de entorno
    link = f"http://localhost:5173/reset-password?token={token}"

    html = f"""
    <html>
        <body style="font-family: sans-serif; border: 1px solid #eee; padding: 20px; border-radius: 10px;">
            <h2 style="color: #3b82f6;">{conf['school_name']}</h2>
            <p>Has solicitado restablecer tu contraseña.</p>
            <p>Haz clic en el siguiente botón para continuar (expira en 15 minutos):</p>
            <a href="{link}" style="background-color: #3b82f6; color: white; padding: 12px 24px; text-decoration: none; border-radius: 8px; font-weight: bold; display: inline-block;">
                Restablecer Contraseña
            </a>
            <p style="margin-top: 20px; font-size: 12px; color: #888;">
                Si no solicitaste este cambio, puedes ignorar este correo.
            </p>
        </body>
    </html>
    """
    msg.attach(MIMEText(html, 'html'))

    # 3. Enviar
    try:
        server = smtplib.SMTP(conf['smtp_host'], int(conf['smtp_port']))
        server.starttls()
        server.login(conf['smtp_user'], conf['smtp_pass'])
        server.sendmail(conf['smtp_user'], recipient_email, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        print(f"Error enviando email: {e}")
        return False