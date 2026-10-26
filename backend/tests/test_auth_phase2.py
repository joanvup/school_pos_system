"""Autenticación Fase 2: JWT, cookies, CSRF, reset, lockout y secretos."""
from datetime import datetime, timedelta, timezone

import pytest
from jose import jwt

from app.api.api_v1.endpoints import auth as auth_endpoint
from app.core import security
from app.core.config import settings
from app.core.secret_store import decrypt_secret
from app.crud import crud_password_reset
from app.models.password_reset_token import PasswordResetToken
from app.models.setting import SystemSetting
from app.models.user import User, UserRole

API = "/api/v1"
PASSWORD = "Segura2026x"


def _login(client, email, password=PASSWORD):
    return client.post(
        f"{API}/auth/login/access-token",
        data={"username": email, "password": password},
    )


def _csrf_headers(client):
    return {settings.CSRF_HEADER_NAME: client.cookies.get(settings.CSRF_COOKIE_NAME)}


def test_access_token_has_hardened_claims(user_factory):
    user = user_factory()
    token = security.create_access_token(user.id, user.token_version)
    payload = jwt.decode(
        token,
        settings.SECRET_KEY,
        algorithms=[security.ALGORITHM],
        audience=settings.JWT_AUDIENCE,
        issuer=settings.JWT_ISSUER,
    )
    assert payload["sub"] == str(user.id)
    assert payload["typ"] == "access"
    assert payload["iss"] == settings.JWT_ISSUER
    assert payload["aud"] == settings.JWT_AUDIENCE
    assert payload["jti"]
    assert payload["ver"] == 0


