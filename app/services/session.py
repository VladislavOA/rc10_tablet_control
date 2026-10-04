from __future__ import annotations

import threading
import queue
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

from .camera import CameraRecorder
from .yandex_disk import YandexDiskClient

TrajectoryExecutor = Callable[[str], bool]


class SessionManager:
    """Countdown -> record -> successful trajectory -> save -> create folder -> QR -> upload."""

    BUSY_PHASES = {"preparing_share", "countdown", "recording", "processing"}

    def __init__(
        self,
        camera: CameraRecorder,
        cloud: YandexDiskClient,
        trajectory_executor: TrajectoryExecutor,
        countdown_seconds: int = 5,
        max_video_seconds: float = 15.0,
    ):
        self.camera = camera
        self.cloud = cloud
        self.trajectory_executor = trajectory_executor
        self.countdown_seconds = max(0, int(countdown_seconds))
        self.max_video_seconds = max(1.0, float(max_video_seconds))

        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._lock = threading.RLock()

        self._session_id: Optional[str] = None
        self._phase = "idle"
        self._started_at: Optional[str] = None
        self._countdown_deadline: Optional[float] = None
        self._video: Optional[str] = None
        self._trajectory: Optional[str] = None
        self._share_url: Optional[str] = None
        self._remote_folder: Optional[str] = None
        self._error: Optional[str] = None
        self._upload_error: Optional[str] = None
        self._upload_state = "idle"
        self._local_ready = False
        self._success = False

    def _is_busy(self) -> bool:
        return self._phase in self.BUSY_PHASES

    def start(self, trajectory: Path) -> str:
        with self._lock:
            if self._is_busy():
                raise RuntimeError("Сессия уже запущена")
            if not self.cloud.enabled:
                raise RuntimeError("Не задан YANDEX_DISK_TOKEN")

            session_id = uuid.uuid4().hex
            self._session_id = session_id
            self._phase = "preparing_share"
            self._started_at = datetime.now().isoformat(timespec="seconds")
            # Safety countdown starts immediately when the user presses the button.
            # Yandex folder is intentionally NOT created yet.
            self._countdown_deadline = time.monotonic() + self.countdown_seconds
            self._trajectory = trajectory.name
            self._video = None
            self._share_url = None
            self._remote_folder = None
            self._error = None
            self._upload_error = None
            self._upload_state = "idle"
            self._local_ready = False
            self._success = False
            self._stop_event.clear()

        with self._lock:
            if self._session_id != session_id:
                raise RuntimeError("Сессия была заменена")
            self._phase = "countdown"

        self._thread = threading.Thread(
            target=self._run,
            args=(session_id, trajectory.name),
            daemon=True,
        )
        self._thread.start()
        return session_id

    def _wait_countdown(self) -> bool:
        while True:
            if self._stop_event.is_set():
                return False
            with self._lock:
                deadline = self._countdown_deadline
            if deadline is None:
                return True
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return True
            time.sleep(min(0.05, remaining))

    def _finish_recording(self) -> Path:
        with self._lock:
            self._phase = "processing"
        video_path = self.camera.stop_recording()
        if not video_path or not video_path.exists():
            raise RuntimeError("Видео не было создано")
        with self._lock:
            self._local_ready = True
        return video_path

    def _upload_background(
        self,
        session_id: str,
        video_path: Path,
        remote_folder: str,
        public_url: str,
    ) -> None:
        first_attempt = True
        while True:
            with self._lock:
                if self._session_id == session_id:
                    self._upload_state = "uploading" if first_attempt else "waiting_upload"

            try:
                self.cloud.upload_to_public_folder(
                    video_path,
                    remote_folder,
                    public_url,
                    remote_name="video.mp4",
                )
                with self._lock:
                    if self._session_id == session_id:
                        self._upload_state = "done"
                        self._upload_error = None
                return
            except Exception as exc:
                with self._lock:
                    if self._session_id == session_id:
                        self._upload_state = "waiting_upload"
                        self._upload_error = str(exc)
                first_attempt = False
                time.sleep(5.0)

    def _execute_trajectory_with_timeout(self, trajectory_name: str) -> tuple[bool, str]:
        """Run the manipulator while limiting how long the camera may record."""
        result_queue: queue.Queue = queue.Queue(maxsize=1)

        def worker() -> None:
            try:
                ok = bool(self.trajectory_executor(trajectory_name))
                result_queue.put(("ok", ok))
            except Exception as exc:
                result_queue.put(("error", exc))

        threading.Thread(target=worker, daemon=True).start()

        try:
            kind, value = result_queue.get(timeout=self.max_video_seconds)
        except queue.Empty:
            return False, f"Максимальная длина видео {self.max_video_seconds:g} с достигнута"

        if kind == "error":
            return False, f"Ошибка манипулятора: {value}"
        if not value:
            return False, "Манипулятор не завершил траекторию"
        return True, ""

    def _run(
        self,
        session_id: str,
        trajectory_name: str,
    ) -> None:
        try:
            if not self._wait_countdown():
                raise RuntimeError("Съёмка отменена")

            with self._lock:
                if self._session_id != session_id:
                    return
                self._countdown_deadline = None
                self._phase = "recording"

            video_path = self.camera.start_recording()
            with self._lock:
                self._video = video_path.name

            movement_ok, movement_error = self._execute_trajectory_with_timeout(trajectory_name)

            # MP4 финализируем в любом случае: при False, исключении или таймауте
            # локальное видео остаётся на ноутбуке.
            video_path = self._finish_recording()

            if not movement_ok:
                with self._lock:
                    if self._session_id != session_id:
                        return
                    self._success = False
                    self._phase = "error"
                    self._error = movement_error
                return

            # Папка на Яндекс.Диске создаётся ТОЛЬКО после успешной траектории.
            with self._lock:
                if self._session_id != session_id:
                    return
                self._phase = "preparing_share"

            folder = self.cloud.create_public_folder(session_id)
            remote_folder = folder["remote_folder"]
            public_url = folder["public_url"]

            with self._lock:
                if self._session_id != session_id:
                    return
                self._share_url = public_url
                self._remote_folder = remote_folder
                self._success = True
                self._phase = "done"
                self._upload_state = "uploading"

            threading.Thread(
                target=self._upload_background,
                args=(session_id, video_path, remote_folder, public_url),
                daemon=True,
            ).start()

        except Exception as exc:
            try:
                if self.camera.status().get("recording"):
                    self.camera.stop_recording()
            except Exception as stop_exc:
                exc = RuntimeError(f"{exc}; ошибка финализации видео: {stop_exc}")
            with self._lock:
                if self._session_id == session_id:
                    self._success = False
                    self._error = str(exc)
                    self._phase = "error"
                    self._countdown_deadline = None

    def stop(self) -> None:
        self._stop_event.set()
        try:
            if self.camera.status().get("recording"):
                self.camera.stop_recording()
        finally:
            with self._lock:
                self._success = False
                self._error = "Съёмка отменена"
                self._phase = "error"
                self._countdown_deadline = None

    def set_share_url(self, video_name: str, share_url: str) -> None:
        with self._lock:
            if self._video == video_name:
                self._share_url = share_url

    def status(self) -> dict:
        with self._lock:
            remaining = 0
            if self._phase == "countdown" and self._countdown_deadline is not None:
                remaining = max(0, int(self._countdown_deadline - time.monotonic() + 0.999))

            return {
                "session_id": self._session_id,
                "phase": self._phase,
                "active": self._is_busy(),
                "countdown_remaining": remaining,
                "started_at": self._started_at,
                "video": self._video,
                "trajectory": self._trajectory,
                "share_url": self._share_url,
                "remote_folder": self._remote_folder,
                "local_ready": self._local_ready,
                "upload_state": self._upload_state,
                "upload_error": self._upload_error,
                "success": self._success,
                "error": self._error,
            }
