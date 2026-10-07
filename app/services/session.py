from __future__ import annotations

import threading
import queue
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

from .camera import CameraRecorder
from .video_postprocess import apply_speed_intervals
from .yandex_disk import YandexDiskClient

TrajectoryExecutor = Callable[[str, Callable[[], None], Callable[[], bool]], bool]


class SessionManager:
    """Countdown -> record -> successful trajectory -> save -> create folder -> QR -> upload."""

    BUSY_PHASES = {"preparing_motion", "preparing_share", "countdown", "recording", "processing"}

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

    def start(
        self,
        trajectory: Path,
        speed_intervals: Optional[list[dict[str, float]]] = None,
    ) -> str:
        with self._lock:
            if self._is_busy():
                raise RuntimeError("Сессия уже запущена")
            if not self.cloud.enabled:
                raise RuntimeError("Не задан YANDEX_DISK_TOKEN")

            session_id = uuid.uuid4().hex
            self._session_id = session_id
            # The countdown and the manipulator preparation start together.
            self._phase = "countdown"
            self._started_at = datetime.now().isoformat(timespec="seconds")
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
            speed_intervals = speed_intervals or []
            self._stop_event.clear()

        self._thread = threading.Thread(
            target=self._run,
            args=(session_id, trajectory.name, speed_intervals),
            daemon=True,
        )
        self._thread.start()
        return session_id

    def _finish_recording(self, speed_intervals: list[dict[str, float]]) -> Path:
        with self._lock:
            self._phase = "processing"
        video_path = self.camera.stop_recording()
        if not video_path or not video_path.exists():
            raise RuntimeError("Видео не было создано")
        apply_speed_intervals(video_path, speed_intervals)
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

    def _execute_trajectory_with_timeout(
        self,
        session_id: str,
        trajectory_name: str,
    ) -> tuple[bool, str]:
        """Prepare the robot during the countdown, record, then release its first motion command."""
        result_queue: queue.Queue = queue.Queue()
        motion_gate = threading.Event()
        abort_gate = threading.Event()

        def worker() -> None:
            try:
                ok = bool(self.trajectory_executor(
                    trajectory_name,
                    on_motion_ready=lambda: result_queue.put(("ready", None)),
                    wait_for_motion_start=lambda: self._wait_motion_gate(
                        session_id,
                        motion_gate,
                        abort_gate,
                    ),
                ))
                result_queue.put(("ok", ok))
            except Exception as exc:
                result_queue.put(("error", exc))

        threading.Thread(target=worker, daemon=True).start()

        # The countdown started with the button press and runs while the robot
        # prepares; motion and recording begin once both have finished.
        deadline = time.monotonic() + self.max_video_seconds
        ready_result = None
        cancelled = False
        while True:
            with self._lock:
                if self._session_id != session_id or self._stop_event.is_set():
                    cancelled = True
                    break
                countdown_deadline = self._countdown_deadline
            now = time.monotonic()
            countdown_left = 0.0 if countdown_deadline is None else countdown_deadline - now

            if ready_result is None:
                if now >= deadline:
                    break
                try:
                    ready_result = result_queue.get(timeout=0.05)
                except queue.Empty:
                    if countdown_left <= 0:
                        with self._lock:
                            if self._session_id == session_id and self._phase == "countdown":
                                self._phase = "preparing_motion"
                    continue
                if ready_result[0] != "ready":
                    break
                continue

            if countdown_left <= 0:
                break
            time.sleep(min(0.05, countdown_left))

        if cancelled or ready_result is None:
            abort_gate.set()
            motion_gate.set()
            if cancelled:
                return False, "Съёмка отменена"
            return False, "Манипулятор не подготовил движение вовремя"
        kind, value = ready_result

        if kind == "error":
            return False, f"Ошибка манипулятора: {value}"
        if kind != "ready":
            return False, "Манипулятор завершил программу без сигнала начала движения"

        try:
            video_path = self.camera.start_recording()
        except Exception:
            abort_gate.set()
            motion_gate.set()
            raise

        with self._lock:
            self._video = video_path.name
            self._countdown_deadline = None
            self._phase = "recording"

        motion_gate.set()
        try:
            kind, value = result_queue.get(timeout=self.max_video_seconds)
        except queue.Empty:
            abort_gate.set()
            return False, f"Максимальная длина видео {self.max_video_seconds:g} с достигнута"

        if kind == "error":
            return False, f"Ошибка манипулятора: {value}"
        if not value:
            return False, "Манипулятор не завершил траекторию"
        return True, ""

    def _wait_motion_gate(
        self,
        session_id: str,
        motion_gate: threading.Event,
        abort_gate: threading.Event,
    ) -> bool:
        while not motion_gate.wait(0.1):
            with self._lock:
                session_changed = self._session_id != session_id
            if session_changed or self._stop_event.is_set() or abort_gate.is_set():
                return False
        with self._lock:
            session_changed = self._session_id != session_id
        return not session_changed and not self._stop_event.is_set() and not abort_gate.is_set()

    def _run(
        self,
        session_id: str,
        trajectory_name: str,
        speed_intervals: list[dict[str, float]],
    ) -> None:
        try:
            with self._lock:
                if self._session_id != session_id:
                    return

            movement_ok, movement_error = self._execute_trajectory_with_timeout(
                session_id,
                trajectory_name,
            )

            with self._lock:
                if self._session_id != session_id:
                    return

            if self.camera.status().get("recording"):
                # Finalize even on failure/timeout so the local video is retained.
                video_path = self._finish_recording(speed_intervals)
            else:
                video_path = None

            if not movement_ok:
                with self._lock:
                    if self._session_id != session_id:
                        return
                    self._success = False
                    self._phase = "error"
                    self._error = movement_error
                return

            if video_path is None:
                raise RuntimeError("Видео не было создано")

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
