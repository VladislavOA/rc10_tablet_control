from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional


@dataclass
class RobotSnapshot:
    backend: str
    ip: str
    connected: bool
    moving: bool
    state: str
    progress: int
    error: Optional[str] = None


class RobotController:
    def __init__(self, backend: str, ip: str, reconnect_attempts: int = 3, reconnect_delay: float = 1.0):
        self.backend = backend
        self.ip = ip
        self.reconnect_attempts = max(1, reconnect_attempts)
        self.reconnect_delay = max(0.0, reconnect_delay)
        self._robot = None
        self._connected = False
        self._moving = False
        self._state = "offline"
        self._progress = 0
        self._error: Optional[str] = None
        self._stop_event = threading.Event()
        self._lock = threading.RLock()

    def _api_connection_alive(self) -> bool:
        if self.backend == "mock":
            return self._connected
        if self._robot is None:
            return False
        try:
            return bool(self._robot.is_connected())
        except Exception:
            return False

    def disconnect(self) -> None:
        with self._lock:
            robot = self._robot
            self._robot = None
            self._connected = False
            self._moving = False
            self._state = "offline"
        if robot is not None:
            try:
                robot.disconnect()
            except Exception:
                pass

    def connect(self) -> bool:
        self.disconnect()
        with self._lock:
            self._error = None

        if self.backend == "mock":
            time.sleep(0.15)
            with self._lock:
                self._connected = True
                self._state = "ready"
            return True

        if self.backend != "robopro":
            raise RuntimeError(f"Неизвестный ROBOT_BACKEND={self.backend}")

        try:
            from API.rc_api import RobotApi
            robot = RobotApi(self.ip, autoconnect=False, show_std_traceback=True)
            connected = bool(robot.connect())
            with self._lock:
                self._robot = robot if connected else None
                self._connected = connected
                self._state = "ready" if connected else "offline"
            return connected
        except Exception as exc:
            with self._lock:
                self._error = str(exc)
                self._connected = False
                self._state = "error"
            raise

    def reconnect(self) -> bool:
        last_error: Optional[Exception] = None
        for attempt in range(1, self.reconnect_attempts + 1):
            try:
                if self.connect():
                    return True
            except Exception as exc:
                last_error = exc
            if attempt < self.reconnect_attempts:
                time.sleep(self.reconnect_delay)
        if last_error:
            raise RuntimeError(f"Не удалось переподключиться к роботу: {last_error}")
        raise RuntimeError("Не удалось переподключиться к роботу")

    def ensure_connected(self, force_check: bool = False):
        alive = self._api_connection_alive() if (force_check or self._connected) else False
        with self._lock:
            self._connected = alive
            if not alive and self._state != "error":
                self._state = "offline"
        if not alive:
            self.reconnect()

    def stop(self):
        self._stop_event.set()
        with self._lock:
            if self._robot is not None:
                try:
                    self._robot.motion.mode.set("hold")
                except Exception:
                    pass
            self._moving = False
            self._state = "ready" if self._connected else "offline"

    def play_trajectory(self, trajectory_path: Path, on_progress: Optional[Callable[[int], None]] = None):
        self.ensure_connected(force_check=True)
        data = json.loads(trajectory_path.read_text(encoding="utf-8"))
        points = data.get("points", [])
        speed = float(data.get("speed", 10))
        accel = float(data.get("accel", 10))
        if not points:
            raise ValueError("В траектории нет точек")

        self._stop_event.clear()
        with self._lock:
            self._moving = True
            self._state = "moving"
            self._progress = 0

        try:
            if self.backend == "mock":
                for i, _point in enumerate(points, start=1):
                    if self._stop_event.is_set():
                        break
                    time.sleep(1.0)
                    progress = round(i / len(points) * 100)
                    with self._lock:
                        self._progress = progress
                    if on_progress:
                        on_progress(progress)
                return

            robot = self._robot
            try:
                robot.controller_state.set("run", await_sec=120)
            except Exception:
                pass

            for point in points:
                if self._stop_event.is_set():
                    break
                try:
                    robot.motion.joint.add_new_waypoint(
                        angle_pose=tuple(point), speed=speed, accel=accel, blend=0, units="deg"
                    )
                except TypeError:
                    robot.motion.joint.add_new_waypoint(
                        tuple(point), speed=speed, accel=accel, blend=0, units="deg"
                    )

            if not self._stop_event.is_set():
                robot.motion.mode.set("move")
                robot.motion.wait_waypoint_completion(0)
                with self._lock:
                    self._progress = 100
                if on_progress:
                    on_progress(100)
        except Exception as exc:
            # Mark it disconnected if the API connection disappeared, so next start reconnects.
            if not self._api_connection_alive():
                with self._lock:
                    self._connected = False
            with self._lock:
                self._error = str(exc)
                self._state = "error"
            raise
        finally:
            with self._lock:
                self._moving = False
                if self._state != "error":
                    self._state = "ready" if self._connected else "offline"

    def snapshot(self) -> RobotSnapshot:
        with self._lock:
            return RobotSnapshot(
                backend=self.backend,
                ip=self.ip,
                connected=self._connected,
                moving=self._moving,
                state=self._state,
                progress=self._progress,
                error=self._error,
            )
