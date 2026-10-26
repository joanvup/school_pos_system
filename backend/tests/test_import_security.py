"""Importación masiva no puede tomar cuentas ni usar claves por defecto (WP1)."""
import io

import pandas as pd

from app.models.user import Student, User, UserRole
from app.utils.excel_handler import process_employees_file, process_students_file


def xlsx(rows):
    buffer = io.BytesIO()
    pd.DataFrame(rows).to_excel(buffer, index=False)
    return buffer.getvalue()


def test_employee_import_cannot_touch_admin(db, user_factory):
    admin = user_factory(role=UserRole.ADMIN, password="AdminClave2026")
    original_hash = admin.hashed_password

    result = process_employees_file(
        xlsx([{"email": admin.email, "full_name": "Secuestrado", "password": "OtraClave2026"}]),
        db,
    )

    db.refresh(admin)
    assert result["created"] == 0
    assert result["updated"] == 0
    assert len(result["errors"]) == 1
    assert admin.role == UserRole.ADMIN
    assert admin.full_name != "Secuestrado"
    assert admin.hashed_password == original_hash


def test_new_employee_requires_explicit_password(db):
    result = process_employees_file(
        xlsx([{"email": "nuevo@test.local", "full_name": "Nuevo Empleado"}]),
        db,
    )

    assert result["created"] == 0
    assert len(result["errors"]) == 1
    assert db.query(User).filter(User.email == "nuevo@test.local").first() is None


def test_new_employee_with_weak_password_is_rejected(db):
    result = process_employees_file(
        xlsx(
            [
                {
                    "email": "debil@test.local",
                    "full_name": "Clave Débil",
                    "password": "empleado123",
                }
            ]
        ),
        db,
    )

    assert result["created"] == 0
    assert len(result["errors"]) == 1


def test_new_employee_with_valid_password_is_created(db):
    result = process_employees_file(
        xlsx(
            [
                {
                    "email": "valido@test.local",
                    "full_name": "Empleado Válido",
                    "password": "ClaveSegura2026",
                }
            ]
        ),
        db,
    )

    user = db.query(User).filter(User.email == "valido@test.local").one()
    assert result["created"] == 1
    assert user.role == UserRole.EMPLEADO
    assert user.must_change_password is True


def test_existing_employee_without_password_keeps_it(db, user_factory):
    employee = user_factory(role=UserRole.EMPLEADO)
    original_hash = employee.hashed_password

    result = process_employees_file(
        xlsx([{"email": employee.email, "full_name": "Nombre Actualizado"}]),
        db,
    )

    db.refresh(employee)
    assert result["updated"] == 1
    assert employee.full_name == "Nombre Actualizado"
    assert employee.hashed_password == original_hash
    assert employee.role == UserRole.EMPLEADO


def test_student_import_cannot_touch_admin(db, user_factory):
    admin = user_factory(role=UserRole.ADMIN)
    original_hash = admin.hashed_password

    result = process_students_file(
        xlsx(
            [
                {
                    "parent_email": admin.email,
                    "parent_name": "Secuestrado",
                    "student_name": "Hijo Falso",
                    "grade": "1-A",
                    "parent_password": "OtraClave2026",
                }
            ]
        ),
        db,
    )

    db.refresh(admin)
    assert len(result["errors"]) == 1
    assert admin.full_name != "Secuestrado"
    assert admin.hashed_password == original_hash


def test_new_parent_requires_password(db):
    result = process_students_file(
        xlsx(
            [
                {
                    "parent_email": "padre-nuevo@test.local",
                    "parent_name": "Padre Nuevo",
                    "student_name": "Estudiante Nuevo",
                    "grade": "2-B",
                }
            ]
        ),
        db,
    )

    assert result["created"] == 0
    assert len(result["errors"]) == 1
    assert db.query(User).filter(User.email == "padre-nuevo@test.local").first() is None


def test_new_parent_and_student_are_created(db):
    result = process_students_file(
        xlsx(
            [
                {
                    "parent_email": "padre-ok@test.local",
                    "parent_name": "Padre Correcto",
                    "student_name": "Estudiante Correcto",
                    "grade": "3-C",
                    "parent_password": "ClaveSegura2026",
                }
            ]
        ),
        db,
    )

    parent = db.query(User).filter(User.email == "padre-ok@test.local").one()
    assert result["created"] == 1
    assert parent.role == UserRole.PADRE
    assert parent.must_change_password is True
    assert db.query(Student).filter(Student.parent_id == parent.id).count() == 1


def test_import_reports_progress_through_callback(db):
    seen: list[int] = []

    result = process_employees_file(
        xlsx(
            [
                {
                    "email": "progreso@test.local",
                    "full_name": "Empleado Progreso",
                    "password": "ClaveSegura2026",
                }
            ]
        ),
        db,
        seen.append,
    )

    assert result["created"] == 1
    assert seen == [100]


def test_import_rejects_files_over_row_cap(db, monkeypatch):
    from app.utils import excel_handler

    monkeypatch.setattr(excel_handler.settings, "MAX_IMPORT_ROWS", 1)

    result = process_employees_file(
        xlsx(
            [
                {"email": "a@test.local", "full_name": "A", "password": "ClaveSegura2026"},
                {"email": "b@test.local", "full_name": "B", "password": "ClaveSegura2026"},
            ]
        ),
        db,
    )

    assert "máximo" in result["error"]
    assert db.query(User).filter(User.email.in_(["a@test.local", "b@test.local"])).count() == 0
