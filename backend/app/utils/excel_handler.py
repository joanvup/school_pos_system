from app.core.security import get_password_hash
from app.models.user import User, Student, UserRole
import pandas as pd
from sqlalchemy.orm import Session 
import io

def process_students_file(file_content, db: Session, task_id: str, progress_dict: dict):
    try:
        df = pd.read_excel(io.BytesIO(file_content))
        df.columns = [c.lower().strip().replace(" ", "_") for c in df.columns]
    except Exception as e:
        return {"error": f"Archivo inválido: {str(e)}"}

    total_rows = len(df) 
    res = {"total": total_rows, "created": 0, "updated": 0, "errors": []}

    for index, row in df.iterrows():
        if task_id in progress_dict:
            progress_dict[task_id]["progress"] = int(((index + 1) / total_rows) * 100)
        
        try:
            email = str(row["parent_email"]).strip()
            parent_name = str(row["parent_name"]).strip()
            student_name = str(row["student_name"]).strip()
            grade = str(row["grade"]).strip()
            
            # 1. GESTIÓN DEL PADRE
            parent = db.query(User).filter(User.email == email).first()
            if parent:
                # ACTUALIZAR PADRE
                parent.full_name = parent_name
                if "parent_password" in row and pd.notnull(row["parent_password"]):
                    parent.hashed_password = get_password_hash(str(row["parent_password"]))
                res["updated"] += 0.5 # Marcamos media actualización (padre)
            else:
                # CREAR PADRE
                pwd = str(row.get("parent_password", "123456"))
                parent = User(
                    email=email, full_name=parent_name, 
                    hashed_password=get_password_hash(pwd), role=UserRole.PADRE
                )
                db.add(parent)
                db.flush()
                res["created"] += 0.5

            # 2. GESTIÓN DEL ESTUDIANTE
            # Buscamos si este padre ya tiene un hijo con ese nombre
            student = db.query(Student).filter(
                Student.parent_id == parent.id, 
                Student.full_name == student_name
            ).first()

            if student:
                # ACTUALIZAR ESTUDIANTE
                student.grade = grade
                res["updated"] += 0.5
            else:
                # CREAR ESTUDIANTE
                new_st = Student(full_name=student_name, grade=grade, parent_id=parent.id)
                db.add(new_st)
                res["created"] += 0.5

            db.commit()
        except Exception as e:
            db.rollback()
            res["errors"].append(f"Fila {index+2}: {str(e)}")

    # Normalizar contadores (ya que un registro es Padre + Estudiante)
    res["created"] = int(res["created"])
    res["updated"] = int(res["updated"])
    return res

def process_employees_file(file_content, db: Session, task_id: str, progress_dict: dict):
    try:
        df = pd.read_excel(io.BytesIO(file_content))
        df.columns = [c.lower().strip().replace(" ", "_") for c in df.columns]
    except Exception as e:
        return {"error": str(e)}

    total_rows = len(df)
    res = {"total": total_rows, "created": 0, "updated": 0, "errors": []}

    for index, row in df.iterrows():
        if task_id in progress_dict:
            progress_dict[task_id]["progress"] = int(((index + 1) / total_rows) * 100)
        try:
            email = str(row["email"]).strip()
            full_name = str(row["full_name"]).strip()
            
            user = db.query(User).filter(User.email == email).first()
            if user:
                # ACTUALIZAR EMPLEADO
                user.full_name = full_name
                if "password" in row and pd.notnull(row["password"]):
                    user.hashed_password = get_password_hash(str(row["password"]))
                res["updated"] += 1
            else:
                # CREAR EMPLEADO
                pwd = str(row.get("password", "empleado123"))
                new_user = User(
                    email=email, full_name=full_name, role=UserRole.EMPLEADO,
                    hashed_password=get_password_hash(pwd)
                )
                db.add(new_user)
                res["created"] += 1
            
            db.commit()
        except Exception as e:
            db.rollback()
            res["errors"].append(f"Fila {index+2}: {str(e)}")
            
    return res