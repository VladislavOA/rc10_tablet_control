from __future__ import annotations

import math
import json
import os
import shutil
import subprocess
from pathlib import Path


def load_speed_intervals(trajectory_path: Path) -> list[dict[str, float]]:
    """Load and validate source-time video speed intervals from a trajectory JSON."""
    try:
        data = json.loads(trajectory_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Не удалось прочитать JSON траектории: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("Корневое значение JSON траектории должно быть объектом")

    intervals = data.get("video_speed_intervals", [])
    if not isinstance(intervals, list):
        raise ValueError("video_speed_intervals должен быть списком")
    _normalize_intervals(intervals)
    return intervals


def _normalize_intervals(
    intervals: list[dict[str, float]],
) -> list[tuple[float, float, float, float]]:
    normalized = []
    for interval in intervals:
        if not isinstance(interval, dict):
            raise ValueError("Каждый интервал должен быть объектом настроек скорости")
        try:
            start = float(interval["start"])
            end = float(interval["end"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("Каждый интервал должен содержать числовые start и end") from exc

        has_constant_speed = "speed" in interval
        has_ramp_start = "start_speed" in interval
        has_ramp_end = "end_speed" in interval
        if has_constant_speed and not has_ramp_start and not has_ramp_end:
            try:
                start_speed = end_speed = float(interval["speed"])
            except (TypeError, ValueError) as exc:
                raise ValueError("speed должен быть числом") from exc
        elif not has_constant_speed and has_ramp_start and has_ramp_end:
            try:
                start_speed = float(interval["start_speed"])
                end_speed = float(interval["end_speed"])
            except (TypeError, ValueError) as exc:
                raise ValueError("start_speed и end_speed должны быть числами") from exc
        else:
            raise ValueError(
                "Укажите либо speed, либо оба поля start_speed и end_speed"
            )

        if not all(math.isfinite(value) for value in (start, end, start_speed, end_speed)):
            raise ValueError("Времена и скорость должны быть конечными числами")
        if start < 0 or end <= start:
            raise ValueError("Каждый интервал должен иметь начало >= 0 и конец позже начала")
        if not all(0.5 <= speed <= 2.0 for speed in (start_speed, end_speed)):
            raise ValueError("Скорость должна быть от 0.5x до 2x")
        normalized.append((start, end, start_speed, end_speed))

    normalized.sort(key=lambda interval: interval[0])
    for previous, current in zip(normalized, normalized[1:]):
        if current[0] < previous[1]:
            raise ValueError("Интервалы изменения скорости не должны пересекаться")
    return normalized


def _video_duration(path: Path, ffprobe: str) -> float:
    result = subprocess.run(
        [
            ffprobe,
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe не смог прочитать видео: {result.stderr.strip()}")
    try:
        duration = float(result.stdout.strip())
    except ValueError as exc:
        raise RuntimeError("Не удалось определить длительность видео") from exc
    if not math.isfinite(duration) or duration <= 0:
        raise RuntimeError("У видео некорректная длительность")
    return duration


def _build_segments(
    duration: float,
    intervals: list[dict[str, float]],
) -> list[tuple[float, float, float, float]]:
    normalized = _normalize_intervals(intervals)
    segments = []
    cursor = 0.0
    for original_start, original_end, original_start_speed, original_end_speed in normalized:
        start = min(original_start, duration)
        end = min(original_end, duration)
        if start >= duration:
            break
        if start > cursor:
            segments.append((cursor, start, 1.0, 1.0))
        if end > start:
            clipped_start_speed = original_start_speed + (
                original_end_speed - original_start_speed
            ) * (start - original_start) / (original_end - original_start)
            clipped_end_speed = original_start_speed + (
                original_end_speed - original_start_speed
            ) * (end - original_start) / (original_end - original_start)
            segments.append((start, end, clipped_start_speed, clipped_end_speed))
            cursor = end
    if cursor < duration:
        segments.append((cursor, duration, 1.0, 1.0))
    return segments


def _build_filter(segments: list[tuple[float, float, float, float]]) -> str:
    split_outputs = "".join(f"[src{index}]" for index in range(len(segments)))
    filters = [f"[0:v]split={len(segments)}{split_outputs}"]
    for index, (start, end, start_speed, end_speed) in enumerate(segments):
        if math.isclose(start_speed, end_speed, rel_tol=1e-9, abs_tol=1e-9):
            setpts = f"(PTS-STARTPTS)/{start_speed:.9f}"
        else:
            segment_duration = end - start
            speed_delta = end_speed - start_speed
            setpts = (
                f"({segment_duration:.9f}/{speed_delta:.9f}*"
                f"log(({start_speed:.9f}+{speed_delta:.9f}*"
                f"(PTS-STARTPTS)*TB/{segment_duration:.9f})/{start_speed:.9f})/TB)"
            )
        filters.append(
            f"[src{index}]trim=start={start:.6f}:end={end:.6f},"
            f"setpts={setpts}[part{index}]"
        )
    parts = "".join(f"[part{index}]" for index in range(len(segments)))
    filters.append(f"{parts}concat=n={len(segments)}:v=1:a=0[outv]")
    return ";".join(filters)


def apply_speed_intervals(video_path: Path, intervals: list[dict[str, float]]) -> None:
    """Retiming source-time intervals in-place, leaving the original intact on failure."""
    if not intervals:
        return

    ffmpeg = shutil.which("ffmpeg")
    ffprobe = shutil.which("ffprobe")
    if not ffmpeg or not ffprobe:
        raise RuntimeError("Для изменения скорости видео необходимы ffmpeg и ffprobe")

    duration = _video_duration(video_path, ffprobe)
    segments = _build_segments(duration, intervals)
    if not any(
        not (math.isclose(start_speed, 1.0) and math.isclose(end_speed, 1.0))
        for _, _, start_speed, end_speed in segments
    ):
        return

    output_path = video_path.with_name(f".{video_path.stem}.retimed.mp4")
    output_path.unlink(missing_ok=True)
    command = [
        ffmpeg,
        "-y", "-loglevel", "error",
        "-i", str(video_path),
        "-filter_complex", _build_filter(segments),
        "-map", "[outv]",
        "-an",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "22",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        str(output_path),
    ]
    try:
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg не смог изменить скорость видео: {result.stderr.strip()}")
        if not output_path.is_file() or output_path.stat().st_size < 1024:
            raise RuntimeError("После обработки получилось пустое или повреждённое видео")
        os.replace(output_path, video_path)
    finally:
        output_path.unlink(missing_ok=True)