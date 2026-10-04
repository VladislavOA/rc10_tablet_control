import pygame
import time
import threading
import numpy as np
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(threadName)-10s | %(levelname)-8s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)
class PS4Joystick:
    """Non-blocking PS4 joystick controller that integrates stick input into position values"""

    def __init__(self, max_speed=0.05, max_rot_speed=0.1, deadzone=0.05, alpha=0.3, poll_rate=100,
                 x_init=0.0, y_init=0.0, z_init=0.0, roll_init=np.pi, pitch_init=0.0, yaw_init=0.0):
        self.max_speed = max_speed
        self.max_speed_init = max_speed
        self.max_rot_speed = max_rot_speed
        self.deadzone = deadzone
        self.alpha = alpha
        self.poll_rate = poll_rate
        self.dt = 1.0 / poll_rate

        self.z_low_limit = 0.0

        # Position accumulators
        self.x_meter = x_init
        self.y_meter = y_init
        self.z_meter = z_init

        # Orientation accumulator
        self.roll_radian = roll_init
        self.pitch_radian = pitch_init
        self.yaw_radian = yaw_init

        self.x_init = x_init
        self.y_init = y_init
        self.z_init = z_init
        self.roll_init = roll_init
        self.pitch_init = pitch_init
        self.yaw_init = yaw_init

        self.dx = 0.0
        self.dy = 0.0
        self.dz = 0.0
        self.droll = 0.0
        self.dpitch = 0.0
        self.dyaw = 0.0


        # Smoothed joystick values
        self._smoothed_x = 0.0
        self._smoothed_y = 0.0
        self._smoothed_z = 0.0
        self._smoothed_roll = 0.0
        self._smoothed_pitch = 0.0
        self._smoothed_yaw = 0.0


        # Button state: 1.0 = open (default), -1.0 = closed
        self._gripper_state = 1.0
        self._prev_button_state = False


        # HIL-SERL button states while recording dataset
        self._intervention = False  # R1 button - level triggered - hold for intervention
        self._success = False   # Traingle button 3 - edge triggered
        self._terminate = False # Circle button 1 - edge trigger
        self._rerecord = False  # Square button 2 - edge trigger

        self._prev_success = False
        self._prev_terminate = False
        self._prev_rerecord = False


        self._lock = threading.Lock()
        self._running = False
        self._thread = None

        # Initialize pygame and joystick
        pygame.init()
        pygame.joystick.init()
        if pygame.joystick.get_count() == 0:
            logger.error("Failed to find a connected controller")
            raise RuntimeError("No controller found")
        self._controller = pygame.joystick.Joystick(0)
        self._controller.init()
        self.start()
        logger.info(f"Connected: {self._controller.get_name()}")

    def _apply_deadzone(self, value):
        if abs(value) < self.deadzone:
            return 0.0
        return (value - (self.deadzone if value > 0 else -self.deadzone)) / (1 - self.deadzone)

    def _poll_loop(self):
        while self._running:
            pygame.event.pump()
            # for event in pygame.event.get():
            #     if event.type == pygame.JOYBUTTONDOWN: # rising edge
            #         # print(event.button)
            #         if event.button == 0:   
            #             # 0 is x button on ps4 joystick
            #             # check which button has what index by printing event.button 
            #             # or check docs: https://www.pygame.org/docs/ref/joystick.html#playstation-4-controller-pygame-2-x
            #             self._toggle_gripper_state()

            #         if event.button == 4: # L1 button
            #             self._adjust_max_speed(-0.01)

            #         if event.button == 5: # R1 button
            #             self._adjust_max_speed(0.01)

            raw_x = self._controller.get_axis(0)  # Left stick horizontal
            raw_y = self._controller.get_axis(1)  # Left stick vertical
            raw_z = self._controller.get_axis(4)  # Right stick vertical

            if self._controller.get_button(4):  # L1 button 0
                with self._lock:
                    self.max_speed = 0.01
            else:
                with self._lock:
                    self.max_speed = self.max_speed_init

            current_intervention = self._controller.get_button(5)   # R1 button
            current_success = self._controller.get_button(2)    # Triangle button
            current_terminate = self._controller.get_button(1)  # Circle button
            current_rerecord = self._controller.get_button(3)   # Square button
            current_button_state = self._controller.get_button(0)   # X/cross button

            with self._lock:
                self._intervention = current_intervention
                if current_success and not self._prev_success:
                    self._success = True
                if current_terminate and not self._prev_terminate:
                    self._terminate = True
                if current_rerecord and not self._prev_rerecord:
                    self._rerecord = True
                # toggle gripper state only on rising edge when it changes from false to true
                if current_button_state and not self._prev_button_state: # cross/x button
                    self._gripper_state = -self._gripper_state

            self._prev_success = current_success
            self._prev_terminate = current_terminate
            self._prev_rerecord = current_rerecord
            self._prev_button_state = current_button_state


            # TODO: add roll and pitch maping to joystick later, not needed right now
            raw_roll = 0.0 # Set this later
            raw_pitch = 0.0 # Set this later 
            raw_yaw = self._controller.get_axis(3)  # Right stick horizontal

            dead_x = self._apply_deadzone(raw_x)
            dead_y = self._apply_deadzone(raw_y)
            dead_z = self._apply_deadzone(raw_z)
            dead_roll = self._apply_deadzone(raw_roll)
            dead_pitch = self._apply_deadzone(raw_pitch)

            dead_yaw = self._apply_deadzone(raw_yaw)

            self._smoothed_x = (self.alpha * dead_x) + ((1 - self.alpha) * self._smoothed_x)
            self._smoothed_y = (self.alpha * dead_y) + ((1 - self.alpha) * self._smoothed_y)
            self._smoothed_z = (self.alpha * dead_z) + ((1 - self.alpha) * self._smoothed_z)

            self._smoothed_roll = (self.alpha * dead_roll) + ((1 - self.alpha) * self._smoothed_roll)
            self._smoothed_pitch = (self.alpha * dead_pitch) + ((1 - self.alpha) * self._smoothed_pitch)
            self._smoothed_yaw = (self.alpha * dead_yaw) + ((1 - self.alpha) * self._smoothed_yaw)

            # Integrate: joystick value is velocity, accumulate into position
            # UP (negative smoothed_y) → increase X_meter, so negate
            # LEFT (negative smoothed_x) → increase Y_meter, so negate
            # Right stick UP (negative smoothed_z) → increase Z_meter, so negate
            dx = self._smoothed_x * self.max_speed * self.dt
            dy = -self._smoothed_y * self.max_speed * self.dt
            dz = -self._smoothed_z * self.max_speed * self.dt

            # Rotation:
            droll = -self._smoothed_roll * self.max_rot_speed * self.dt
            dpitch = -self._smoothed_pitch * self.max_rot_speed * self.dt
            dyaw = -self._smoothed_yaw * self.max_rot_speed * self.dt

            with self._lock:
                self.x_meter += dx
                self.y_meter += dy
                if self.z_meter + dz >= self.z_low_limit:
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
        """Start the background polling thread"""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()

    def stop(self):
        """Stop the background polling thread"""
        self._running = False
        if self._thread:
            self._thread.join()
        pygame.quit()

    def get_joystick(self):
        """Returns (X_meter, Y_meter, Z_meter) - current accumulated position"""
        with self._lock:
            return self.x_meter, self.y_meter, self.z_meter, self.roll_radian, self.pitch_radian, self.yaw_radian
        
    def get_delta_velocities(self):
        """Returns (dvx, dvy, dvz, dvroll, dvpitch, dvyaw) - current velocities"""
        with self._lock:
            return self._smoothed_x, -self._smoothed_y, -self._smoothed_z, self._smoothed_roll, self._smoothed_pitch, -self._smoothed_yaw

    def get_normalized_deltas(self):
        """Returns smoothed stick delections in [-1, 1] for x, y, z, and yaw"""
        with self._lock:
            return self._smoothed_x, -self._smoothed_y, -self._smoothed_z, -self._smoothed_yaw

    def get_button_states(self):
        """Returns HIL-SERL episode control button states and clears edge trigger flags"""
        with self._lock:
            states = {
                "is_intervention": self._intervention,
                "success": self._success,
                "terminate_episode": self._terminate,
                "rerecord_episode": self._rerecord,
            }
            self._success = False
            self._terminate = False
            self._rerecord = False
            return states

    def get_gripper_state(self):
        """Returns 1.0 (open) or -1.0 (closed). Toggled by PS4 button x press."""
        with self._lock:
            return self._gripper_state
        
    def _toggle_gripper_state(self):
        """Toggle the gripper state"""
        with self._lock:
            self._gripper_state = -self._gripper_state

    def _adjust_max_speed(self, delta_speed):
        with self._lock:
            new_speed = self.max_speed + delta_speed
            self.max_speed = max(0.01, min(0.2, new_speed))
            logger.info(f"Max translation speed adjusted to: {self.max_speed:.2f}")

    def reset(self):
        """Reset position to origin"""
        with self._lock:
            self.x_meter = self.x_init
            self.y_meter = self.y_init
            self.z_meter = self.z_init
            self.roll_radian = self.roll_init
            self.pitch_radian = self.pitch_init
            self.yaw_radian = self.yaw_init  

if __name__ == "__main__":
    joy = PS4Joystick(max_speed=0.05)
    try:
        while True:
            x, y, z, roll, pitch, yaw = joy.get_joystick()
            dvx, dvy, dvz, dvroll, dvpitch, dvyaw = joy.get_delta_velocities()
            print(f"X_meter: {x:.4f}, Y_meter: {y:.4f}, Z_meter: {z:.4f} "
                  f"yaw_radian: {yaw: 4f}, gripper_state: {joy.get_gripper_state()} "
                  f"vx: {dvx:.4f}, vy: {dvy:.4f}, vz: {dvz:.4f}, vyaw: {dvyaw:.4f} ",
                  end="\r", flush=True)
            time.sleep(0.05)
    except KeyboardInterrupt:
        joy.stop()
