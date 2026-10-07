from __future__ import annotations

import asyncio
import io
import json

import qrcode
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .config import (
    CAPTURE_FOURCC,
    CAPTURE_HEIGHT,
    CAPTURE_WIDTH,
    BASE_DIR,
    CAMERA_INDEX,
    CAMERA_SOURCE,
    PREVIEW_FPS,
    PREVIEW_HEIGHT,
    PREVIEW_JPEG_QUALITY,
    PREVIEW_WIDTH,
    START_COUNTDOWN_SECONDS,
    MAX_VIDEO_SECONDS,
    TRAJECTORY_DIR,
    VIDEO_DIR,
    VIDEO_FPS,
    VIDEO_HEIGHT,
    VIDEO_ROTATION,
    VIDEO_WIDTH,
    YANDEX_DISK_DIR,
    YANDEX_DISK_TOKEN,
    YANDEX_LINKS_FILE,
)
from .services.camera import CameraRecorder
from .services.manipulator import execute_manipulator_trajectory
from .services.session import SessionManager
from .services.video_postprocess import load_speed_intervals
from .services.yandex_disk import YandexDiskClient

app = FastAPI(title="RC10 Tablet Control", version="6.0.0")

camera_source = CAMERA_SOURCE if CAMERA_SOURCE else CAMERA_INDEX
camera = CameraRecorder(
    camera_source,
    VIDEO_DIR,
    VIDEO_FPS,
    VIDEO_WIDTH,
    VIDEO_HEIGHT,
    PREVIEW_WIDTH,
    PREVIEW_HEIGHT,
    PREVIEW_FPS,
    PREVIEW_JPEG_QUALITY,
    VIDEO_ROTATION,
    capture_width=CAPTURE_WIDTH,
    capture_height=CAPTURE_HEIGHT,
    capture_fourcc=CAPTURE_FOURCC,
)
yandex = YandexDiskClient(YANDEX_DISK_TOKEN, YANDEX_DISK_DIR, YANDEX_LINKS_FILE)
session = SessionManager(
    camera,
    yandex,
    execute_manipulator_trajectory,
    countdown_seconds=START_COUNTDOWN_SECONDS,
    max_video_seconds=MAX_VIDEO_SECONDS,
)

# The tablet (especially as a home-screen app) must revalidate the UI files,
# otherwise it keeps showing a stale page after an update.
NO_CACHE_HEADERS = {"Cache-Control": "no-cache"}


class RevalidatedStaticFiles(StaticFiles):
    async def get_response(self, path, scope):
        response = await super().get_response(path, scope)
        response.headers.update(NO_CACHE_HEADERS)
        return response


app.mount("/static", RevalidatedStaticFiles(directory=BASE_DIR / "app" / "static"), name="static")


class StartRequest(BaseModel):
    trajectory: str


@app.on_event("startup")
def startup():
    camera.start_worker()


@app.get("/")
def index():
    return FileResponse(BASE_DIR / "app" / "static" / "index.html", headers=NO_CACHE_HEADERS)


@app.get("/api/status")
def status():
    return {
        "camera": camera.status(),
        "session": session.status(),
        "cloud": {
            "provider": "yandex_disk",
            "enabled": yandex.enabled,
            "directory": YANDEX_DISK_DIR,
        },
    }


@app.get("/api/trajectories")
def trajectories():
    result = []
    for path in sorted(TRAJECTORY_DIR.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            result.append({
                "file": path.name,
                "name": data.get("name", path.stem),
                "points": len(data.get("points", [])),
            })
        except Exception:
            continue
    return result


@app.post("/api/session/start")
def start_session(body: StartRequest):
    trajectory = (TRAJECTORY_DIR / body.trajectory).resolve()
    if trajectory.parent != TRAJECTORY_DIR.resolve() or not trajectory.exists():
        raise HTTPException(404, "Траектория не найдена")
    try:
        speed_intervals = load_speed_intervals(trajectory)
        session_id = session.start(trajectory, speed_intervals)
        return {"ok": True, "session_id": session_id, "session": session.status()}
    except ValueError as exc:
        raise HTTPException(400, f"Неверные настройки видео траектории: {exc}")
    except Exception as exc:
        raise HTTPException(409, str(exc))


def qr_png(url: str) -> Response:
    img = qrcode.make(url)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return Response(
        content=buf.getvalue(),
        media_type="image/png",
        headers={"Cache-Control": "no-store"},
    )


@app.get("/api/session/{session_id}/qr")
def session_qr(session_id: str):
    current = session.status()
    if current.get("session_id") != session_id:
        raise HTTPException(404, "Сессия не найдена")
    url = current.get("share_url")
    if not url:
        raise HTTPException(409, "Публичная папка ещё не готова")
    return qr_png(url)


@app.post("/api/session/stop")
def stop_session():
    session.stop()
    return {"ok": True}


def safe_video(name: str):
    path = (VIDEO_DIR / name).resolve()
    if path.parent != VIDEO_DIR.resolve() or not path.exists() or path.suffix.lower() != ".mp4":
        raise HTTPException(404, "Видео не найдено")
    return path


@app.post("/api/videos/{name}/publish")
def publish_video(name: str):
    path = safe_video(name)
    try:
        result = yandex.upload_public(path)
        session.set_share_url(path.name, result["public_url"])
        return {"ok": True, **result}
    except Exception as exc:
        raise HTTPException(502, str(exc))


@app.get("/api/videos/{name}/qr")
def video_qr(name: str):
    safe_video(name)
    url = yandex.get_link(name)
    current = session.status()
    if not url and current.get("video") == name:
        url = current.get("share_url")
    if not url:
        raise HTTPException(409, "Видео ещё не опубликовано на Яндекс Диске")

    return qr_png(url)


@app.websocket("/ws/camera")
async def camera_websocket(websocket: WebSocket):
    await websocket.accept()
    camera.preview_client_connected()
    last_seq = -1
    try:
        while True:
            await websocket.receive_text()
            for _ in range(50):
                seq, jpeg = camera.latest_jpeg()
                if jpeg is not None and seq != last_seq:
                    last_seq = seq
                    await websocket.send_bytes(jpeg)
                    break
                await asyncio.sleep(0.002)
            else:
                seq, jpeg = camera.latest_jpeg()
                if jpeg is not None:
                    last_seq = seq
                    await websocket.send_bytes(jpeg)
    except WebSocketDisconnect:
        pass
    except Exception:
        try:
            await websocket.close()
        except Exception:
            pass
    finally:
        camera.preview_client_disconnected()
