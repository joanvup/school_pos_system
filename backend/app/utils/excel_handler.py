from app.core.config import settings
from app.core.security import get_password_hash, validate_password
from app.models.user import User, Student, UserRole
import pandas as pd
from sqlalchemy.orm import Session 
import io
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from typing import Callable, Optional


def _row_password(row, column: str, required: bool) -> str | None:
    """Lee y valida una contraseña de la fila. None si no viene y no es obligatoria."""
    if column not in row or pd.isna(row[column]) or not str(row[column]).strip():
        if required:
            raise ValueError(f"La columna '{column}' es obligatoria para usuarios nuevos")
        return None
    return validate_password(str(row[column]).strip())

def generate_students_template() -> io.BytesIO:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Estudiantes y Padres"

    headers = [
        "parent_email",
        "parent_name",
        "student_name",
        "grade",
        "parent_password"
    ]

    sample_data = [
        ["padre1@ejemplo.com", "Carlos Perez", "Juan Perez", "10-A", "Padre2026Seguro"],
        ["padre1@ejemplo.com", "Carlos Perez", "Maria Perez", "6-B", "Padre2026Seguro"],
        ["padre2@ejemplo.com", "Ana Gomez", "Santiago Gomez", "11-C", "claveSegura123"],
    ]

    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="1E40AF", end_color="1E40AF", fill_type="solid")
    center_alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    thin_border = Border(
        left=Side(style='thin', color='D1D5DB'),
        right=Side(style='thin', color='D1D5DB'),
        top=Side(style='thin', color='D1D5DB'),
        bottom=Side(style='thin', color='D1D5DB')
    )

    ws.append(headers)
    for col_num in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=col_num)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = center_alignment
        cell.border = thin_border

    for row_idx, row_data in enumerate(sample_data, start=2):
        ws.append(row_data)
        for col_num in range(1, len(row_data) + 1):
            cell = ws.cell(row=row_idx, column=col_num)
            cell.border = thin_border
            cell.alignment = Alignment(vertical="center")

    for col in ws.columns:
        max_len = max(len(str(cell.value or '')) for cell in col)
        col_letter = get_column_letter(col[0].column)
        ws.column_dimensions[col_letter].width = max(max_len + 5, 18)

    ws.row_dimensions[1].height = 28

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output

def generate_employees_template() -> io.BytesIO:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Empleados y Staff"

    headers = [
        "email",
        "full_name",
        "password"
    ]

    sample_data = [
        ["docente1@colegio.edu.co", "Roberto Gomez", "Empleado2026"],
        ["staff1@colegio.edu.co", "Laura Martinez", "claveSegura2026"],
        ["mantenimiento1@colegio.edu.co", "Pedro Sanchez", "Empleado2026"],
    ]

    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="1E40AF", end_color="1E40AF", fill_type="solid")
    center_alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    thin_border = Border(
        left=Side(style='thin', color='D1D5DB'),
        right=Side(style='thin', color='D1D5DB'),
        top=Side(style='thin', color='D1D5DB'),
        bottom=Side(style='thin', color='D1D5DB')
    )

    ws.append(headers)
    for col_num in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=col_num)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = center_alignment
        cell.border = thin_border

    for row_idx, row_data in enumerate(sample_data, start=2):
        ws.append(row_data)
        for col_num in range(1, len(row_data) + 1):
            cell = ws.cell(row=row_idx, column=col_num)
            cell.border = thin_border
            cell.alignment = Alignment(vertical="center")

    for col in ws.columns:
        max_len = max(len(str(cell.value or '')) for cell in col)
        col_letter = get_column_letter(col[0].column)
        ws.column_dimensions[col_letter].width = max(max_len + 5, 20)

    ws.row_dimensions[1].height = 28

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output

def _report_progress(progress_cb: Optional[Callable[[int], None]], percent: int) -> None:
    if progress_cb is not None:
        progress_cb(max(0, min(100, percent)))


def process_students_file(
    file_content,
    db: Session,
    progress_cb: Optional[Callable[[int], None]] = None,
):
    try:
        df = pd.read_excel(io.BytesIO(file_content))
        df.columns = [c.lower().strip().replace(" ", "_") for c in df.columns]
    except Exception as e:
        return {"error": f"Archivo inválido: {str(e)}"}

    if len(df) > settings.MAX_IMPORT_ROWS:
        return {
            "error": (
                f"El archivo tiene {len(df)} filas y el máximo es "
                f"{settings.MAX_IMPORT_ROWS}"
            )
        }

    total_rows = len(df) 
    res = {"total": total_rows, "created": 0, "updated": 0, "errors": []}

    for index, row in df.iterrows():
        _report_progress(progress_cb, int(((index + 1) / total_rows) * 100))
        
        try:
            email = str(row["parent_email"]).strip()
            parent_name = str(row["parent_name"]).strip()
            student_name = str(row["student_name"]).strip()
            grade = str(row["grade"]).strip()
            
            # 1. GESTIÓN DEL PADRE
            parent = db.query(User).filter(User.email == email).first()
            if parent:
                if parent.role != UserRole.PADRE:
                    raise ValueError("El correo pertenece a un usuario que no es padre")
                # ACTUALIZAR PADRE
                parent.full_name = parent_name
                new_password = _row_password(row, "parent_password", required=False)
                if new_password:
                    parent.hashed_password = get_password_hash(new_password)
                    parent.must_change_password = True
                res["updated"] += 0.5 # Marcamos media actualización (padre)
            else:
                # CREAR PADRE
                pwd = _row_password(row, "parent_password", required=True)
                parent = User(
                    email=email, full_name=parent_name,
                    hashed_password=get_password_hash(pwd), role=UserRole.PADRE,
                    must_change_password=True,
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

def process_employees_file(
    file_content,
    db: Session,
    progress_cb: Optional[Callable[[int], None]] = None,
):
    try:
        df = pd.read_excel(io.BytesIO(file_content))
        df.columns = [c.lower().strip().replace(" ", "_") for c in df.columns]
    except Exception as e:
        return {"error": str(e)}

    if len(df) > settings.MAX_IMPORT_ROWS:
        return {
            "error": (
                f"El archivo tiene {len(df)} filas y el máximo es "
                f"{settings.MAX_IMPORT_ROWS}"
            )
        }

    total_rows = len(df)
    res = {"total": total_rows, "created": 0, "updated": 0, "errors": []}

    for index, row in df.iterrows():
        _report_progress(progress_cb, int(((index + 1) / total_rows) * 100))
        try:
            email = str(row["email"]).strip()
            full_name = str(row["full_name"]).strip()
            
            user = db.query(User).filter(User.email == email).first()
            if user:
                if user.role != UserRole.EMPLEADO:
                    raise ValueError("El correo pertenece a un usuario que no es empleado")
                # ACTUALIZAR EMPLEADO (nunca rol ni contraseña sin valor explícito)
                user.full_name = full_name
                new_password = _row_password(row, "password", required=False)
                if new_password:
                    user.hashed_password = get_password_hash(new_password)
                    user.must_change_password = True
                res["updated"] += 1
            else:
                # CREAR EMPLEADO
                pwd = _row_password(row, "password", required=True)
                new_user = User(
                    email=email, full_name=full_name, role=UserRole.EMPLEADO,
                    hashed_password=get_password_hash(pwd),
                    must_change_password=True,
                )
                db.add(new_user)
                res["created"] += 1
            
            db.commit()
        except Exception as e:
            db.rollback()
            res["errors"].append(f"Fila {index+2}: {str(e)}")
            
    return res