def test_token_with_wrong_type_or_expiry_is_rejected(client, user_factory):
    user = user_factory()
    now = datetime.now(timezone.utc)
    wrong_type = jwt.encode(
        {
            "sub": str(user.id),
            "typ": "refresh",
            "iss": settings.JWT_ISSUER,
            "aud": settings.JWT_AUDIENCE,
            "iat": now,
            "exp": now + timedelta(minutes=5),
            "ver": 0,
        },
        settings.SECRET_KEY,
        algorithm=security.ALGORITHM,
    )
    expired = security.create_access_token(
        user.id, user.token_version, timedelta(seconds=-5)
    )

    for token in (wrong_type, expired):
        response = client.get(
            f"{API}/users/me", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 401


def test_token_version_revokes_previous_tokens(client, db, user_factory):
    user = user_factory()
    stale_headers = {
        "Authorization": f"Bearer {security.create_access_token(user.id, 0)}"
    }
    assert client.get(f"{API}/users/me", headers=stale_headers).status_code == 200

    user.token_version = 1
    db.commit()

    response = client.get(f"{API}/users/me", headers=stale_headers)
    assert response.status_code == 401
    assert "Sesión expirada" in response.json()["detail"]


def test_login_sets_httponly_cookie_and_csrf(client, user_factory):
    user = user_factory(role=UserRole.ADMIN)
    response = _login(client, user.email)
    assert response.status_code == 200
    assert response.json()["expires_in"] == settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    assert response.json()["must_change_password"] is False

    set_cookie = " ".join(response.headers.get_list("set-cookie"))
    assert settings.AUTH_COOKIE_NAME in set_cookie
    assert "HttpOnly" in set_cookie

    assert client.cookies.get(settings.AUTH_COOKIE_NAME)
    assert client.cookies.get(settings.CSRF_COOKIE_NAME)
    assert client.get(f"{API}/users/me").status_code == 200


def test_cookie_session_requires_csrf_for_writes(client, db, user_factory):
    user = user_factory()
    _login(client, user.email)

    blocked = client.post(f"{API}/auth/logout-all")
    assert blocked.status_code == 403

    allowed = client.post(
        f"{API}/auth/logout-all", headers=_csrf_headers(client)
    )
    assert allowed.status_code == 200

    db.refresh(user)
    assert user.token_version == 1


def test_logout_clears_session(client, user_factory):
    user = user_factory()
    _login(client, user.email)
    assert client.get(f"{API}/users/me").status_code == 200

    assert client.post(f"{API}/auth/logout").status_code == 200
    assert client.get(f"{API}/users/me").status_code == 401


def test_login_lockout_is_uniform_and_expires(client, db, user_factory):
    user = user_factory()
    unknown = _login(client, "nadie@example.com", "OtraClave2026")
    wrong = _login(client, user.email, "OtraClave2026")
    assert unknown.status_code == wrong.status_code == 401
    assert unknown.json()["detail"] == wrong.json()["detail"]

    for _ in range(settings.MAX_FAILED_LOGIN_ATTEMPTS - 1):
        assert _login(client, user.email, "OtraClave2026").status_code == 401

    db.refresh(user)
    assert user.locked_until is not None
    assert _login(client, user.email).status_code == 429

    user.locked_until = security.utcnow() - timedelta(seconds=1)
    db.commit()
    assert _login(client, user.email).status_code == 200


def test_must_change_password_blocks_and_revokes(
    client, db, user_factory, auth_headers
):
    user = user_factory(role=UserRole.ADMIN)
    user.must_change_password = True
    db.commit()
    headers = auth_headers(user)

    assert client.get(f"{API}/users/me", headers=headers).status_code == 200
    assert client.get(f"{API}/users/", headers=headers).status_code == 403

    wrong = client.post(
        f"{API}/auth/change-password",
        json={"current_password": "OtraClave2026", "new_password": "NuevaClave2026"},
        headers=headers,
    )
    assert wrong.status_code == 400

    changed = client.post(
        f"{API}/auth/change-password",
        json={"current_password": PASSWORD, "new_password": "NuevaClave2026"},
        headers=headers,
    )
    assert changed.status_code == 200

    assert client.get(f"{API}/users/", headers=headers).status_code == 401

    relogin = _login(client, user.email, "NuevaClave2026")
    assert relogin.status_code == 200
    assert relogin.json()["must_change_password"] is False


def test_admin_password_reset_forces_change_and_revokes(
    client, db, user_factory, auth_headers
):
    admin = user_factory(role=UserRole.ADMIN)
    target = user_factory()
    stale = auth_headers(target)

    response = client.put(
        f"{API}/users/{target.id}",
        json={"password": "Temporal2026"},
        headers=auth_headers(admin),
    )
    assert response.status_code == 200

    db.refresh(target)
    assert target.must_change_password is True
    assert client.get(f"{API}/users/me", headers=stale).status_code == 401


def test_password_recovery_and_one_time_reset(
    client, db, user_factory, monkeypatch
):
    user = user_factory()
    captured = {}

    def fake_send(db_session, recipient_email, token):
        captured["email"] = recipient_email
        captured["token"] = token
        return True

    monkeypatch.setattr(auth_endpoint, "send_recovery_email", fake_send)

    response = client.post(
        f"{API}/auth/password-recovery", json={"email": user.email}
    )
    assert response.status_code == 200

    rows = (
        db.query(PasswordResetToken)
        .filter(PasswordResetToken.user_id == user.id)
        .all()
    )
    assert len(rows) == 1
    assert rows[0].token_hash == crud_password_reset.hash_token(captured["token"])
    assert rows[0].token_hash != captured["token"]
    assert rows[0].used_at is None

    new_password = "NuevaClave2026"
    reset = client.post(
        f"{API}/auth/reset-password",
        json={"token": captured["token"], "new_password": new_password},
    )
    assert reset.status_code == 200

    db.refresh(rows[0])
    db.refresh(user)
    assert rows[0].used_at is not None
    assert security.verify_password(new_password, user.hashed_password)
    assert user.token_version == 1
    assert user.must_change_password is False

    replay = client.post(
        f"{API}/auth/reset-password",
        json={"token": captured["token"], "new_password": "OtraClave2026"},
    )
    assert replay.status_code == 400


def test_recovery_is_uniform_for_unknown_email(client, db):
    response = client.post(
        f"{API}/auth/password-recovery", json={"email": "nadie@example.com"}
    )
    assert response.status_code == 200
    assert db.query(PasswordResetToken).count() == 0


def test_expired_reset_token_is_rejected(client, db, user_factory):
    user = user_factory()
    raw_token = "token-de-prueba-suficientemente-largo-123456"
    db.add(
        PasswordResetToken(
            user_id=user.id,
            token_hash=crud_password_reset.hash_token(raw_token),
            purpose="password_reset",
            expires_at=security.utcnow() - timedelta(minutes=1),
        )
    )
    db.commit()

    response = client.post(
        f"{API}/auth/reset-password",
        json={"token": raw_token, "new_password": "NuevaClave2026"},
    )
    assert response.status_code == 400


def test_reset_rejects_weak_password(client, db, user_factory):
    user = user_factory()
    raw_token = "token-de-prueba-suficientemente-largo-abcdef"
    db.add(
        PasswordResetToken(
            user_id=user.id,
            token_hash=crud_password_reset.hash_token(raw_token),
            purpose="password_reset",
            expires_at=security.utcnow() + timedelta(minutes=5),
        )
    )
    db.commit()

    response = client.post(
        f"{API}/auth/reset-password",
        json={"token": raw_token, "new_password": "123456"},
    )
    assert response.status_code == 422


def test_inactive_user_gets_no_reset_token(
    client, db, user_factory, monkeypatch
):
    user = user_factory()
    user.is_active = False
    db.commit()

    monkeypatch.setattr(
        auth_endpoint, "send_recovery_email", lambda *args, **kwargs: True
    )
    response = client.post(
        f"{API}/auth/password-recovery", json={"email": user.email}
    )
    assert response.status_code == 200
    assert db.query(PasswordResetToken).count() == 0


def test_smtp_password_is_encrypted_at_rest(
    client, db, user_factory, auth_headers
):
    admin = user_factory(role=UserRole.ADMIN)
    response = client.put(
        f"{API}/settings/",
        json={"smtp_pass": "Secreta12345"},
        headers=auth_headers(admin),
    )
    assert response.status_code == 200

    stored = (
        db.query(SystemSetting)
        .filter(SystemSetting.key == "smtp_pass")
        .first()
    )
    assert stored.value.startswith("enc:v1:")
    assert "Secreta12345" not in stored.value
    assert decrypt_secret(stored.value) == "Secreta12345"

    data = client.get(f"{API}/settings/", headers=auth_headers(admin)).json()
    assert data["smtp_pass"] == ""
    assert data["smtp_pass_set"] is True
