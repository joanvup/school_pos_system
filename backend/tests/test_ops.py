"""Importaciones persistentes y límites de solicitudes entre workers (Fase 3)."""
import io
import uuid

import pandas as pd

from app.api.api_v1.endpoints import data_import
from app.models.ops import ImportJob
from app.models.user import UserRole

API = "/api/v1"


def xlsx(rows) -> bytes:
    buffer = io.BytesIO()
    pd.DataFrame(rows).to_excel(buffer, index=False)
    return buffer.getvalue()


def test_import_status_only_visible_to_creator(client, db, user_factory, auth_headers):
    owner = user_factory(role=UserRole.ADMIN)
    other = user_factory(role=UserRole.ADMIN)
    job = ImportJob(id=str(uuid.uuid4()), user_id=owner.id, kind="students", progress=40)
    db.add(job)
    db.commit()

    assert client.get(f"{API}/import/status/{job.id}").status_code == 401

    owner_response = client.get(
        f"{API}/import/status/{job.id}", headers=auth_headers(owner)
    )
    assert owner_response.status_code == 200
    assert owner_response.json()["progress"] == 40
    assert owner_response.json()["status"] == "processing"

    other_response = client.get(
        f"{API}/import/status/{job.id}", headers=auth_headers(other)
    )
    assert other_response.status_code == 404


def test_import_status_rejects_unknown_task(client, user_factory, auth_headers):
    admin = user_factory(role=UserRole.ADMIN)
    response = client.get(
        f"{API}/import/status/{uuid.uuid4()}", headers=auth_headers(admin)
    )
    assert response.status_code == 404


def test_import_rejects_disguised_file(client, user_factory, auth_headers):
    admin = user_factory(role=UserRole.ADMIN)
    response = client.post(
        f"{API}/import/employees",
        files={"file": ("empleados.xlsx", b"no soy un zip", "application/octet-stream")},
        headers=auth_headers(admin),
    )
    assert response.status_code == 400


def test_import_creates_persisted_job(
    client, db, user_factory, auth_headers, monkeypatch
):
    started: list[str] = []
    monkeypatch.setattr(data_import, "run_async_import", lambda *args: started.append(args[0]))
    admin = user_factory(role=UserRole.ADMIN)

    response = client.post(
        f"{API}/import/employees",
        files={
            "file": (
                "empleados.xlsx",
                xlsx(
                    [
                        {
                            "email": "lote@test.local",
                            "full_name": "Empleado Lote",
                            "password": "ClaveSegura2026",
                        }
                    ]
                ),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
        headers=auth_headers(admin),
    )

    assert response.status_code == 200
    task_id = response.json()["task_id"]
    assert started == [task_id]

    job = db.query(ImportJob).filter(ImportJob.id == task_id).one()
    assert job.user_id == admin.id
    assert job.kind == "employees"
    assert job.status == "processing"


def test_password_recovery_is_rate_limited(client, db):
    payload = {"email": "recuperacion@example.com"}

    for _ in range(5):
        assert client.post(f"{API}/auth/password-recovery", json=payload).status_code == 200

    blocked = client.post(f"{API}/auth/password-recovery", json=payload)
    assert blocked.status_code == 429
    assert "Retry-After" in blocked.headers
