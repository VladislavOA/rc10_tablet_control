#!/usr/bin/env python3
"""
play.py — плавное воспроизведение программы RC10.

Логика:
1. Загружает JSON.
2. Для каждого непрерывного блока motion-точек строит плотный путь:
   XYZ -> PCHIP, ориентация -> SLERP.
3. Полностью проверяет весь сгенерированный путь через IK.
4. Только после успешной проверки начинает движение.
5. Уже готовый путь подаёт контроллеру небольшим rolling-window.
"""

import argparse
import json
import math
import time
from pathlib import Path

import numpy as np
from scipy.interpolate import PchipInterpolator
from scipy.spatial.transform import Rotation as Rot, Slerp

from rc10_api.rc_api import RobotApi


MOTION = ("joint", "linear")


def load_steps(path: Path):
    path = Path(path)
    if not path.is_file():
        alt = Path("data/trajectories") / path
        if alt.is_file():
            path = alt

    data = json.loads(path.read_text(encoding="utf-8"))
    steps = data["steps"]

    for i, s in enumerate(steps, 1):
        t = s.get("type")
        if t in MOTION:
            if len(s.get("joints_deg", [])) != 6:
                raise ValueError(f"шаг {i}: нужны 6 значений joints_deg")
            if len(s.get("tcp", [])) != 6:
                raise ValueError(f"шаг {i}: нужны 6 значений tcp")
        elif t == "set_output":
            if not 0 <= int(s["index"]) <= 23:
                raise ValueError(f"шаг {i}: index выхода должен быть 0..23")
        elif t == "wait":
            if float(s["seconds"]) < 0:
                raise ValueError(f"шаг {i}: пауза < 0")
        else:
            raise ValueError(f"шаг {i}: неизвестный тип {t!r}")

    return path, steps


def normalize_pose_rad(pose):
    pose = np.asarray(pose, float).copy()
    pose[3:6] = (pose[3:6] + math.pi) % (2 * math.pi) - math.pi
    return pose


def build_smooth_path(block, step_m=0.015, max_rot_step_deg=2.0):
    if len(block) == 1:
        return [np.asarray(block[0]["tcp"], float)]

    tcp = np.asarray([s["tcp"] for s in block], float)
    xyz = tcp[:, :3]

    segment_lengths = np.linalg.norm(np.diff(xyz, axis=0), axis=1)
    segment_lengths = np.maximum(segment_lengths, 1e-6)
    u = np.r_[0.0, np.cumsum(segment_lengths)]

    xyz_interp = PchipInterpolator(u, xyz, axis=0)

    rotations = Rot.from_euler("xyz", tcp[:, 3:6], degrees=True)
    slerp = Slerp(u, rotations)

    linear_samples = int(np.ceil(u[-1] / step_m)) + 1

    rot_angles = [
        math.degrees((a.inv() * b).magnitude())
        for a, b in zip(rotations[:-1], rotations[1:])
    ]
    rotation_samples = int(np.ceil(sum(rot_angles) / max_rot_step_deg)) + 1

    n = max(2, linear_samples, rotation_samples)
    uu = np.linspace(0.0, u[-1], n)

    pos = xyz_interp(uu)
    rpy = slerp(uu).as_euler("xyz", degrees=True)

    return [np.r_[p, r] for p, r in zip(pos, rpy)]


def check_ik(robot, path):
    q = np.asarray(robot._rtd_receiver.rt_data.act_q, float)
    print(f"[IK] проверяю {len(path)} точек...")

    for i, pose_deg in enumerate(path):
        pose_rad = np.asarray(pose_deg, float).copy()
        pose_rad[3:6] = np.radians(pose_rad[3:6])
        pose_rad = normalize_pose_rad(pose_rad)

        sol = robot.motion.kinematics.get_inverse(
            tcp_pose=list(pose_rad),
            angle_pose=list(q),
            orientation_units="rad",
            get_all=False,
        )

        if sol is None:
            raise RuntimeError(
                f"Недостижимая точка {i}/{len(path)-1}: "
                f"xyz={np.round(pose_deg[:3], 4)}, "
                f"rpy={np.round(pose_deg[3:6], 2)}"
            )

        q = np.asarray(sol, float)
        if i % 25 == 0 or i == len(path) - 1:
            print(f"[IK] {i+1}/{len(path)} OK")

    print("[IK] весь маршрут достижим")


def wait_motion_done(robot):
    warned = False
    while not robot.motion.check_waypoint_completion(0):
        mode = robot.motion.mode.get()
        if mode == "pause":
            if not warned:
                print("ПАУЗА:", robot.motion.mode.check_warning_status())
                warned = True
        else:
            warned = False
        time.sleep(0.02)


def add_linear(robot, pose_deg, args, blend):
    robot.motion.linear.add_new_waypoint(
        tcp_pose=list(np.asarray(pose_deg, float)),
        speed=args.lin_speed,
        accel=args.lin_accel,
        blend=blend,
        orientation_units="deg",
    )


