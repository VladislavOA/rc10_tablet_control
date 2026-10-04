from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES = ["https://www.googleapis.com/auth/drive.file"]


class GoogleDriveStorage:
    """Google Drive storage with public-by-link sharing.

    Every uploaded video gets an `anyone: reader` permission. The QR code points
    directly to the Google Drive webViewLink, so the backend does not proxy the
    video and there is no extra download timeout on QR open.
    """

    def __init__(self, token_file: Path, folder_id: str | None, share_index: Path, share_hours: int = 24):
        self.token_file = token_file
        self.folder_id = folder_id or None
        self.share_index = share_index
        self._lock = threading.RLock()
        self.share_index.parent.mkdir(parents=True, exist_ok=True)

    def _credentials(self) -> Credentials:
        if not self.token_file.exists():
            raise RuntimeError(
                f"Google Drive не авторизован. Сначала запустите scripts/google_login.py. "
                f"Ожидается token: {self.token_file}"
            )
        creds = Credentials.from_authorized_user_file(str(self.token_file), SCOPES)
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            self.token_file.write_text(creds.to_json(), encoding="utf-8")
        if not creds.valid:
            raise RuntimeError("Google OAuth token недействителен")
        return creds

    def _service(self):
        return build("drive", "v3", credentials=self._credentials(), cache_discovery=False)

    def _load_index(self) -> dict:
        if not self.share_index.exists():
            return {}
        try:
            return json.loads(self.share_index.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _save_index(self, data: dict) -> None:
        tmp = self.share_index.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self.share_index)

    def upload_public(self, file_path: Path) -> dict:
        service = self._service()
        metadata = {"name": file_path.name}
        if self.folder_id:
            metadata["parents"] = [self.folder_id]

        media = MediaFileUpload(str(file_path), mimetype="video/mp4", resumable=True)
        result = (
            service.files()
            .create(body=metadata, media_body=media, fields="id,name,size,mimeType,createdTime,webViewLink")
            .execute()
        )

        # Anyone who has the link can view the file; no Google login is required.
        service.permissions().create(
            fileId=result["id"],
            body={
                "type": "anyone",
                "role": "reader",
                "allowFileDiscovery": False,
            },
            fields="id",
        ).execute()

        # webViewLink can be absent in the create response on some accounts, so
        # fetch it once after creating the permission.
        info = service.files().get(
            fileId=result["id"],
            fields="id,name,webViewLink,webContentLink",
        ).execute()
        share_url = info.get("webViewLink") or f"https://drive.google.com/file/d/{result['id']}/view"
        result["share_url"] = share_url

        with self._lock:
            data = self._load_index()
            data[file_path.name] = {
                "drive_file_id": result["id"],
                "share_url": share_url,
            }
            self._save_index(data)

        return result

    def share_url_for_name(self, name: str) -> Optional[str]:
        with self._lock:
            item = self._load_index().get(name)
        if not item:
            return None
        return item.get("share_url")
