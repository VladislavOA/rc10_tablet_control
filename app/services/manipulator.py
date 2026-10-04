import sys
import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
TRAJECTORY_DIR = BASE_DIR / "data" / "trajectories"
PLAY_SCRIPT = Path(__file__).with_name("play.py")


def execute_manipulator_trajectory(
    json_name: str,
    ip: str = "10.10.10.10",
    lin_speed: float = 0.25,
    joint_speed: float = 50.0,
    lin_accel: float = 0.6,
    joint_accel: float = 100.0,
    blend: float = 0.04,
    scale: float = 0.5,
    loops: int = 1,
) -> bool:
    """Запускает play.py для воспроизведения траектории робота.

    :param json_name: Имя или путь к JSON-файлу с программой (например, 'arab2.json')
    :param ip: IP-адрес контроллера робота
    :param lin_speed: Линейная скорость TCP (м/с)
    :param joint_speed: Скорость суставов (град/с)
    :param lin_accel: Линейное ускорение (м/с²)
    :param joint_accel: Суставное ускорение (град/с²)
    :param blend: Радиус сглаживания траектории (м)
    :param scale: Глобальный множитель скорости/ускорения (0.0 .. 1.0)
    :param loops: Количество циклов воспроизведения
    :return: True, если программа выполнилась успешно (код возврата 0), иначе False
    """
    json_path = Path(json_name).expanduser()
    if not json_path.is_absolute():
        candidates = (json_path, TRAJECTORY_DIR / json_path, BASE_DIR / json_path)
        json_path = next((path.resolve() for path in candidates if path.is_file()), json_path)
    if not json_path.is_file():
        print(f"Ошибка: Файл '{json_name}' не найден.")
        return False

    cmd = [
        sys.executable,  # текущий интерпретатор Python
        str(PLAY_SCRIPT),
        str(json_path),
        "--ip", str(ip),
        "--lin-speed", str(lin_speed),
        "--joint-speed", str(joint_speed),
        "--lin-accel", str(lin_accel),
        "--joint-accel", str(joint_accel),
        "--blend", str(blend),
        "--scale", str(scale),
        "--loops", str(loops),
        "--yes",  # флаг автоматического подтверждения без ожидания ввода [y/N]
    ]

    try:
        # Запуск процесса; вывод транслируется в консоль в реальном времени
        result = subprocess.run(cmd, cwd=BASE_DIR)
        return result.returncode == 0
    except (KeyboardInterrupt, subprocess.SubprocessError, Exception) as exc:
        print(f"Исключение при выполнении play.py: {exc}")
        return False


# Пример использования:
if __name__ == "__main__":
    success = execute_manipulator_trajectory("arab2.json")
    if success:
        print("Программа робота успешно завершена.")
    else:
        print("Воспроизведение программы завершилось с ошибкой.")