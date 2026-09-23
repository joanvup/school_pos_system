import sys
import os

# Añadir el directorio actual al path para que Python encuentre el módulo 'app'
sys.path.append(os.getcwd())

from app.db.session import SessionLocal
from app.db.base import Base # <--- Esto carga TODOS los modelos (User, Card, Student, etc.)
from app.models.user import User, UserRole
from app.core.security import get_password_hash

def fix():
    db = SessionLocal()
    admin_email = "admin@school.com"
    nueva_clave = "admin123_seguro"
    
    try:
        # Buscamos al usuario
        user = db.query(User).filter(User.email == admin_email).first()
        
        if user:
            # Generamos el hash de la nueva contraseña
            user.hashed_password = get_password_hash(nueva_clave)
            user.is_active = True
            user.role = UserRole.ADMIN
            db.commit()
            print("\n" + "="*50)
            print("EXITO: Contrasena restaurada.")
            print(f"Usuario: {admin_email}")
            print(f"Clave: {nueva_clave}")
            print("="*50 + "\n")
        else:
            user = User(
                full_name="Administrador del Sistema",
                email=admin_email,
                hashed_password=get_password_hash(nueva_clave),
                role=UserRole.ADMIN,
                is_active=True
            )
            db.add(user)
            db.commit()
            print("\n" + "="*50)
            print("EXITO: Usuario administrador creado.")
            print(f"Usuario: {admin_email}")
            print(f"Clave: {nueva_clave}")
            print("="*50 + "\n")
            
    except Exception as e:
        print(f"ERROR: Ocurrio un error inesperado: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    fix()