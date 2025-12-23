import sys
import os

# Añadir el directorio actual al path para que Python encuentre el módulo 'app'
sys.path.append(os.getcwd())

from app.db.session import SessionLocal
from app.db.base import Base # <--- Esto carga TODOS los modelos (User, Card, Student, etc.)
from app.models.user import User
from app.core.security import get_password_hash

def fix():
    db = SessionLocal()
    admin_email = "admin@school.com"
    
    try:
        # Buscamos al usuario
        user = db.query(User).filter(User.email == admin_email).first()
        
        if user:
            # Generamos el hash de la nueva contraseña
            nueva_clave = "admin123_seguro"
            user.hashed_password = get_password_hash(nueva_clave)
            
            db.commit()
            print(f"\n" + "="*50)
            print(f"✅ ÉXITO: Contraseña restaurada.")
            print(f"📧 Usuario: {admin_email}")
            print(f"🔑 Nueva Clave: {nueva_clave}")
            print("="*50 + "\n")
        else:
            print(f"❌ ERROR: No se encontró ningún usuario con el email: {admin_email}")
            
    except Exception as e:
        print(f"❌ Ocurrió un error inesperado: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    fix()