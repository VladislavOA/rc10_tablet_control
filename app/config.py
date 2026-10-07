import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
TRAJECTORY_DIR = DATA_DIR / "trajectories"
VIDEO_DIR = DATA_DIR / "videos"
YANDEX_LINKS_FILE = DATA_DIR / "yandex_links.json"

CAMERA_SOURCE = os.getenv("CAMERA_SOURCE", "").strip()
CAMERA_INDEX = int(os.getenv("CAMERA_INDEX", "0"))
VIDEO_FPS = float(os.getenv("VIDEO_FPS", "30"))
VIDEO_WIDTH = int(os.getenv("VIDEO_WIDTH", "1280"))
VIDEO_HEIGHT = int(os.getenv("VIDEO_HEIGHT", "720"))
VIDEO_ROTATION = int(os.getenv("VIDEO_ROTATION", "90")) % 360

# Mode requested from the capture device. Empty size = derived from VIDEO_*.
CAPTURE_WIDTH = int(os.getenv("CAPTURE_WIDTH", "0") or 0)
CAPTURE_HEIGHT = int(os.getenv("CAPTURE_HEIGHT", "0") or 0)
CAPTURE_FOURCC = os.getenv("CAPTURE_FOURCC", "MJPG").strip().upper()

PREVIEW_WIDTH = int(os.getenv("PREVIEW_WIDTH", "360"))
PREVIEW_HEIGHT = int(os.getenv("PREVIEW_HEIGHT", "640"))
PREVIEW_FPS = float(os.getenv("PREVIEW_FPS", "20"))
PREVIEW_JPEG_QUALITY = int(os.getenv("PREVIEW_JPEG_QUALITY", "65"))

START_COUNTDOWN_SECONDS = max(0, int(os.getenv("START_COUNTDOWN_SECONDS", "5")))
MANIPULATOR_STUB_SECONDS = max(0.0, float(os.getenv("MANIPULATOR_STUB_SECONDS", "30")))
MAX_VIDEO_SECONDS = max(1.0, float(os.getenv("MAX_VIDEO_SECONDS", "15")))

YANDEX_DISK_TOKEN = os.getenv("YANDEX_DISK_TOKEN", "").strip()
YANDEX_DISK_DIR = os.getenv("YANDEX_DISK_DIR", "/RC10/videos").strip() or "/RC10/videos"
APP_PORT = int(os.getenv("APP_PORT", "8070"))

VIDEO_DIR.mkdir(parents=True, exist_ok=True)
TRAJECTORY_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)
