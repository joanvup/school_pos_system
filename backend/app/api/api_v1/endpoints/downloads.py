import hashlib
import re
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from app.api import deps
from app.core.config import settings
from app.models.user import User

router = APIRouter()

_DEFAULT_EXECUTABLE_NAME = "ACR122U_NFC.exe"


def _executable_path() -> Path:
    configured_path = settings.NFC_EXECUTABLE_PATH.strip()
    backend_path = Path(__file__).resolve().parents[4]

    if configured_path:
        path = Path(configured_path).expanduser()
        if not path.is_absolute():
            path = backend_path / path
    else:
        path = backend_path / "dist" / _DEFAULT_EXECUTABLE_NAME

    return path.resolve()


def _download_filename() -> str:
    version = re.sub(r"[^A-Za-z0-9._-]", "", settings.NFC_EXECUTABLE_VERSION)
    return f"ACR122U_NFC_v{version or '1.0.0'}.exe"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


@router.get("/nfc-reader")
def download_nfc_reader(
    current_user: User = Depends(deps.get_current_active_staff),
):
    path = _executable_path()
    if not path.is_file():
        raise HTTPException(
            status_code=503,
            detail="El ejecutable del lector NFC no está disponible en el servidor",
        )

    return FileResponse(
        path=path,
        media_type="application/vnd.microsoft.portable-executable",
        filename=_download_filename(),
        headers={
            "X-Content-SHA256": _sha256(path),
            "X-Content-Type-Options": "nosniff",
        },
    )
