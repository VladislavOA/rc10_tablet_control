# RC10 Tablet Control

Minimal project for the RC10 tablet interface.

Flow:
1. Choose a trajectory from `data/trajectories/*.json`.
2. Press the capture button to prepare the manipulator and validate the path.
3. Once the robot signals that it is ready to move, a 5-second countdown is shown.
4. Recording starts immediately before the first motion command is released.
5. If the stub returns `True`, recording is finalized and uploaded to Yandex Disk.
6. Only the current session can display its QR code, which prevents an old QR from appearing immediately after a new press.

## Run

```bash
cp .env.example .env
# put YANDEX_DISK_TOKEN into .env
./run.sh
```

Open `http://<laptop-ip>:8070` on the iPad.

## Video speed per trajectory

Set optional `video_speed_intervals` in each file under `data/trajectories/`.
Times are seconds from the start of the camera recording; areas outside the
listed intervals keep normal speed. Intervals must not overlap. Use `speed` for
a constant speed, or `start_speed` and `end_speed` for a linear speed ramp:

```json
"video_speed_intervals": [
  {"start": 1.5, "end": 4.0, "speed": 0.5},
  {"start": 7.0, "end": 9.0, "start_speed": 0.5, "end_speed": 2.0}
]
```

All speed values must be between `0.5` and `2.0`. In the ramp example, speed
changes linearly from `0.5x` at 7 seconds to `2.0x` at 9 seconds. A JSON test
fixture is available at `tests/fixtures/video_speed_ramp.json`; it contains a
wait-only program and is not included in the app's selectable trajectories.
An omitted field or an empty list leaves the video unchanged. Processing uses
`ffmpeg` and `ffprobe` before the video is uploaded.

## Manipulator integration

Replace only the body of:

```python
app/services/manipulator.py
execute_manipulator_trajectory(trajectory_json_name: str) -> bool
```

Keep the signature. Return `True` only when the selected trajectory has completed successfully; return `False` on failure.
