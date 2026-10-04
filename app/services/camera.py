from __future__ import annotations

import shutil
import subprocess
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Union

import cv2


class CameraRecorder:
    """Single-owner camera capture with recording + low-latency JPEG preview.

    The camera is read exactly once in a background thread. Recording uses the
    original frame while the tablet preview uses a smaller JPEG. WebSocket
    clients always receive only the newest JPEG, so old frames never queue up.
    """

    def __init__(
        self,
        source: Union[int, str],
        video_dir: Path,
        fps: float,
        width: int,
        height: int,
        preview_width: int = 640,
        preview_height: int = 360,
        preview_fps: float = 20,
        preview_jpeg_quality: int = 65,
        rotation: int = 90,
    ):
        self.source = source
        self.video_dir = video_dir
        self.fps = fps
        self.width = width
        self.height = height
        self.preview_width = preview_width
        self.preview_height = preview_height
        self.preview_fps = max(1.0, preview_fps)
        self.preview_jpeg_quality = max(30, min(95, preview_jpeg_quality))
        self.rotation = rotation % 360
        if self.rotation not in (0, 90, 180, 270):
            raise ValueError("VIDEO_ROTATION должен быть 0, 90, 180 или 270")

        self._cap = None
        self._writer = None
        self._recording = False
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._lock = threading.RLock()
        self._last_file: Optional[Path] = None
        self._temp_file: Optional[Path] = None
        self._error: Optional[str] = None
        self._latest_frame = None
        self._latest_jpeg: Optional[bytes] = None
        self._jpeg_seq = 0
        self._record_started_at: Optional[float] = None
        self._written_frames = 0
        self._preview_clients = 0

    def _open_capture(self):
        if isinstance(self.source, str) and self.source:
            return cv2.VideoCapture(self.source, cv2.CAP_FFMPEG)
        return cv2.VideoCapture(int(self.source), cv2.CAP_V4L2)

    def _ensure_camera(self) -> bool:
        if self._cap is not None and self._cap.isOpened():
            return True

        cap = self._open_capture()
        if not cap.isOpened():
            self._error = f"Камера недоступна: {self.source}"
            try:
                cap.release()
            except Exception:
                pass
            return False

        if not (isinstance(self.source, str) and self.source):
            # USB camera: request MJPEG from the device to reduce USB bandwidth.
            cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))

        cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        cap.set(cv2.CAP_PROP_FPS, self.fps)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        self._cap = cap
        self._error = None
        return True

    def _reset_capture(self):
        cap = self._cap
        self._cap = None
        if cap is not None:
            try:
                cap.release()
            except Exception:
                pass

    def start_worker(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()


    def _orient_frame(self, frame):
        """Rotate camera frames before both preview and recording."""
        if self.rotation == 90:
            return cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
        if self.rotation == 180:
            return cv2.rotate(frame, cv2.ROTATE_180)
        if self.rotation == 270:
            return cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)
        return frame

    def _encode_preview(self, frame) -> None:
        preview = cv2.resize(
            frame,
            (self.preview_width, self.preview_height),
            interpolation=cv2.INTER_AREA,
        )
        ok, jpg = cv2.imencode(
            ".jpg",
            preview,
            [int(cv2.IMWRITE_JPEG_QUALITY), self.preview_jpeg_quality],
        )
        if ok:
            with self._lock:
                self._latest_jpeg = jpg.tobytes()
                self._jpeg_seq += 1

    def _loop(self):
        preview_interval = 1.0 / self.preview_fps
        next_preview_at = 0.0

        while not self._stop.is_set():
            if not self._ensure_camera():
                time.sleep(1.0)
                continue

            ok, frame = self._cap.read()
            if not ok:
                self._error = "Не удалось получить кадр с камеры"
                self._reset_capture()
                time.sleep(0.25)
                continue

            # Convert the landscape sensor frame into the configured orientation.
            frame = self._orient_frame(frame)

            now = time.monotonic()
            with self._lock:
                self._latest_frame = frame
                writer = self._writer
                recording = self._recording
                started_at = self._record_started_at

            # Preview is encoded at its own FPS. Recording keeps the original frame.
            with self._lock:
                preview_clients = self._preview_clients

            if preview_clients > 0 and now >= next_preview_at:
                self._encode_preview(frame)
                next_preview_at = now + preview_interval

            if recording and writer is not None and started_at is not None:
                elapsed = max(0.0, now - started_at)
                target_frames = int(elapsed * self.fps) + 1
                with self._lock:
                    missing = target_frames - self._written_frames
                    if missing > 0:
                        missing = min(missing, max(int(self.fps * 2), 1))
                        for _ in range(missing):
                            writer.write(frame)
                            self._written_frames += 1


    def preview_client_connected(self):
        with self._lock:
            self._preview_clients += 1

    def preview_client_disconnected(self):
        with self._lock:
            self._preview_clients = max(0, self._preview_clients - 1)

    def latest_jpeg(self):
        """Return (sequence, jpeg_bytes). The bytes are immutable and safe to share."""
        with self._lock:
            return self._jpeg_seq, self._latest_jpeg

    def start_recording(self) -> Path:
        self.start_worker()
        deadline = time.time() + 5
        while self._latest_frame is None and time.time() < deadline:
            time.sleep(0.05)
        if not self._ensure_camera() or self._latest_frame is None:
            raise RuntimeError(self._error or "Камера недоступна")

        stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        final_path = self.video_dir / f"rc10_{stamp}.mp4"
        temp_path = self.video_dir / f".rc10_{stamp}.avi"

        with self._lock:
            frame = self._latest_frame
            actual_h, actual_w = frame.shape[:2]

        fourcc = cv2.VideoWriter_fourcc(*"MJPG")
        writer = cv2.VideoWriter(str(temp_path), fourcc, self.fps, (actual_w, actual_h))
        if not writer.isOpened():
            raise RuntimeError("Не удалось открыть VideoWriter")

        with self._lock:
            self._writer = writer
            self._recording = True
            self._last_file = final_path
            self._temp_file = temp_path
            self._record_started_at = time.monotonic()
            self._written_frames = 0
        return final_path

    def _finalize_mp4(self, temp_path: Path, final_path: Path) -> None:
        ffmpeg = shutil.which("ffmpeg")
        if not ffmpeg:
            raise RuntimeError("Для корректного MP4 нужен ffmpeg: sudo apt install ffmpeg")

        cmd = [
            ffmpeg, "-y", "-loglevel", "error",
            "-i", str(temp_path),
            "-an",
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-crf", "22",
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            str(final_path),
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            raise RuntimeError(f"ffmpeg не смог собрать MP4: {proc.stderr.strip()}")
        if not final_path.exists() or final_path.stat().st_size < 1024:
            raise RuntimeError("Получился пустой или повреждённый MP4")
        temp_path.unlink(missing_ok=True)

    def stop_recording(self) -> Optional[Path]:
        with self._lock:
            self._recording = False
            writer = self._writer
            self._writer = None
            final_path = self._last_file
            temp_path = self._temp_file
            self._temp_file = None
            self._record_started_at = None

        if writer is not None:
            writer.release()

        if final_path and temp_path and temp_path.exists():
            self._finalize_mp4(temp_path, final_path)
        return final_path

    def status(self) -> dict:
        cap_ok = bool(self._cap is not None and self._cap.isOpened())
        return {
            "source": str(self.source),
            "available": cap_ok,
            "recording": self._recording,
            "preview": {
                "width": self.preview_width,
                "height": self.preview_height,
                "fps": self.preview_fps,
                "jpeg_quality": self.preview_jpeg_quality,
            },
            "rotation": self.rotation,
            "preview_clients": self._preview_clients,
            "error": self._error,
            "last_file": self._last_file.name if self._last_file else None,
        }
