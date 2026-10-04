import threading
import time
import numpy as np
from py3dcnx import SpaceMouse


class SpaceMouseWrapper:
    """Non-blocking 6DOF SpaceMouse controller that integrates input into pose values

    SpaceMouse acts as velocity command:
      Translation:
        - Push forward (y negative)  → X_meter increases
        - Push left (x negative)     → Y_meter increases
        - Push up (z negative)       → Z_meter increases
      Rotation:
        - Tilt forward (roll negative)  → Pitch_radian increases
        - Tilt left (pitch negative)    → Roll_radian increases
        - Twist left (yaw negative)     → Yaw_radian increases
    """

    RAW_MAX = 350.0

    def __init__(self, max_speed=0.05, max_rot_speed=0.1, deadzone=200.0,
                 alpha=0.3, poll_rate=100, device_num=0,
                 x_init=0.0, y_init=0.0, z_init=0.0,
                 roll_init=0.0, pitch_init=0.0, yaw_init=0.0):
        """
        Args:
            max_speed: Max position change per second (meters/sec).
            max_rot_speed: Max orientation change per second (radians/sec).
            deadzone: Ignore raw values with abs below this threshold.
            alpha: Exponential smoothing factor (0 < alpha <= 1). Lower = smoother.
            poll_rate: Internal integration rate in Hz.
            device_num: SpaceMouse device index.
            x/y/z_init: Initial position offsets (meters).
            roll/pitch/yaw_init: Initial orientation offsets (radians).
        """
        self.max_speed = max_speed
        self.max_rot_speed = max_rot_speed
        self.deadzone = deadzone
        self.active_range = self.RAW_MAX - deadzone
        self.alpha = alpha
        self.poll_rate = poll_rate
        self.dt = 1.0 / poll_rate

        # Position accumulators
        self.x_meter = x_init
        self.y_meter = y_init
        self.z_meter = z_init

        # Orientation accumulators
        self.roll_radian = roll_init
        self.pitch_radian = pitch_init
        self.yaw_radian = yaw_init

        self.dx = 0
        self.dy = 0
        self.dz = 0
        self.droll = 0
        self.dpitch = 0
        self.dyaw = 0

        # Smoothed values (normalized -1 to 1)
        self._smooth_tx = 0.0
        self._smooth_ty = 0.0
        self._smooth_tz = 0.0
        self._smooth_rx = 0.0
        self._smooth_ry = 0.0
        self._smooth_rz = 0.0

        # Latest raw values from SpaceMouse events
        self._raw_translate = [0, 0, 0]  # x, y, z
        self._raw_rotate = [0, 0, 0]     # roll, pitch, yaw
        self._raw_lock = threading.Lock()

        # Button state: 1.0 = open (default), -1.0 = closed
        self._gripper_state = 1.0
        self._button_lock = threading.Lock()

        self._lock = threading.Lock()
        self._running = False
        self._thread = None

        # Set up SpaceMouse
        self._sm = SpaceMouse(num=device_num)
        print("SpaceMouse devices found:", SpaceMouse.get_devices())
        self._sm.register_handler(self._on_translate, "translate")
        self._sm.register_handler(self._on_rotate, "rotate")
        self._sm.register_handler(self._on_button, "button")

        self.start()

    def _apply_deadzone(self, value):
        if abs(value) < self.deadzone:
            return 0.0
        sign = 1.0 if value > 0 else -1.0
        return sign * (abs(value) - self.deadzone) / self.active_range

    def _on_translate(self, event):
        with self._raw_lock:
            self._raw_translate = [event['x'], event['y'], event['z']]

    def _on_rotate(self, event):
        with self._raw_lock:
            self._raw_rotate = [event['roll'], event['pitch'], event['yaw']]

    def _on_button(self, event):
        # Toggle gripper on any button press
        pressed = event.get('val', [])
        if pressed:
            with self._button_lock:
                self._gripper_state = -self._gripper_state

    def _integrate_loop(self):
        while self._running:
            with self._raw_lock:
                tx, ty, tz = self._raw_translate
                rroll, rpitch, ryaw = self._raw_rotate

            # Apply deadzone and normalize to [-1, 1]
            nx = self._apply_deadzone(tx)
            ny = self._apply_deadzone(ty)
            nz = self._apply_deadzone(tz)
            nroll = self._apply_deadzone(rroll)
            npitch = self._apply_deadzone(rpitch)
            nyaw = self._apply_deadzone(ryaw)

            # Exponential smoothing
            self._smooth_tx = self.alpha * nx + (1 - self.alpha) * self._smooth_tx
            self._smooth_ty = self.alpha * ny + (1 - self.alpha) * self._smooth_ty
            self._smooth_tz = self.alpha * nz + (1 - self.alpha) * self._smooth_tz
            self._smooth_rx = self.alpha * nroll + (1 - self.alpha) * self._smooth_rx
            self._smooth_ry = self.alpha * npitch + (1 - self.alpha) * self._smooth_ry
            self._smooth_rz = self.alpha * nyaw + (1 - self.alpha) * self._smooth_rz

            # Integrate velocity into position (with axis remapping and negation)
            # Translation: -y → +X, -x → +Y, -z → +Z
            dx = -self._smooth_ty * self.max_speed * self.dt
            dy = -self._smooth_tx * self.max_speed * self.dt
            dz = -self._smooth_tz * self.max_speed * self.dt

            # Rotation: -roll → +Pitch, -pitch → +Roll, -yaw → +Yaw
            droll = -self._smooth_ry * self.max_rot_speed * self.dt
            dpitch = -self._smooth_rx * self.max_rot_speed * self.dt
            dyaw = -self._smooth_rz * self.max_rot_speed * self.dt

            with self._lock:
                self.x_meter += dx
                self.y_meter += dy
                self.z_meter += dz
                self.roll_radian += droll
                self.pitch_radian += dpitch
                self.yaw_radian += dyaw

                self.dx = dx
                self.dy = dy
                self.dz = dz
                self.droll = droll
                self.dpitch = dpitch
                self.dyaw = dyaw

            time.sleep(self.dt)

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._integrate_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join()
        self._sm.shutdown()

    def get_pose(self):
        """Returns (X_meter, Y_meter, Z_meter, Roll_radian, Pitch_radian, Yaw_radian)"""
        with self._lock:
            return (self.x_meter, self.y_meter, self.z_meter,
                    self.roll_radian, self.pitch_radian, self.yaw_radian)
        
    def get_delta(self):
        """Returns (dX_meter, dY_meter, dZ_meter, dRoll_radian, dPitch_radian, dYaw_radian)"""
        with self._lock:
            return (self.dx, self.dy, self.dz,
                    self.droll, self.dpitch, self.dyaw)

    def get_gripper_state(self):
        """Returns 1.0 (open) or -1.0 (closed). Toggled by SpaceMouse button press."""
        with self._button_lock:
            return self._gripper_state

    def get_velocity(self):
        """Returns smoothed velocities in robot frame (vx, vy, vz, vyaw), normalized -1.0 to 1.0.

        Applies the same axis remapping as the integration loop:
        -smooth_ty → +X, -smooth_tx → +Y, -smooth_tz → +Z, -smooth_rz → +Yaw
        """
        return (-self._smooth_ty, -self._smooth_tx, -self._smooth_tz, -self._smooth_rz)

    def reset(self):
        with self._lock:
            self.x_meter = 0.0
            self.y_meter = 0.0
            self.z_meter = 0.0
            self.roll_radian = 0.0
            self.pitch_radian = 0.0
            self.yaw_radian = 0.0


if __name__ == "__main__":
    sm = SpaceMouseWrapper(
        max_speed=0.05, max_rot_speed=0.1,
        x_init=0.5, y_init=0.5, z_init=0.5,
        roll_init=np.pi, pitch_init=0.0, yaw_init=0.0
        )
    try:
        while True:
            x, y, z, roll, pitch, yaw = sm.get_pose()
            print(f"X: {x:+.4f}m  Y: {y:+.4f}m  Z: {z:+.4f}m  "
                  f"R: {roll:+.4f}rad  P: {pitch:+.4f}rad  Y: {yaw:+.4f}rad",
                  end="\r")
            time.sleep(0.05)
    except KeyboardInterrupt:
        print()
        sm.stop()
