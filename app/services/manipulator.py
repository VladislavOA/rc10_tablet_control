#!/usr/bin/env python3

import subprocess
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]
TRAJECTORY_DIR = BASE_DIR / "data" / "trajectories"
PLAY_SCRIPT = Path(__file__).with_name("play.py")


def execute_manipulator_trajectory(
    json_name: str,
    ip: str = "10.10.10.10",
    lin_speed: float = 0.80,
    joint_speed: float = 80.0,
    lin_accel: float = 0.80,
    joint_accel: float = 80.0,
    blend: float = 0.005,
    scale: float = 1.0,
    step: float = 0.015,
    rot_step: float = 2.0,
    window: int = 5,
    loops: int = 1,
) -> bool:

    json_path = Path(json_name).expanduser()

    if not json_path.is_absolute():
        candidates = (
            json_path,
            TRAJECTORY_DIR / json_path,
            BASE_DIR / json_path,
        )

        json_path = next(
            (p.resolve() for p in candidates if p.is_file()),
            json_path,
        )

    if not json_path.is_file():
        print(f"Ошибка: файл '{json_name}' не найден.")
        return False

    cmd = [
        sys.executable,
        str(PLAY_SCRIPT),
        str(json_path),
        "--ip", str(ip),
        "--lin-speed", str(lin_speed),
        "--joint-speed", str(joint_speed),
        "--lin-accel", str(lin_accel),
        "--joint-accel", str(joint_accel),
        "--blend", str(blend),
        "--scale", str(scale),
        "--step", str(step),
        "--rot-step", str(rot_step),
        "--window", str(window),
        "--loops", str(loops),
        "--yes",
    ]

    try:
        result = subprocess.run(cmd, cwd=BASE_DIR)
        return result.returncode == 0

    except KeyboardInterrupt:
        print("Остановлено пользователем.")
        return False

    except subprocess.SubprocessError as exc:
        print(f"Ошибка запуска play.py: {exc}")
        return False


if __name__ == "__main__":
    success = execute_manipulator_trajectory("arab3.json")

    if success:
        print("Программа робота успешно завершена.")
    else:
        print("Воспроизведение завершилось с ошибкой.")