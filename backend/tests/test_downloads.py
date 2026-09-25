import hashlib
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import HTTPException

from app.api import deps
from app.api.api_v1.endpoints import downloads
from app.models.user import UserRole


class DownloadHelpersTest(unittest.TestCase):
    def test_default_path_points_to_backend_dist(self):
        with patch.object(downloads.settings, "NFC_EXECUTABLE_PATH", ""):
            expected = Path(downloads.__file__).resolve().parents[4] / "dist" / "ACR122U_NFC.exe"
            self.assertEqual(downloads._executable_path(), expected)

    def test_sha256_matches_file_content(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "reader.exe"
            path.write_bytes(b"test executable")
            self.assertEqual(downloads._sha256(path), hashlib.sha256(b"test executable").hexdigest())

    def test_staff_dependency_allows_pos_roles_only(self):
        for role in (UserRole.ADMIN, UserRole.SUPERVISOR, UserRole.VENDEDOR):
            user = SimpleNamespace(role=role)
            self.assertIs(deps.get_current_active_staff(user), user)

        with self.assertRaises(HTTPException) as context:
            deps.get_current_active_staff(SimpleNamespace(role=UserRole.PADRE))
        self.assertEqual(context.exception.status_code, 403)

    def test_missing_executable_returns_service_unavailable(self):
        with tempfile.TemporaryDirectory() as directory:
            missing_path = Path(directory) / "missing.exe"
            with patch.object(downloads.settings, "NFC_EXECUTABLE_PATH", str(missing_path)):
                with self.assertRaises(HTTPException) as context:
                    downloads.download_nfc_reader(SimpleNamespace(role=UserRole.ADMIN))
        self.assertEqual(context.exception.status_code, 503)
