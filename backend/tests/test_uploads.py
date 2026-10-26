"""Endurecimiento de subidas de imagen (Fase 3)."""

import io

from PIL import Image

from app.models.user import UserRole
from app.utils import images

API = "/api/v1"


def _png_bytes(size=(64, 64), color=(10, 120, 200, 255)) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGBA", size, color).save(buffer, "PNG")
    return buffer.getvalue()


def _jpeg_bytes(size=(64, 64)) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", size, (200, 30, 30)).save(buffer, "JPEG")
    return buffer.getvalue()


def _post_logo(client, headers, data: bytes, filename="logo.png"):
    return client.post(
        f"{API}/settings/logo",
        files={"file": (filename, data, "image/png")},
        headers=headers,
    )


def test_logo_reencodes_to_png(client, user_factory, auth_headers, tmp_path, monkeypatch):
    monkeypatch.setattr(images, "UPLOAD_ROOT", tmp_path)
    admin = user_factory(role=UserRole.ADMIN)

    response = _post_logo(client, auth_headers(admin), _png_bytes(), "raro.webp")

    assert response.status_code == 200
    url = response.json()["logo_url"]
    assert url == "/uploads/branding/school_logo.png"
    with Image.open(tmp_path / "branding" / "school_logo.png") as stored:
        assert stored.format == "PNG"


def test_logo_rejects_svg(client, user_factory, auth_headers, tmp_path, monkeypatch):
    monkeypatch.setattr(images, "UPLOAD_ROOT", tmp_path)
    admin = user_factory(role=UserRole.ADMIN)

    response = _post_logo(
        client,
        auth_headers(admin),
        b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>',
        "logo.svg",
    )

    assert response.status_code == 400
    assert not (tmp_path / "branding").exists()


def test_logo_rejects_disguised_text(client, user_factory, auth_headers, tmp_path, monkeypatch):
    monkeypatch.setattr(images, "UPLOAD_ROOT", tmp_path)
    admin = user_factory(role=UserRole.ADMIN)

    response = _post_logo(client, auth_headers(admin), b"<html>no soy png</html>")

    assert response.status_code == 400


def test_logo_rejects_oversized(client, user_factory, auth_headers, tmp_path, monkeypatch):
    monkeypatch.setattr(images, "UPLOAD_ROOT", tmp_path)
    admin = user_factory(role=UserRole.ADMIN)

    response = _post_logo(client, auth_headers(admin), b"\x89PNG\r\n\x1a\n" + b"0" * 3_000_000)

    assert response.status_code == 413


def test_logo_requires_admin(client, user_factory, auth_headers):
    parent = user_factory(role=UserRole.PADRE)

    response = _post_logo(client, auth_headers(parent), _png_bytes())

    assert response.status_code == 403


def test_product_image_reencodes_and_keeps_alpha(
    client, db, user_factory, auth_headers, product_factory, tmp_path, monkeypatch
):
    monkeypatch.setattr(images, "UPLOAD_ROOT", tmp_path)
    admin = user_factory(role=UserRole.ADMIN)
    product = product_factory()

    response = client.post(
        f"{API}/products/{product.id}/image",
        files={"file": ("foto.png", _png_bytes(), "image/png")},
        headers=auth_headers(admin),
    )

    assert response.status_code == 200
    image_url = response.json()["image_url"]
    assert image_url.startswith("/uploads/products/")

    stored_name = image_url.rsplit("/", 1)[-1]
    assert stored_name.startswith(f"product-{product.id}-")
    assert stored_name.endswith(".png")

    db.refresh(product)
    assert product.image_url == image_url


def test_product_image_jpeg_stays_jpeg(
    client, user_factory, auth_headers, product_factory, tmp_path, monkeypatch
):
    monkeypatch.setattr(images, "UPLOAD_ROOT", tmp_path)
    admin = user_factory(role=UserRole.ADMIN)
    product = product_factory()

    response = client.post(
        f"{API}/products/{product.id}/image",
        files={"file": ("foto.jpg", _jpeg_bytes(), "image/jpeg")},
        headers=auth_headers(admin),
    )

    assert response.status_code == 200
    image_url = response.json()["image_url"]
    assert image_url.endswith(".jpg")
    stored = tmp_path / "products" / image_url.rsplit("/", 1)[-1]
    with Image.open(stored) as image:
        assert image.format == "JPEG"


def test_product_image_rejects_unknown_product(
    client, user_factory, auth_headers, tmp_path, monkeypatch
):
    monkeypatch.setattr(images, "UPLOAD_ROOT", tmp_path)
    admin = user_factory(role=UserRole.ADMIN)

    response = client.post(
        f"{API}/products/999999/image",
        files={"file": ("foto.png", _png_bytes(), "image/png")},
        headers=auth_headers(admin),
    )

    assert response.status_code == 404
