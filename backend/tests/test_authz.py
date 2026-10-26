"""Cierre de accesos anónimos y fuga de secretos (WP1)."""
from app.models.card import Card, CardStatus
from app.models.setting import SystemSetting
from app.models.user import User, UserRole

API = "/api/v1"


def test_create_user_requires_authentication(client):
    response = client.post(
        f"{API}/users/",
        json={
            "email": "intruso@example.com",
            "full_name": "Intruso",
            "role": "admin",
            "password": "Segura2026x",
        },
    )
    assert response.status_code == 401


def test_create_user_rejects_non_admin(client, user_factory, auth_headers):
    parent = user_factory(role=UserRole.PADRE)
    response = client.post(
        f"{API}/users/",
        json={
            "email": "admin2@example.com",
            "full_name": "Casi Admin",
            "role": "admin",
            "password": "Segura2026x",
        },
        headers=auth_headers(parent),
    )
    assert response.status_code == 403


def test_admin_can_create_user(client, user_factory, auth_headers):
    admin = user_factory(role=UserRole.ADMIN)
    response = client.post(
        f"{API}/users/",
        json={
            "email": "nuevo-admin@example.com",
            "full_name": "Nuevo Admin",
            "role": "admin",
            "password": "Segura2026x",
        },
        headers=auth_headers(admin),
    )
    assert response.status_code == 201
    assert response.json()["role"] == "admin"


def test_settings_are_private_and_never_leak_password(client, db, user_factory, auth_headers):
    db.add(SystemSetting(key="smtp_pass", value="super-secreto"))
    db.add(SystemSetting(key="school_name", value="Colegio Test"))
    db.commit()

    anonymous = client.get(f"{API}/settings/")
    assert anonymous.status_code == 401

    admin = user_factory(role=UserRole.ADMIN)
    response = client.get(f"{API}/settings/", headers=auth_headers(admin))
    assert response.status_code == 200
    data = response.json()
    assert data["smtp_pass"] == ""
    assert data["smtp_pass_set"] is True
    assert "super-secreto" not in response.text


def test_public_settings_only_expose_allowlist(client, db):
    db.add(SystemSetting(key="smtp_pass", value="super-secreto"))
    db.add(SystemSetting(key="school_name", value="Colegio Test"))
    db.add(SystemSetting(key="school_logo", value="/uploads/logo.png"))
    db.commit()

    response = client.get(f"{API}/settings/public")
    assert response.status_code == 200
    data = response.json()
    assert data == {
        "school_name": "Colegio Test",
        "school_logo": "/uploads/logo.png",
    }


def test_blank_smtp_password_keeps_existing_secret(client, db, user_factory, auth_headers):
    db.add(SystemSetting(key="smtp_pass", value="super-secreto"))
    db.commit()

    admin = user_factory(role=UserRole.ADMIN)
    response = client.put(
        f"{API}/settings/",
        json={"smtp_pass": "", "school_name": "Otro Colegio"},
        headers=auth_headers(admin),
    )
    assert response.status_code == 200

    stored = db.query(SystemSetting).filter(SystemSetting.key == "smtp_pass").first()
    assert stored.value == "super-secreto"


def test_card_check_requires_staff_and_hides_grade(
    client, family_factory, user_factory, auth_headers
):
    _, _, card = family_factory()

    anonymous = client.get(f"{API}/cards/check/{card.uid}")
    assert anonymous.status_code == 401

    seller = user_factory(role=UserRole.VENDEDOR)
    response = client.get(f"{API}/cards/check/{card.uid}", headers=auth_headers(seller))
    assert response.status_code == 200
    data = response.json()
    assert data["uid"] == card.uid
    assert set(data) == {"uid", "balance", "status", "owner_name", "owner_type"}
    assert "grade" not in data


def test_recent_sales_requires_staff(client, user_factory, auth_headers):
    assert client.get(f"{API}/sales/recent").status_code == 401

    parent = user_factory(role=UserRole.PADRE)
    assert client.get(f"{API}/sales/recent", headers=auth_headers(parent)).status_code == 403

    seller = user_factory(role=UserRole.VENDEDOR)
    assert client.get(f"{API}/sales/recent", headers=auth_headers(seller)).status_code == 200


def test_parent_can_only_block_and_not_change_limit(
    client, db, family_factory, auth_headers
):
    parent, _, card = family_factory(daily_limit="5000.00")
    headers = auth_headers(parent)

    limit_change = client.put(
        f"{API}/cards/{card.uid}",
        json={"daily_limit": 999999},
        headers=headers,
    )
    assert limit_change.status_code == 403

    unblock = client.put(
        f"{API}/cards/{card.uid}",
        json={"status": "active"},
        headers=headers,
    )
    assert unblock.status_code == 403

    block = client.put(
        f"{API}/cards/{card.uid}",
        json={"status": "blocked"},
        headers=headers,
    )
    assert block.status_code == 200
    assert block.json()["status"] == "blocked"


def test_employee_cannot_change_own_limit(
    client, employee_card_factory, auth_headers
):
    employee, card = employee_card_factory()
    response = client.put(
        f"{API}/cards/{card.uid}",
        json={"daily_limit": 0},
        headers=auth_headers(employee),
    )
    assert response.status_code == 403


def test_removed_gateways_and_simulate_endpoints_are_gone(client):
    assert client.post(f"{API}/recharges/simulate-pse", json={}).status_code == 404
    assert client.post(f"{API}/payments/notify/wompi", json={}).status_code == 404
    assert client.post(f"{API}/payments/notify/mercadopago", json={}).status_code == 404


def test_import_status_requires_admin(client):
    assert client.get(f"{API}/import/status/abc").status_code == 401
