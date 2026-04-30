"""Robot state module for EdPy Robot Simulator.

Tracks robot position, heading, motor states, and sensor values with accurate
clear-on-read behavior matching the real Edison robot.
"""

import math
import threading
import time
from typing import Optional, Tuple
from .environment import Environment


class RobotState:
    """Manages the complete state of the simulated Edison robot.

    This includes position, heading, motor states, sensor values, and all
    the low-level register simulation needed for accurate EdPy behavior.
    """

    # Sensor positions relative to robot center (in pixels)
    IR_SENSOR_OFFSET = (15, 0)  # Front center
    LINE_TRACKER_OFFSET = (12, 0)  # Slightly behind IR
    LEFT_LED_OFFSET = (-8, -12)
    RIGHT_LED_OFFSET = (-8, 12)

    def __init__(self, environment: Environment, x: float = 400, y: float = 300):
        self.env = environment
        self.lock = threading.Lock()

        # Position and heading
        self.x = x
        self.y = y
        self.heading = 0  # 0 degrees = facing right (positive X)

        # Motor state
        self.left_motor_control = 0xC0  # STOP by default
        self.right_motor_control = 0xC0  # STOP by default
        self.left_motor_distance = 0
        self.right_motor_distance = 0
        self.left_motor_strain = False
        self.right_motor_strain = False

        # LED state
        self.left_led = 0
        self.right_led = 0

        # IR state
        self.ir_tx_action = 0
        self.ir_tx_char = 0
        self.ir_rx_status = 0
        self.ir_rx_char = 0
        self.obstacle_detection_enabled = False

        # Line tracker state
        self.line_tracker_status = 0
        self.line_tracker_power = 0
        self._last_line_state = 0

        # Beeper state
        self.beep_status = 0
        self.beep_action = 0
        self.beep_freq = 0
        self.beep_duration = 0
        self.beep_tempo = 250  # TEMPO_MEDIUM
        self._clap_pending = False
        self._tune_finished = False
        self._tone_finished = False

        # Timer state
        self.timer_status = 0
        self.timer_action = 0
        self.timer_pause = 0
        self.timer_one_shot = 0
        self._countdown_start = 0
        self._countdown_duration = 0
        self._pause_until = 0

        # Device state
        self.dev_random = 0
        self.dev_button = 0

        # Settings
        self.edison_version = 2  # Ed.V2
        self.distance_units = 0  # Ed.CM
        self.tempo = 250  # Ed.TEMPO_MEDIUM

        # Simulation timing
        self._running = False
        self._update_thread: Optional[threading.Thread] = None
        self._update_interval = 0.02  # 50 Hz update rate

    def start(self) -> None:
        """Start the physics update loop."""
        with self.lock:
            if not self._running:
                self._running = True
                self._update_thread = threading.Thread(target=self._update_loop, daemon=True)
                self._update_thread.start()

    def stop(self) -> None:
        """Stop the physics update loop."""
        with self.lock:
            self._running = False
        if self._update_thread:
            self._update_thread.join(timeout=0.5)

    def reset(self, x: float = 400, y: float = 300, heading: float = 0) -> None:
        """Reset robot to initial state."""
        with self.lock:
            self.x = x
            self.y = y
            self.heading = heading
            self.left_motor_control = 0xC0
            self.right_motor_control = 0xC0
            self.left_motor_distance = 0
            self.right_motor_distance = 0
            self.ir_rx_status = 0
            self.obstacle_detection_enabled = False
            self.line_tracker_status = 0
            self.beep_status = 0
            self.dev_button = 0
            self._clap_pending = False

    def _update_loop(self) -> None:
        """Main physics update loop."""
        while True:
            with self.lock:
                if not self._running:
                    break
                self._update_physics()
                self._update_sensors()
                self._update_timers()
            time.sleep(self._update_interval)

    def _update_physics(self) -> None:
        """Update robot position based on motor states."""
        # Decode motor controls
        left_speed, left_dir = self._decode_motor_control(self.left_motor_control)
        right_speed, right_dir = self._decode_motor_control(self.right_motor_control)

        if left_speed == 0 and right_speed == 0:
            return

        # Calculate movement (simplified differential drive)
        # Speed 0 = full (10 px/update), Speed 10 = slow (1 px/update)
        left_vel = (11 - left_speed) * 2 * left_dir if left_speed > 0 else 0
        right_vel = (11 - right_speed) * 2 * right_dir if right_speed > 0 else 0

        # Update distance counters
        if left_vel != 0:
            self.left_motor_distance += abs(int(left_vel))
        if right_vel != 0:
            self.right_motor_distance += abs(int(right_vel))

        # Calculate new position
        if left_dir == right_dir:  # Forward or backward
            speed = (left_vel + right_vel) / 2
            rad = math.radians(self.heading)
            new_x = self.x + speed * math.cos(rad)
            new_y = self.y + speed * math.sin(rad)
        elif left_dir == -right_dir:  # Spin in place
            turn_rate = (right_vel - left_vel) / 20  # Degrees per update
            self.heading = (self.heading + turn_rate) % 360
            new_x, new_y = self.x, self.y
        else:  # Arc turn
            speed = (left_vel + right_vel) / 2
            turn_factor = (right_vel - left_vel) / 50
            self.heading = (self.heading + turn_factor) % 360
            rad = math.radians(self.heading)
            new_x = self.x + speed * math.cos(rad)
            new_y = self.y + speed * math.sin(rad)

        # Collision detection
        if not self.env.check_collision(new_x, new_y):
            self.x = new_x
            self.y = new_y
        else:
            # Collision - mark motors as strained
            self.left_motor_strain = left_vel != 0
            self.right_motor_strain = right_vel != 0

        # Keep within bounds
        self.x = max(20, min(self.env.width - 20, self.x))
        self.y = max(20, min(self.env.height - 20, self.y))

    def _decode_motor_control(self, control: int) -> Tuple[int, int]:
        """Decode motor control byte into speed and direction.

        Returns: (speed, direction) where direction is -1, 0, or 1
        """
        if control & 0xC0 == 0xC0:  # STOP
            return 0, 0

        speed = control & 0x0F
        if control & 0x80:  # Forward
            return speed, 1
        elif control & 0x40:  # Backward
            return speed, -1
        else:
            return 0, 0

    def _update_sensors(self) -> None:
        """Update sensor readings based on environment."""
        # Get sensor positions in world coordinates
        ir_x, ir_y = self._get_sensor_world_pos(self.IR_SENSOR_OFFSET)
        line_x, line_y = self._get_sensor_world_pos(self.LINE_TRACKER_OFFSET)

        # Update line tracker status
        on_line = self.env.check_line_position(line_x, line_y)
        new_line_state = 1 if on_line else 0

        # Check for line change
        if new_line_state != self._last_line_state:
            self.line_tracker_status |= 0x02  # Set change bit
            self._last_line_state = new_line_state

        # Set line state bit
        if on_line:
            self.line_tracker_status |= 0x01
        else:
            self.line_tracker_status &= ~0x01

        # Update obstacle detection (only if beam is enabled)
        if self.obstacle_detection_enabled:
            self._update_obstacle_detection(ir_x, ir_y)

        # Update clap detection
        if self._clap_pending:
            self.beep_status |= 0x04  # Set clap detected bit
            self._clap_pending = False

        # Update music finished status
        if self._tune_finished:
            self.beep_status |= 0x01
            self._tune_finished = False
        if self._tone_finished:
            self.beep_status |= 0x02
            self._tone_finished = False

    def _update_obstacle_detection(self, x: float, y: float) -> None:
        """Update obstacle detection based on IR sensor reading."""
        # Cast rays at different angles for left, center, right detection
        # Center (ahead): 0 degrees relative to heading
        # Left: -15 degrees, Right: +15 degrees
        detection = 0

        for offset, bit in [(0, 0x10), (-15, 0x20), (15, 0x08)]:  # AHEAD, LEFT, RIGHT
            obs, dist = self.env.ray_cast(x, y, self.heading + offset, max_distance=100)
            if obs and dist < 100:
                detection |= bit

        if detection:
            self.ir_rx_status |= 0x40  # OBSTACLE_DETECTED bit
            self.ir_rx_status |= detection

    def _update_timers(self) -> None:
        """Update countdown timers."""
        now = time.time()

        # Update one-shot countdown
        if self._countdown_duration > 0:
            elapsed = int((now - self._countdown_start) * 100)  # hundredths of seconds
            remaining = max(0, self._countdown_duration - elapsed)
            self.timer_one_shot = remaining
            if remaining == 0:
                self.timer_status |= 0x01  # Timer finished
        else:
            self.timer_one_shot = 0

    def _get_sensor_world_pos(self, offset: Tuple[float, float]) -> Tuple[float, float]:
        """Convert sensor offset to world coordinates based on robot heading."""
        rad = math.radians(self.heading)
        cos_h = math.cos(rad)
        sin_h = math.sin(rad)

        # Rotate offset by heading
        rot_x = offset[0] * cos_h - offset[1] * sin_h
        rot_y = offset[0] * sin_h + offset[1] * cos_h

        return self.x + rot_x, self.y + rot_y

    # Motor control methods
    def set_left_motor(self, control: int) -> None:
        """Set left motor control byte."""
        with self.lock:
            self.left_motor_control = control & 0xFF

    def set_right_motor(self, control: int) -> None:
        """Set right motor control byte."""
        with self.lock:
            self.right_motor_control = control & 0xFF

    def reset_distance(self) -> None:
        """Reset both motor distance counters."""
        with self.lock:
            self.left_motor_distance = 0
            self.right_motor_distance = 0

    def get_distance(self, which: int) -> int:
        """Get distance for specified motor in current units."""
        with self.lock:
            if which == 0:  # MOTOR_LEFT
                ticks = self.left_motor_distance
            else:
                ticks = self.right_motor_distance

            # Convert based on distance units
            if self.distance_units == 0:  # CM
                return ticks // 8
            elif self.distance_units == 1:  # INCH
                return ticks // 20
            else:  # TIME (raw ticks)
                return ticks

    # LED methods
    def set_left_led(self, value: int) -> None:
        """Set left LED state (0 or 1)."""
        with self.lock:
            self.left_led = value & 0x01

    def set_right_led(self, value: int) -> None:
        """Set right LED state (0 or 1)."""
        with self.lock:
            self.right_led = value & 0x01

    # Obstacle detection methods
    def set_obstacle_detection(self, enabled: bool) -> None:
        """Enable/disable obstacle detection beam."""
        with self.lock:
            self.obstacle_detection_enabled = enabled

    def read_obstacle_detection(self) -> int:
        """Read obstacle detection with clear-on-read behavior.

        Returns: OBSTACLE_NONE, OBSTACLE_LEFT, OBSTACLE_AHEAD, or OBSTACLE_RIGHT
        Returns exactly one direction constant for compatibility with == comparisons.
        Priority: AHEAD > LEFT > RIGHT
        """
        with self.lock:
            status = self.ir_rx_status

            if not (status & 0x40):  # OBSTACLE_DETECTED bit
                return 0  # OBSTACLE_NONE

            # Determine which direction - return exactly ONE for == comparisons
            # Priority: AHEAD > LEFT > RIGHT
            if status & 0x10:  # OBSTACLE_AHEAD
                data = 0x10
            elif status & 0x20:  # OBSTACLE_LEFT
                data = 0x20
            elif status & 0x08:  # OBSTACLE_RIGHT
                data = 0x08
            else:
                data = 0  # Should not happen if OBSTACLE_DETECTED is set

            return data

    def clear_obstacle_detection(self) -> None:
        """Clear obstacle detection bits.

        Called separately to match Edison's behavior where multiple reads
        return the same value until explicitly cleared.
        """
        with self.lock:
            # Clear obstacle detected bit and all direction bits
            self.ir_rx_status &= ~0x78

    # Line tracker methods
    def set_line_tracker_led(self, value: int) -> None:
        """Set line tracker LED power."""
        with self.lock:
            self.line_tracker_power = value & 0x01

    def read_line_state(self) -> int:
        """Read current line state (0=white, 1=black)."""
        with self.lock:
            return self.line_tracker_status & 0x01

    def read_line_change(self) -> int:
        """Read line change with clear-on-read behavior."""
        with self.lock:
            change = self.line_tracker_status & 0x02
            if change:
                self.line_tracker_status &= ~0x02  # Clear change bit
                return 1
            return 0

    # Keypad methods
    def press_button(self, button: int) -> None:
        """Simulate a button press (KEYPAD_TRIANGLE or KEYPAD_ROUND)."""
        with self.lock:
            self.dev_button = button & 0x0F

    def read_keypad(self) -> int:
        """Read keypad with clear-on-read behavior."""
        with self.lock:
            value = self.dev_button & 0x0F
            self.dev_button = 0  # Clear after reading
            return value

    # Clap sensor methods
    def trigger_clap(self) -> None:
        """Trigger a clap detection."""
        with self.lock:
            self._clap_pending = True

    def read_clap_sensor(self) -> int:
        """Read clap sensor with clear-on-read behavior."""
        with self.lock:
            value = self.beep_status & 0x04
            if value:
                self.beep_status &= ~0x04  # Clear bit 2
            return value

    # Remote control methods
    def send_remote_code(self, code: int) -> None:
        """Simulate a remote control code (0-7)."""
        with self.lock:
            self.ir_rx_status |= 0x02  # Set remote detected bit
            # Store code in appropriate location (simplified)

    def read_remote(self) -> int:
        """Read remote control code with clear-on-read behavior."""
        with self.lock:
            if not (self.ir_rx_status & 0x02):
                return 255  # REMOTE_CODE_NONE

            # Simplified - in real implementation would read match index
            code = 0  # Placeholder
            self.ir_rx_status &= ~0x02  # Clear bit 1
            return code

    # Music methods
    def play_beep(self) -> None:
        """Play standard beep."""
        with self.lock:
            self.beep_action = 4
            # Schedule tone finished after short delay
            self._tone_finished = True

    def read_music_end(self) -> int:
        """Read music end status with clear-on-read behavior."""
        with self.lock:
            result = 0
            if self.beep_status & 0x01:
                self.beep_status &= ~0x01
                result = 1
            if self.beep_status & 0x02:
                self.beep_status &= ~0x02
                result = 1
            return result

    # Timer methods
    def start_countdown(self, time_val: int, units: int) -> None:
        """Start countdown timer."""
        with self.lock:
            if units == 0:  # TIME_SECONDS
                time_val *= 100  # Convert to hundredths
            else:  # TIME_MILLISECONDS
                time_val //= 10  # Convert to hundredths

            self._countdown_duration = time_val
            self._countdown_start = time.time()
            self.timer_one_shot = time_val

    def read_countdown(self, units: int) -> int:
        """Read countdown timer value."""
        with self.lock:
            time_val = self.timer_one_shot
            if units == 0:  # TIME_SECONDS
                return time_val // 100
            else:  # TIME_MILLISECONDS
                return time_val * 10

    def time_wait(self, time_val: int, units: int) -> None:
        """Pause execution for specified time."""
        if units == 0:  # TIME_SECONDS
            delay = time_val
        else:  # TIME_MILLISECONDS
            delay = time_val / 1000.0

        time.sleep(delay)

    # Random number
    def read_random(self) -> int:
        """Generate random 8-bit value."""
        import random
        return random.randint(0, 255)

    # Drive load
    def read_drive_load(self) -> int:
        """Read motor strain status."""
        with self.lock:
            result = 0
            if self.left_motor_strain:
                result |= 0x01
            if self.right_motor_strain:
                result |= 0x01
            return result

    # Getters for GUI
    def get_position(self) -> Tuple[float, float, float]:
        """Get current position and heading."""
        with self.lock:
            return self.x, self.y, self.heading

    def get_led_states(self) -> Tuple[int, int]:
        """Get LED states."""
        with self.lock:
            return self.left_led, self.right_led

    def is_obstacle_detection_enabled(self) -> bool:
        """Check if obstacle detection beam is enabled."""
        with self.lock:
            return self.obstacle_detection_enabled
