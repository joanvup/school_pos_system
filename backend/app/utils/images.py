"""Validación y almacenamiento seguro de imágenes subidas.

Nunca guarda el archivo original: comprueba la firma binaria, decodifica con
Pillow y vuelve a codificar en un formato seguro, sin metadatos.
"""

import io
import os
import uuid
import warnings
from pathlib import Path

from fastapi import HTTPException, UploadFile
from PIL import Image, UnidentifiedImageError

BACKEND_DIR = Path(__file__).resolve().parents[2]
UPLOAD_ROOT = BACKEND_DIR / "uploads"

MAX_IMAGE_PIXELS = 24_000_000
MAX_SIDE = 1600

Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS


def _sniff_format(data: bytes) -> str | None:
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "PNG"
    if data.startswith(b"\xff\xd8\xff"):
        return "JPEG"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "WEBP"
    return None


def _has_alpha(image: Image.Image) -> bool:
    return image.mode in ("RGBA", "LA") or (
        image.mode == "P" and "transparency" in image.info
    )


async def store_image(
    file: UploadFile,
    *,
    subdir: str,
    prefix: str,
    max_bytes: int,
    force_png: bool = False,
    max_side: int = MAX_SIDE,
    filename: str | None = None,
) -> str:
    """Valida y guarda una imagen. Devuelve la URL relativa pública."""
    if filename is not None and Path(filename).name != filename:
        raise ValueError("filename no puede contener rutas")

    data = await file.read(max_bytes + 1)
    if not data:
        raise HTTPException(status_code=400, detail="La imagen está vacía")
    if len(data) > max_bytes:
        raise HTTPException(
            status_code=413, detail="La imagen supera el tamaño máximo permitido"
        )

    sniffed = _sniff_format(data)
    if sniffed is None:
        raise HTTPException(status_code=400, detail="Formato de imagen no permitido")

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data)) as image:
                image.load()
                if image.width * image.height > MAX_IMAGE_PIXELS:
                    raise HTTPException(
                        status_code=400, detail="La imagen tiene demasiados píxeles"
                    )
                if force_png or _has_alpha(image):
                    out = image.convert("RGBA")
                    out_format, extension = "PNG", "png"
                else:
                    out = image.convert("RGB")
                    out_format, extension = "JPEG", "jpg"
                out.thumbnail((max_side, max_side), Image.LANCZOS)
                buffer = io.BytesIO()
                if out_format == "JPEG":
                    out.save(buffer, out_format, quality=85, optimize=True)
                else:
                    out.save(buffer, out_format, optimize=True)
    except HTTPException:
        raise
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
        raise HTTPException(status_code=400, detail="El archivo no es una imagen válida")

    name = filename or f"{prefix}-{uuid.uuid4().hex}.{extension}"
    target_dir = UPLOAD_ROOT / subdir
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / name

    tmp_path = target_path.with_name(target_path.name + ".tmp")
    tmp_path.write_bytes(buffer.getvalue())
    os.chmod(tmp_path, 0o644)
    os.replace(tmp_path, target_path)

    return f"/uploads/{subdir}/{name}"
