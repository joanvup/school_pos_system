"""Observabilidad y límites de reportes (Fase 3)."""

import logging

from app.models.user import UserRole

API = "/api/v1"


def test_health_returns_request_id(client):
    response = client.get("/health")

    assert response.status_code == 200
    request_id = response.headers.get("X-Request-ID")
    assert request_id
    assert len(request_id) == 16
    assert all(character in "0123456789abcdef" for character in request_id)


def test_request_log_uses_route_template_without_uid(client, caplog):
    with caplog.at_level(logging.INFO, logger="app.request"):
        client.get(f"{API}/cards/check/UID-SECRETO-123")

    records = [
        record
        for record in caplog.records
        if record.getMessage() == "request"
        and getattr(record, "route", "").startswith(f"{API}/cards/check")
    ]
    assert records
    assert records[-1].route == f"{API}/cards/check/{{uid}}"
    assert records[-1].status == 401
    # El log de la app nunca incluye el UID; solo la plantilla de la ruta.
    assert all("UID-SECRETO-123" not in str(record.__dict__) for record in records)


def test_reports_limit_is_bounded(client, user_factory, auth_headers):
    admin = user_factory(role=UserRole.ADMIN)

    response = client.get(
        f"{API}/reports/sales-total?limit=100000", headers=auth_headers(admin)
    )

    assert response.status_code == 422


def test_reports_skip_rejects_negative(client, user_factory, auth_headers):
    admin = user_factory(role=UserRole.ADMIN)

    response = client.get(
        f"{API}/reports/sales-total?skip=-5", headers=auth_headers(admin)
    )

    assert response.status_code == 422


def test_student_balance_is_bounded(client, user_factory, auth_headers):
    admin = user_factory(role=UserRole.ADMIN)

    response = client.get(
        f"{API}/reports/student-balance/1?limit=999999", headers=auth_headers(admin)
    )

    assert response.status_code == 422
