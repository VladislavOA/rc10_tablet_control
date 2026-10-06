#!/usr/bin/env python3

import argparse
import json
import time
from pathlib import Path

import numpy as np

from rc10_api.rc_api import RobotApi


def read_pose(robot, kind, name):
    """Считать текущую позицию робота из RTD."""

    rt = robot._rtd_receiver.rt_data

    joints_rad = np.asarray(rt.act_q, dtype=float)
    tcp_rad = np.asarray(rt.act_tcp_x, dtype=float)

    joints_deg = np.degrees(joints_rad)

    tcp = tcp_rad.copy()
    tcp[3:6] = np.degrees(tcp[3:6])

    return {
        "type": kind,
        "name": name,
        "joints_deg": [round(float(x), 6) for x in joints_deg],
        "tcp": [round(float(x), 6) for x in tcp],
    }


def describe(i, step):
    t = step["type"]

    if t in ("joint", "linear"):
        tcp = step["tcp"]

        return (
            f"{i}. {t} {step['name']} "
            f"xyz=({tcp[0]:.3f}, {tcp[1]:.3f}, {tcp[2]:.3f})"
        )

    if t == "set_output":
        return (
            f"{i}. output "
            f"{step['index']}={int(step['value'])}"
        )

    if t == "wait":
        return f"{i}. wait {step['seconds']} s"

    return f"{i}. {step}"


def save(path, steps):
    data = {
        "version": 1,
        "units": {
            "joints": "deg",
            "xyz": "m",
            "rpy": "deg",
        },
        "steps": steps,
    }

    path.write_text(
        json.dumps(
            data,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def main():
    ap = argparse.ArgumentParser(
        description="Запись точек RC10 в READ ONLY режиме"
    )

    ap.add_argument(
        "file",
        type=Path,
        help="JSON-файл программы",
    )

    ap.add_argument(
        "--ip",
        default="10.10.10.10",
        help="IP контроллера RC10",
    )

    ap.add_argument(
        "--append",
        action="store_true",
        help="добавить точки в существующий файл",
    )

    ap.add_argument(
        "--force",
        action="store_true",
        help="перезаписать существующий файл",
    )

    args = ap.parse_args()

    steps = []

    if args.file.exists():
        if args.append:
            steps = json.loads(
                args.file.read_text(encoding="utf-8")
            )["steps"]

        elif not args.force:
            raise SystemExit(
                f"{args.file} уже существует: "
                f"используйте --append или --force"
            )

    print(f"Подключение к {args.ip} в READ ONLY...")

    robot = RobotApi(
        ip=args.ip,
        read_only=True,
        timeout=5,
    )

    try:
        # Дать RTD получить первые данные
        time.sleep(0.3)

        print("READ ONLY подключение успешно.")
        print()
        print("Двигайте робот через штатное ПО RC10.")
        print()
        print("Команды:")
        print("  j [имя]   сохранить текущую точку как joint")
        print("  l [имя]   сохранить текущую точку как linear")
        print("  o N 0/1   добавить set_output в программу")
        print("  w SEC     добавить ожидание")
        print("  u         удалить последний шаг")
        print("  p         показать записанные шаги")
        print("  q         сохранить и выйти")
        print()
        print("Enter без команды = j")
        print()

        while True:
            try:
                line = input(
                    f"[{len(steps)} шагов] > "
                ).strip()

            except (EOFError, KeyboardInterrupt):
                print()
                break

            parts = line.split()

            cmd = (
                parts[0].lower()
                if parts
                else "j"
            )

            rest = parts[1:]

            try:
                if cmd in ("j", "l"):

                    n = (
                        sum(
                            s["type"] in ("joint", "linear")
                            for s in steps
                        )
                        + 1
                    )

                    name = (
                        rest[0]
                        if rest
                        else f"P{n}"
                    )

                    kind = (
                        "joint"
                        if cmd == "j"
                        else "linear"
                    )

                    pose = read_pose(
                        robot,
                        kind,
                        name,
                    )

                    steps.append(pose)

                    print(
                        "  +",
                        describe(
                            len(steps),
                            pose,
                        ),
                    )

                elif cmd == "o":

                    idx = int(rest[0])
                    val = int(rest[1])

                    if not (
                        0 <= idx <= 23
                        and val in (0, 1)
                    ):
                        raise ValueError

                    step = {
                        "type": "set_output",
                        "index": idx,
                        "value": bool(val),
                    }

                    steps.append(step)

                    print(
                        "  +",
                        describe(
                            len(steps),
                            step,
                        ),
                    )

                elif cmd == "w":

                    step = {
                        "type": "wait",
                        "seconds": float(rest[0]),
                    }

                    steps.append(step)

                    print(
                        "  +",
                        describe(
                            len(steps),
                            step,
                        ),
                    )

                elif cmd == "u":

                    if steps:
                        removed = steps.pop()

                        print(
                            "  - удалён:",
                            describe(
                                len(steps) + 1,
                                removed,
                            ),
                        )

                elif cmd == "p":

                    if not steps:
                        print("  пока пусто")

                    for i, step in enumerate(
                        steps,
                        1,
                    ):
                        print(
                            describe(
                                i,
                                step,
                            )
                        )

                elif cmd == "q":
                    break

                else:
                    print(
                        "  неизвестная команда "
                        "(j/l/o/w/u/p/q)"
                    )

                    continue

            except (
                ValueError,
                IndexError,
            ):
                print(
                    "  неверные аргументы"
                )

                continue

            # Автосохранение
            save(
                args.file,
                steps,
            )

    finally:
        save(
            args.file,
            steps,
        )

        print(
            f"Сохранено шагов: "
            f"{len(steps)} -> {args.file}"
        )

        robot._shutdown_api_sockets()


if __name__ == "__main__":
    main()