def execute_smooth_path(robot, path, args):
    if not path:
        return

    rt = robot._rtd_receiver.rt_data
    window = args.window

    robot.motion.mode.set("hold")

    i = 0
    total = len(path)

    while i < total and i < window:
        blend = 0.0 if i == total - 1 else args.blend
        add_linear(robot, path[i], args, blend)
        i += 1

    robot.motion.mode.set("move")

    while i < total:
        mode = robot.motion.mode.get()

        if mode == "pause":
            print("ПАУЗА:", robot.motion.mode.check_warning_status())
            time.sleep(0.05)
            continue

        if getattr(rt, "buff_fill", 0) < window:
            blend = 0.0 if i == total - 1 else args.blend
            add_linear(robot, path[i], args, blend)
            i += 1
        else:
            time.sleep(0.005)

    wait_motion_done(robot)


def move_to_first_point(robot, first, args):
    cur = robot.motion.joint.get_actual_position(units="deg")
    jump = max(abs(a - b) for a, b in zip(cur, first["joints_deg"]))

    print(
        f"Переезд в первую точку {first.get('name', '?')}: "
        f"макс. поворот сустава {jump:.1f}°"
    )

    robot.motion.joint.add_new_waypoint(
        angle_pose=first["joints_deg"],
        speed=args.joint_speed,
        accel=args.joint_accel,
        blend=0.0,
        units="deg",
    )

    robot.motion.mode.set("move")
    robot.motion.wait_waypoint_completion(0)


def split_motion_blocks(steps):
    result = []
    block = []

    for s in steps:
        if s["type"] in MOTION:
            block.append(s)
            continue

        if block:
            result.append(("motion", block))
            block = []

        result.append(("action", s))

    if block:
        result.append(("motion", block))

    return result


def build_all_plans(steps, args):
    program = []

    for kind, item in split_motion_blocks(steps):
        if kind == "motion":
            path = build_smooth_path(
                item,
                step_m=args.step,
                max_rot_step_deg=args.rot_step,
            )
            program.append(("motion", item, path))
        else:
            program.append(("action", item))

    return program


def main():
    ap = argparse.ArgumentParser(description="Плавное воспроизведение программы RC10")

    ap.add_argument("file", type=Path)
    ap.add_argument("--ip", default="10.10.10.10")

    ap.add_argument("--scale", type=float, default=0.5)
    ap.add_argument("--joint-speed", type=float, default=25.0)
    ap.add_argument("--joint-accel", type=float, default=60.0)
    ap.add_argument("--lin-speed", type=float, default=0.10)
    ap.add_argument("--lin-accel", type=float, default=0.30)
    ap.add_argument("--blend", type=float, default=0.01)
    ap.add_argument("--step", type=float, default=0.015)
    ap.add_argument("--rot-step", type=float, default=2.0)
    ap.add_argument("--window", type=int, default=5)
    ap.add_argument("--loops", type=int, default=1)
    ap.add_argument("--yes", action="store_true")
    ap.add_argument("--dry-run", action="store_true")

    args = ap.parse_args()

    path, steps = load_steps(args.file)
    print(f"Программа: {path}")
    print(f"Исходных шагов: {len(steps)}")

    program = build_all_plans(steps, args)

    total_generated = sum(
        len(entry[2])
        for entry in program
        if entry[0] == "motion"
    )

    print(f"Полный плавный маршрут построен: {total_generated} промежуточных TCP-точек")

    for i, entry in enumerate(program, 1):
        if entry[0] == "motion":
            block, smooth = entry[1], entry[2]
            print(
                f"  блок {i}: "
                f"{block[0].get('name','?')} -> {block[-1].get('name','?')}, "
                f"{len(block)} исходных -> {len(smooth)} плавных"
            )
        else:
            print(f"  действие {i}: {entry[1]['type']}")

    if args.dry_run:
        return

    robot = RobotApi(ip=args.ip, read_only=False, timeout=5)

    try:
        robot.motion.scale_setup.set(
            velocity=args.scale,
            acceleration=args.scale,
        )

        robot.controller_state.set("run", await_sec=120)
        robot.motion.mode.set("hold")

        for idx, entry in enumerate(program, 1):
            if entry[0] == "motion":
                print(f"[PLAN] IK-check блока {idx}")
                check_ik(robot, entry[2])

        print("[PLAN] ВЕСЬ МАРШРУТ ПОСТРОЕН И ПРОШЁЛ IK")

        first = next((s for s in steps if s["type"] in MOTION), None)
        if first is None:
            print("Нет точек движения.")
            return

        if not args.yes:
            answer = input("Путь свободен? Начать движение? [y/N] ").strip().lower()
            if answer != "y":
                print("Отменено.")
                return

        for loop_no in range(1, args.loops + 1):
            print(f"Цикл {loop_no}/{args.loops}")
            move_to_first_point(robot, first, args)

            for entry in program:
                if entry[0] == "motion":
                    execute_smooth_path(robot, entry[2], args)
                    continue

                s = entry[1]

                if s["type"] == "set_output":
                    print(f"DO{s['index']} = {int(bool(s['value']))}")
                    robot.io.digital.set_output(
                        int(s["index"]),
                        bool(s["value"]),
                    )

                elif s["type"] == "wait":
                    print(f"Пауза {s['seconds']} с")
                    time.sleep(float(s["seconds"]))

        print("Готово.")

    except KeyboardInterrupt:
        print("\nОстановлено пользователем.")

    finally:
        try:
            robot.motion.mode.set("hold")
        except Exception as exc:
            print("Не удалось перевести в hold:", exc)

        robot._shutdown_api_sockets()


if __name__ == "__main__":
    main()