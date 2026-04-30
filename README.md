# EdPy Robot Simulator

A visual simulator for the Edison robot's EdPy programming language. Test your EdPy code in a virtual environment before running it on the actual robot!

## Credits and License

This simulator is based on **EdPy** - the Python-inspired programming language for the Edison robot.

- **Original EdPy Project**: https://github.com/Bdanilko/EdPy
- **Original Author**: Brian Danilko
- **Documentation**: https://github.com/Bdanilko/EdPy/tree/master/doc
- **EdPy Online Editor**: https://www.edpyapp.com/

The original EdPy project is released under the **GNU General Public License v2.0**.

This simulator was created to provide a visual testing environment for EdPy code, enabling faster iteration when developing robot programs.

---

## Features

- **Visual Robot Representation**: Orange robot with wheels moving on a 2D canvas
- **Maze Editor Mode**: Grid-based wall drawing for creating test environments
- **Sensor Simulation**: Obstacle detection, line tracking, light sensors with accurate "clear-on-read" behavior
- **Real-time Code Execution**: Run EdPy code and watch results immediately
- **Virtual Inputs**: Simulate keypad presses, claps, and remote control signals
- **Performance Optimized**: Smart redrawing and efficient physics (10 Hz update rate)

---

## Quick Start

### Running the Simulator

From the parent directory (EdPy folder):

```bash
python -m simulator
```

Or from within the simulator directory:

```bash
python main.py
```

### Creating a Maze and Testing

1. **Enable Maze Mode**: Check "Maze Mode (Grid Snap)" for grid-aligned walls
2. **Select "Draw Wall"**: Click and drag on the canvas to create walls
3. **Reset Robot**: Click "Reset Robot" to place the robot at your maze start
4. **Run Code**: The obstacle avoidance code is pre-loaded - click "Run"!

---

## Tested Programs

