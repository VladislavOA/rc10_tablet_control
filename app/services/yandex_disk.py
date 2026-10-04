from __future__ import annotations

import json
import threading
import time
import uuid
from pathlib import Path
from typing import Optional

import requests


class YandexDiskClient:
    API = "https://cloud-api.yandex.net/v1/disk"

    def __init__(self, token: str, remote_dir: str, links_file: Path):
        self.token = token.strip()
        self.remote_dir = "/" + remote_dir.strip("/") if remote_dir.strip("/") else "/RC10/videos"
        self.links_file = links_file
        self._lock = threading.RLock()
        self._links: dict[str, dict] = {}
        self._load_links()

    @property
    def enabled(self) -> bool:
        return bool(self.token)

    @property
    def headers(self) -> dict[str, str]:
        return {"Authorization": f"OAuth {self.token}"}

    def _load_links(self) -> None:
        try:
            if self.links_file.exists():
                data = json.loads(self.links_file.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    self._links = data
        except Exception:
            self._links = {}

    def _save_links(self) -> None:
        self.links_file.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.links_file.with_suffix(".tmp")
        tmp.write_text(json.dumps(self._links, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self.links_file)

    def get_link(self, local_name: str) -> Optional[str]:
        with self._lock:
            item = self._links.get(local_name) or {}
            return item.get("public_url")

    def _request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        if not self.enabled:
            raise RuntimeError("YANDEX_DISK_TOKEN не задан")
        headers = dict(self.headers)
        headers.update(kwargs.pop("headers", {}) or {})
        response = requests.request(
            method,
            f"{self.API}{endpoint}",
            headers=headers,
            timeout=kwargs.pop("timeout", 30),
            **kwargs,
        )
        if response.status_code >= 400:
            try:
                payload = response.json()
                message = payload.get("message") or payload.get("description") or response.text
            except Exception:
                message = response.text
            raise RuntimeError(f"Яндекс Диск HTTP {response.status_code}: {message}")
        return response

    def _mkdir(self, path: str) -> None:
        response = requests.put(
            f"{self.API}/resources",
            headers=self.headers,
            params={"path": path},
            timeout=30,
        )
        if response.status_code not in (201, 409):
            try:
                payload = response.json()
                message = payload.get("message") or payload.get("description") or response.text
            except Exception:
                message = response.text
            raise RuntimeError(f"Не удалось создать {path}: HTTP {response.status_code}: {message}")

    def ensure_directory(self) -> None:
        if not self.enabled:
            raise RuntimeError("YANDEX_DISK_TOKEN не задан")
        current = ""
        for part in [p for p in self.remote_dir.split("/") if p]:
            current += "/" + part
            self._mkdir(current)

    def create_public_folder(self, session_id: str) -> dict:
        """Create and publish the visitor folder before the video exists."""
        if not self.enabled:
            raise RuntimeError("YANDEX_DISK_TOKEN не задан")

        self.ensure_directory()
        safe_id = "".join(c for c in session_id if c.isalnum() or c in "-_")
        if not safe_id:
            raise RuntimeError("Некорректный session_id")

        remote_folder = f"{self.remote_dir.rstrip('/')}/{safe_id}"
        self._mkdir(remote_folder)

        self._request(
            "PUT",
            "/resources/publish",
            params={"path": remote_folder},
        )

        # После publish Яндекс иногда не возвращает public_url мгновенно.
        # Ждём несколько секунд вместо того, чтобы считать сессию ошибочной.
        public_url = None
        last_info = {}
        for _ in range(30):
            last_info = self._request(
                "GET",
                "/resources",
                params={"path": remote_folder, "fields": "name,path,public_url"},
            ).json()
            public_url = last_info.get("public_url")
            if public_url:
                break
            time.sleep(0.25)

        if not public_url:
            raise RuntimeError("Яндекс Диск опубликовал папку, но public_url не появился за 7.5 секунд")

        item = {
            "public_url": public_url,
            "remote_folder": remote_folder,
            "session_id": session_id,
        }
        with self._lock:
            self._links[f"session:{session_id}"] = item
            self._save_links()
        return item

    def upload_to_public_folder(
        self,
        local_path: Path,
        remote_folder: str,
        public_url: str,
        remote_name: str = "video.mp4",
    ) -> dict:
        """Upload the finished MP4 into an already-published folder."""
        if not local_path.exists():
            raise FileNotFoundError(local_path)
        if not self.enabled:
            raise RuntimeError("YANDEX_DISK_TOKEN не задан")

        remote_path = f"{remote_folder.rstrip('/')}/{remote_name}"

        upload_info = self._request(
            "GET",
            "/resources/upload",
            params={"path": remote_path, "overwrite": "true"},
        ).json()
        upload_href = upload_info.get("href")
        if not upload_href:
            raise RuntimeError("Яндекс Диск не вернул URL загрузки")

        with local_path.open("rb") as fh:
            upload_response = requests.put(
                upload_href,
                data=fh,
                headers={"Content-Type": "video/mp4"},
                timeout=(15, 900),
            )
        if upload_response.status_code >= 400:
            raise RuntimeError(
                f"Ошибка загрузки MP4 на Яндекс Диск: HTTP {upload_response.status_code}: "
                f"{upload_response.text}"
            )

        info = self._request(
            "GET",
            "/resources",
            params={"path": remote_path, "fields": "name,path,size"},
        ).json()

        item = {
            "public_url": public_url,
            "remote_folder": remote_folder,
            "remote_path": remote_path,
            "remote_name": remote_name,
            "size": info.get("size", local_path.stat().st_size),
        }
        with self._lock:
            self._links[local_path.name] = item
            self._save_links()
        return item

    def upload_public(self, local_path: Path) -> dict:
        """Backward-compatible manual publish helper."""
        session_id = uuid.uuid4().hex
        folder = self.create_public_folder(session_id)
        return self.upload_to_public_folder(
            local_path,
            folder["remote_folder"],
            folder["public_url"],
        )
