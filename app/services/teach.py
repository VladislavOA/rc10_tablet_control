#!/usr/bin/env python3
"""
teach.py — запись программы по контрольным точкам в режиме Free Drive.

Запуск:
    python teach.py program.json                 # новая программа
    python teach.py program.json --append        # дописать в существующую
    python teach.py program.json --ip 10.10.10.10

Робот снимается с тормозов (состояние 'run') и переводится в Free Drive:
двигайте его рукой, а в консоли записывайте шаги программы.

Команды в консоли:
    Enter | j [имя]   записать текущую позу как точку 'joint' (MoveJ, по осям)
    l [имя]           записать текущую позу как точку 'linear' (MoveL, по прямой)
    o <idx> <0|1>     шаг: цифровой выход idx (0-23) = 0/1 (например, захват)
    w <сек>           шаг: пауза
    u                 удалить последний шаг
    p                 показать все шаги
    q                 сохранить и выйти

ВАЖНО: держите руку у кнопки аварийной остановки. Для точной компенсации
гравитации в Free Drive заранее задайте TOOL_OFFSET и PAYLOAD ниже.
"""
import argparse
import json
import threading
import time
from pathlib import Path

from rc10_api.rc_api import RobotApi

# ---- Настройки инструмента (None = не менять то, что уже есть в контроллере) --
TOOL_OFFSET = None   # (x, y, z, rx, ry, rz): метры и ГРАДУСЫ, смещение TCP от фланца
PAYLOAD = None       # (масса_кг, (cx, cy, cz)): центр масс в СК фланца, метры
# ------------------------------------------------------------------------------

FORMAT_VERSION = 1


class FreeDriveKeeper(threading.Thread):
    """Free Drive — циклическая команда: её нужно слать ~100 Гц, пока режим нужен.
    Как только отправка прекращается, режим заканчивается."""

    def __init__(self, robot, hz=100):
        super().__init__(daemon=True)
        self._robot = robot
        self._period = 1.0 / hz
        self._stop_evt = threading.Event()
        self.error = None

    def run(self):
        next_t = time.monotonic()
        while not self._stop_evt.is_set():
            try:
                self._robot.motion.free_drive(True)
            except Exception as exc:  # сокет закрыт, авария и т.п.
                self.error = exc
                return
            next_t += self._period
            delay = next_t - time.monotonic()
            if delay > 0:
                time.sleep(delay)
            else:
                next_t = time.monotonic()

    def stop(self):
        self._stop_evt.set()
        if self.is_alive():
            self.join(timeout=1)


def read_pose(robot, kind, name):
    """Текущая поза в обоих представлениях: углы суставов и TCP."""
    joints = robot.motion.joint.get_actual_position(units="deg")
    tcp = robot.motion.linear.get_actual_position(orientation_units="deg")
    return {
        "type": kind,
        "name": name,
        "joints_deg": [round(float(v), 5) for v in joints],
        "tcp": [round(float(v), 6) for v in tcp[:6]],  # x,y,z [м]; rx,ry,rz [град]
    }


def describe(i, s):
    if s["type"] in ("joint", "linear"):
        j = ", ".join(f"{v:.1f}" for v in s["joints_deg"])
        xyz = ", ".join(f"{v * 1000:.0f}" for v in s["tcp"][:3])
        return f"{i:>3}. {s['type']:<6} {s['name']:<14} q[deg]=[{j}]  xyz[mm]=[{xyz}]"
    if s["type"] == "set_output":
        return f"{i:>3}. set_output  DO{s['index']} = {int(s['value'])}"
    if s["type"] == "wait":
        return f"{i:>3}. wait        {s['seconds']} c"
    return f"{i:>3}. ?"


def save(path, steps):
    data = {
        "version": FORMAT_VERSION,
        "units": {"joints": "deg", "xyz": "m", "rpy": "deg"},
        "steps": steps,
    }
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


def main():
    ap = argparse.ArgumentParser(description="Запись контрольных точек (Free Drive)")
    ap.add_argument("file", type=Path, help="куда сохранить программу (.json)")
    ap.add_argument("--ip", default="10.10.10.10")
    ap.add_argument("--append", action="store_true", help="дописать в существующий файл")
    ap.add_argument("--force", action="store_true", help="перезаписать существующий файл")
    args = ap.parse_args()

    steps = []
    if args.file.exists():
        if args.append:
            steps = json.loads(args.file.read_text(encoding="utf-8"))["steps"]
        elif not args.force:
            raise SystemExit(f"{args.file} уже существует: используйте --append или --force")

    robot = RobotApi(ip=args.ip, read_only=False, timeout=5)
    keeper = None
    try:
        if TOOL_OFFSET is not None:
            robot.tool.set(TOOL_OFFSET, units="deg")
        if PAYLOAD is not None:
            robot.payload.set(mass=PAYLOAD[0], tcp_mass_center=PAYLOAD[1])

        robot.controller_state.set("run", await_sec=120)  # снять с тормозов
        keeper = FreeDriveKeeper(robot)
        keeper.start()
        print("Free Drive включён — двигайте робота рукой.")
        print(__doc__.split("Команды в консоли:")[1].split("ВАЖНО")[0])

        while True:
            if keeper.error:
                raise RuntimeError(f"Free Drive прервался: {keeper.error!r}")
            try:
                line = input(f"[{len(steps)} шагов] > ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break

            parts = line.split()
            cmd = parts[0].lower() if parts else "j"
            rest = parts[1:]
            try:
                if cmd in ("j", "l"):
                    n = sum(s["type"] in ("joint", "linear") for s in steps) + 1
                    name = rest[0] if rest else f"P{n}"
                    kind = "joint" if cmd == "j" else "linear"
                    steps.append(read_pose(robot, kind, name))
                    print("  +", describe(len(steps), steps[-1]))
                elif cmd == "o":
                    idx, val = int(rest[0]), int(rest[1])
                    if not (0 <= idx <= 23 and val in (0, 1)):
                        raise ValueError
                    steps.append({"type": "set_output", "index": idx, "value": bool(val)})
                    print("  +", describe(len(steps), steps[-1]))
                elif cmd == "w":
                    steps.append({"type": "wait", "seconds": float(rest[0])})
                    print("  +", describe(len(steps), steps[-1]))
                elif cmd == "u":
                    if steps:
                        print("  - удалён:", describe(len(steps), steps.pop()))
                elif cmd == "p":
                    for i, s in enumerate(steps, 1):
                        print(describe(i, s))
                elif cmd == "q":
                    break
                else:
                    print("  неизвестная команда (j/l/o/w/u/p/q)")
                    continue
            except (ValueError, IndexError):
                print("  неверные аргументы, см. список команд выше")
                continue
            save(args.file, steps)  # автосохранение после каждого изменения
    finally:
        if keeper:
            keeper.stop()
        try:
            robot.motion.mode.set("hold")  # выйти из Free Drive, удерживать позицию
        except Exception as exc:
            print("Не удалось перевести в hold:", exc)
        save(args.file, steps)
        print(f"Сохранено шагов: {len(steps)} -> {args.file}")
        robot._shutdown_api_sockets()


if __name__ == "__main__":
    main()