This simulator has been tested with the official EdPy example programs from [EdPyApp.com](https://www.edpyapp.com/v3/):

### 1. Avoid Obstacles Example
The pre-loaded obstacle avoidance program demonstrates:
- IR obstacle detection with `Ed.ReadObstacleDetection()`
- Directional responses (LEFT, RIGHT, AHEAD)
- Random turns using `Ed.Random()`
- LED feedback during navigation

```python
import Ed

Ed.DistanceUnits = Ed.CM
Ed.Tempo = Ed.TEMPO_MEDIUM

LedStatusBlink = 0
Ed.TimeWait(250, Ed.TIME_MILLISECONDS)
Ed.ObstacleDetectionBeam(Ed.ON)
Ed.Drive(Ed.FORWARD, Ed.SPEED_5, Ed.DISTANCE_UNLIMITED)

while True:
    LedStatusBlink = LedStatusBlink ^ 1
    Ed.LeftLed(LedStatusBlink)
    Ed.RightLed(LedStatusBlink)
    Ed.TimeWait(150, Ed.TIME_MILLISECONDS)
    
    if Ed.ReadObstacleDetection() == Ed.OBSTACLE_LEFT:
        # Handle left obstacle
        pass
    elif Ed.ReadObstacleDetection() == Ed.OBSTACLE_RIGHT:
        # Handle right obstacle
        pass
    elif Ed.ReadObstacleDetection() == Ed.OBSTACLE_AHEAD:
        # Handle ahead obstacle
        pass
    Ed.ReadObstacleDetection()  # Clear register
    Ed.Drive(Ed.FORWARD, Ed.SPEED_5, Ed.DISTANCE_UNLIMITED)
```

### 2. Test Program
Basic functionality testing including motor control, LEDs, and timing.

---

## Supported EdPy Commands

### Movement Control

| Command | Description |
|---------|-------------|
| `Ed.Drive(direction, speed, distance)` | Drive both motors |
| `Ed.DriveLeftMotor(direction, speed, distance)` | Drive left motor only |
| `Ed.DriveRightMotor(direction, speed, distance)` | Drive right motor only |
| `Ed.SPIN_LEFT`, `Ed.SPIN_RIGHT` | Spin in place |
| `Ed.SimpleDriveForward()` | Drive forward at full speed |
| `Ed.SimpleDriveBackward()` | Drive backward at full speed |
| `Ed.SimpleDriveStop()` | Stop both motors |
| `Ed.ResetDistance()` | Reset distance counters |
| `Ed.ReadDistance(which)` | Read distance traveled |

**Directions**: `Ed.STOP`, `Ed.FORWARD`, `Ed.BACKWARD`, `Ed.FORWARD_RIGHT`, `Ed.BACKWARD_RIGHT`, `Ed.FORWARD_LEFT`, `Ed.BACKWARD_LEFT`, `Ed.SPIN_RIGHT`, `Ed.SPIN_LEFT`

**Speeds**: `Ed.SPEED_FULL` (0) through `Ed.SPEED_10` (10)

### LED and Control

| Command | Description |
|---------|-------------|
| `Ed.LeftLed(Ed.ON/Ed.OFF)` | Control left LED |
| `Ed.RightLed(Ed.ON/Ed.OFF)` | Control right LED |
| `Ed.ObstacleDetectionBeam(Ed.ON/Ed.OFF)` | Enable/disable IR obstacle detection |
| `Ed.LineTrackerLed(Ed.ON/Ed.OFF)` | Control line tracker LED |
| `Ed.TimeWait(time, units)` | Pause execution |
| `Ed.StartCountDown(time, units)` | Start countdown timer |
| `Ed.ReadCountDown(units)` | Read countdown value |

### Sensor Reading

| Command | Returns | Description |
|---------|---------|-------------|
| `Ed.ReadObstacleDetection()` | `OBSTACLE_LEFT`, `OBSTACLE_RIGHT`, `OBSTACLE_AHEAD`, `OBSTACLE_NONE` | Detect obstacles with IR beam |
| `Ed.ReadLineState()` | `LINE_ON_BLACK` (1) or `LINE_ON_WHITE` (0) | Check line tracker |
| `Ed.ReadLineChange()` | 0 or 1 | Check if surface changed |
| `Ed.ReadKeypad()` | `KEYPAD_TRIANGLE`, `KEYPAD_ROUND`, `KEYPAD_NONE` | Read button press |
| `Ed.ReadClapSensor()` | `CLAP_DETECTED` or `CLAP_NOT_DETECTED` | Check for clap |
| `Ed.ReadRandom()` | 0-255 | Random 8-bit value |
| `Ed.Random(choice1, choice2)` | choice1 or choice2 | Random selection |
| `Ed.ReadDriveLoad()` | Drive strain status | Check motor strain |

### Music and Sound

| Command | Description |
|---------|-------------|
| `Ed.PlayBeep()` | Play standard beep |
| `Ed.PlayTone(freq_code, duration)` | Play tone at frequency |
| `Ed.PlayTune(tune_string)` | Play melody |
| `Ed.ChangeTempo(tempo)` | Change music tempo |
| `Ed.ReadMusicEnd()` | Check if music finished |

### Configuration

| Variable | Values | Description |
|----------|--------|-------------|
| `Ed.DistanceUnits` | `Ed.CM`, `Ed.INCH`, `Ed.TIME` | Distance measurement units |
| `Ed.Tempo` | `Ed.TEMPO_VERY_SLOW` to `Ed.TEMPO_VERY_FAST` | Music tempo |
| `Ed.EdisonVersion` | `Ed.V1`, `Ed.V2` | Robot version |

---

## Maze Editor Interface

### Toolbar Options

- **Select/Move**: Click obstacles to remove them
- **Draw Wall**: Click and drag to create maze walls
- **Draw Line (Follow)**: Draw white lines for line-following programs

### Maze Mode

Enable "Maze Mode (Grid Snap)" to:
- Snap walls to a 30px grid
- Create clean, aligned mazes
- Easier wall placement

### Controls

- **Clear Maze**: Remove all walls and lines
- **Reset Robot**: Place robot at starting position (400, 300)

---

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| **F5** | Run code |
| **Escape** | Stop code execution |

---

## Important Implementation Notes

### Clear-on-Read Behavior

The simulator accurately models the real Edison robot's "clear-on-read" sensor behavior:

- `Ed.ReadObstacleDetection()` - Clears detection after reading
- `Ed.ReadKeypad()` - Clears button after reading
- `Ed.ReadClapSensor()` - Clears clap detection after reading
- `Ed.ReadLineChange()` - Clears change bit after reading
- `Ed.ReadMusicEnd()` - Clears music end status after reading

**Important**: Multiple reads in quick succession (within 500ms) return the same cached value for obstacle detection. This matches the real robot's control loop behavior.

### Obstacle Detection

Remember to enable the IR beam before reading:

```python
Ed.ObstacleDetectionBeam(Ed.ON)  # REQUIRED!
# ... driving code ...
if Ed.ReadObstacleDetection() == Ed.OBSTACLE_AHEAD:
    # Handle obstacle
    pass
```

### Spin Directions

Spin directions properly rotate the robot in place:

```python
Ed.Drive(Ed.SPIN_RIGHT, Ed.SPEED_5, 90)  # Turn 90 degrees right
Ed.Drive(Ed.SPIN_LEFT, Ed.SPEED_5, 90)   # Turn 90 degrees left
```

---

## Virtual Inputs Panel

Simulate real-world interactions:

- **Keypad Buttons**: Triangle (1) and Round (4)
- **Clap Button**: Trigger clap detection
- **Sensors Panel**: Real-time display of position, heading, LED states, obstacles, and line state

---

## Architecture

The simulator is organized into modules:

- `__main__.py` - Entry point for `python -m simulator`
- `main.py` - Standalone entry point
- `environment.py` - Obstacles, lines, and collision detection
- `robot_state.py` - Robot physics, position, heading, sensor state
- `ed_module.py` - Ed.* function implementations
- `runner.py` - Code execution harness with stop flag support
- `gui.py` - Tkinter user interface with maze editor

---

## Requirements

- Python 3.6+
- tkinter (usually included with Python)
- threading (standard library)

---

## References

- **EdPy Documentation**: https://github.com/Bdanilko/EdPy/tree/master/doc
- **EdPyApp Online Editor**: https://www.edpyapp.com/v3/
- **Original EdPy Project**: https://github.com/Bdanilko/EdPy

---

## License

This simulator follows the same license as the original EdPy project:
**GNU General Public License v2.0**

See the LICENSE file in the parent directory for full license text.
