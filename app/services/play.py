#!/usr/bin/env python3
"""
play.py — воспроизведение программы, записанной teach.py, с плавным сглаживанием точек (blend).

Запуск:
    python play.py program.json --dry-run          # только показать план, без робота
    python play.py program.json                    # плавно, с blend=0.03 м
    python play.py program.json --blend 0.05 --scale 0.5 --loops 3 --yes

Итоговая скорость = заданная скорость (--joint-speed / --lin-speed) x --scale.
"""
import argparse
import json
import time
from pathlib import Path

from rc10_api.rc_api import RobotApi

MOTION = ("joint", "linear")


def load_steps(path):
    path = Path('data/trajectories') / path
    data = json.loads(path.read_text(encoding="utf-8"))
    steps = data["steps"]
    for i, s in enumerate(steps, 1):
        t = s.get("type")
        if t in MOTION:
            if len(s.get("joints_deg", [])) != 6 or len(s.get("tcp", [])) != 6:
                raise ValueError(f"шаг {i}: нужны 6 значений joints_deg и tcp")
        elif t == "set_output":
            if not 0 <= int(s["index"]) <= 23:
                raise ValueError(f"шаг {i}: index выхода должен быть 0-23")
        elif t == "wait":
            if float(s["seconds"]) < 0:
                raise ValueError(f"шаг {i}: пауза < 0")
        else:
            raise ValueError(f"шаг {i}: неизвестный тип {t!r}")
    return steps


def wait_motion_done(robot):
    """Ждать, пока очередь точек не опустеет. Сообщает о паузе (safeguard/столкновение)."""
    warned = False
    while not robot.motion.check_waypoint_completion(0):
        if robot.motion.mode.get() == "pause":
            if not warned:
                print("  ПАУЗА:", robot.motion.mode.check_warning_status(),
                      "— снимите причину; Ctrl+C для остановки")
                warned = True
        else:
            warned = False
        time.sleep(0.02)


def add_step_to_robot(robot, s, point_blend, args):
    """Вспомогательная функция отправки одной точки."""
    if s["type"] == "joint":
        robot.motion.joint.add_new_waypoint(
            angle_pose=s["joints_deg"],
            speed=args.joint_speed,
            accel=args.joint_accel,
            blend=point_blend,
            units="deg",
        )
    else:
        robot.motion.linear.add_new_waypoint(
            tcp_pose=s["tcp"],
            speed=args.lin_speed,
            accel=args.lin_accel,
            blend=point_blend,
            orientation_units="deg",
        )


def run_block(robot, block, args):
    """
    Выполнить подряд идущие шаги движения как одну плавную траекторию.
    Поддерживает длинные последовательности точек без переполнения буфера.
    """
    if not block:
        return

    rt = robot._rtd_receiver.rt_data
    # Окно предварительной загрузки (размер буфера контроллера за вычетом запаса)
    window = max(5, int(getattr(rt, "buff_sz", 20) or 20) - 2)

    robot.motion.mode.set("hold")  # сбросить старую очередь
    total = len(block)
    i = 0

    # 1. Предзаполнение буфера ядра контроллера
    while i < total and i < window:
        is_last = (i == total - 1)
        point_blend = 0.0 if is_last else args.blend
        add_step_to_robot(robot, block[i], point_blend, args)
        i += 1

    robot.motion.mode.set("move")

    # 2. Потоковое добавление оставшихся точек по мере освобождения очереди
    while i < total:
        if robot.motion.mode.get() == "pause":
            time.sleep(0.05)
            continue

        if getattr(rt, "buff_fill", 0) < window:
            is_last = (i == total - 1)
            point_blend = 0.0 if is_last else args.blend
            add_step_to_robot(robot, block[i], point_blend, args)
            i += 1
        else:
            time.sleep(0.005)

    wait_motion_done(robot)


def run_program(robot, steps, args):
    block = []
    for i, s in enumerate(steps, 1):
        if s["type"] in MOTION:
            block.append(s)
            continue
        # Если встретили I/O или wait — сначала плавно доезжаем до конца блока движения
        run_block(robot, block, args)
        block = []
        if s["type"] == "set_output":
            print(f"  шаг {i}: DO{s['index']} = {int(bool(s['value']))}")
            robot.io.digital.set_output(int(s["index"]), bool(s["value"]))
        else:
            print(f"  шаг {i}: пауза {s['seconds']} c")
            time.sleep(float(s["seconds"]))
    run_block(robot, block, args)


def main():
    ap = argparse.ArgumentParser(description="Воспроизведение программы RC10")
    ap.add_argument("file", type=Path)
    ap.add_argument("--ip", default="10.10.10.10")
    ap.add_argument("--scale", type=float, default=0.3, help="множитель скорости/ускорения 0..1")
    ap.add_argument("--joint-speed", type=float, default=30, help="град/с (0..180)")
    ap.add_argument("--joint-accel", type=float, default=60, help="град/с^2 (0..1500)")
    ap.add_argument("--lin-speed", type=float, default=0.1, help="м/с (0..3)")
    ap.add_argument("--lin-accel", type=float, default=0.25, help="м/с^2 (0..15)")
    # Ненулевой blend по умолчанию устраняет остановки в точках:
    ap.add_argument("--blend", type=float, default=0.03, help="радиус сглаживания в метрах (например 0.02 - 0.05)")
    ap.add_argument("--loops", type=int, default=1)
    ap.add_argument("--yes", action="store_true", help="не спрашивать подтверждение")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    steps = load_steps(args.file)
    print(f"Программа: {args.file}, шагов: {len(steps)}, циклов: {args.loops}, blend: {args.blend} м")
    for i, s in enumerate(steps, 1):
        label = {"set_output": f"DO{s.get('index')} = {int(bool(s.get('value')))}",
                 "wait": f"{s.get('seconds')} c"}.get(s["type"], s.get("name", ""))
        print(f"  {i:>3}. {s['type']:<10} {label}")
    if args.dry_run or not steps:
        return

    robot = RobotApi(ip=args.ip, read_only=False, timeout=5)
    try:
        robot.motion.scale_setup.set(velocity=args.scale, acceleration=args.scale)
        robot.controller_state.set("run", await_sec=120)
        robot.motion.mode.set("hold")

        first = next((s for s in steps if s["type"] in MOTION), None)
        if first and not args.yes:
            cur = robot.motion.joint.get_actual_position(units="deg")
            jump = max(abs(a - b) for a, b in zip(cur, first["joints_deg"]))
            print(f"Первое движение: до {first['name']}, максимальный поворот сустава {jump:.1f} град.")
            if input("Путь свободен? Начать? [y/N] ").strip().lower() != "y":
                print("Отменено.")
                return

        for n in range(1, args.loops + 1):
            print(f"Цикл {n}/{args.loops}")
            run_program(robot, steps, args)
        print("Готово.")
    except KeyboardInterrupt:
        print("\nОстановлено пользователем.")
    finally:
        try:
            robot.motion.mode.set("hold")  # остановка + сброс очереди
        except Exception as exc:
            print("Не удалось перевести в hold:", exc)
        robot._shutdown_api_sockets()


if __name__ == "__main__":
    main()