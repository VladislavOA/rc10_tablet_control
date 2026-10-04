# RC10 Tablet Control

Minimal project for the RC10 tablet interface.

Flow:
1. Choose a trajectory from `data/trajectories/*.json`.
2. Press the capture button.
3. A 5-second countdown is shown.
4. Recording starts and `execute_manipulator_trajectory(json_name)` is called.
5. If the stub returns `True`, recording is finalized and uploaded to Yandex Disk.
6. Only the current session can display its QR code, which prevents an old QR from appearing immediately after a new press.

## Run

```bash
cp .env.example .env
# put YANDEX_DISK_TOKEN into .env
./run.sh
```

Open `http://<laptop-ip>:8070` on the iPad.

## Manipulator integration

Replace only the body of:

```python
app/services/manipulator.py
execute_manipulator_trajectory(trajectory_json_name: str) -> bool
```

Keep the signature. Return `True` only when the selected trajectory has completed successfully; return `False` on failure.
