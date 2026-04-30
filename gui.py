"""GUI module for EdPy Robot Simulator.

Provides a tkinter-based graphical interface for visualizing the robot,
controlling the simulation, and editing the environment.
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox
import math
import threading
from typing import Optional, Tuple
from .environment import Environment, RectObstacle, CircleObstacle, LineSegment
from .robot_state import RobotState
from .runner import CodeRunner


class SimulatorGUI:
    """Main GUI window for the EdPy Robot Simulator."""

    # Canvas dimensions - sized to fit on typical screens
    CANVAS_WIDTH = 900
    CANVAS_HEIGHT = 700

    # Grid settings for maze mode
    GRID_SIZE = 30  # Pixels per grid cell

    # Robot drawing dimensions
    ROBOT_LENGTH = 36
    ROBOT_WIDTH = 28

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("EdPy Robot Simulator - Maze Edition")
        self.root.geometry("1400x900")
        self.root.configure(bg='#2b2b2b')

        # Make window resizable and set minimum size
        self.root.minsize(1200, 700)

        # Configure modern dark theme
        self._setup_styles()

        # Create environment and robot state
        self.environment = Environment(self.CANVAS_WIDTH, self.CANVAS_HEIGHT)
        self.environment.create_default_environment()
        self.robot_state = RobotState(self.environment, 400, 300)

        # Create code runner
        self.runner = CodeRunner(self.robot_state)
        self.runner.on_error = self._on_code_error
        self.runner.on_complete = self._on_code_complete

        # Drawing mode
        self.draw_mode = "select"
        self.draw_start = None
        self.temp_shape = None
        self.maze_mode = False  # Grid-based drawing
        self.grid_items = []  # Store grid line item IDs

        # Canvas item IDs for efficient updates
        self._canvas_items = {}
        self._obstacle_items = []
        self._line_items = []
        self._last_robot_pos = None
        self._last_robot_heading = None
        self._last_left_led = None
        self._last_right_led = None
        self._last_ir_enabled = None
        self._needs_full_redraw = True

        # Build UI
        self._create_menu()
        self._create_layout()
        self._create_bindings()

        # Start robot physics
        self.robot_state.start()

        # Start GUI update loop (lower frequency for performance)
        self._update_gui()

    def _setup_styles(self) -> None:
        """Configure modern dark theme styles."""
        # Color scheme
        self.colors = {
            'bg': '#2b2b2b',
            'bg_light': '#3c3c3c',
            'bg_lighter': '#4a4a4a',
            'fg': '#f0f0f0',
            'fg_dim': '#b0b0b0',
            'accent': '#0d8bd9',
            'accent_hover': '#0a7bc0',
            'success': '#4caf50',
            'warning': '#ff9800',
            'error': '#f44336',
            'maze_grid': '#444444',
            'robot_orange': '#ff8c00',
            'robot_outline': '#cc5500',
        }

        style = ttk.Style()
        style.theme_use('clam')

        # Configure main styles
        style.configure('.',
            background=self.colors['bg'],
            foreground=self.colors['fg'],
            fieldbackground=self.colors['bg_light'],
            font=('Segoe UI', 10)
        )

        style.configure('TFrame', background=self.colors['bg'])
        style.configure('TLabel', background=self.colors['bg'], foreground=self.colors['fg'])
        style.configure('TButton',
            background=self.colors['bg_light'],
            foreground=self.colors['fg'],
            padding=(10, 5),
            font=('Segoe UI', 10)
        )
        style.map('TButton',
            background=[('active', self.colors['bg_lighter']), ('pressed', self.colors['accent'])],
            foreground=[('pressed', 'white')]
        )

        style.configure('Accent.TButton',
            background=self.colors['accent'],
            foreground='white',
            padding=(15, 8),
            font=('Segoe UI', 10, 'bold')
        )
        style.map('Accent.TButton',
            background=[('active', self.colors['accent_hover']), ('pressed', '#0869a3')]
        )

        style.configure('Stop.TButton',
            background=self.colors['error'],
            foreground='white',
            padding=(15, 8),
            font=('Segoe UI', 10, 'bold')
        )

        style.configure('TLabelframe',
            background=self.colors['bg'],
            foreground=self.colors['fg'],
            padding=10
        )
        style.configure('TLabelframe.Label',
            background=self.colors['bg'],
            foreground=self.colors['fg'],
            font=('Segoe UI', 10, 'bold')
        )

        style.configure('TRadiobutton',
            background=self.colors['bg'],
            foreground=self.colors['fg']
        )
        style.configure('TEntry',
            fieldbackground=self.colors['bg_light'],
            foreground=self.colors['fg'],
            insertcolor=self.colors['fg']
        )

        # Menu styling
        self.root.option_add('*Menu.background', self.colors['bg_light'])
        self.root.option_add('*Menu.foreground', self.colors['fg'])
        self.root.option_add('*Menu.activeBackground', self.colors['accent'])
        self.root.option_add('*Menu.activeForeground', 'white')

    def _create_menu(self) -> None:
        """Create menu bar."""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Load Code...", command=self._load_code)
        file_menu.add_command(label="Save Code...", command=self._save_code)
        file_menu.add_separator()
        file_menu.add_command(label="Clear Environment", command=self._clear_environment)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self._on_exit)

        # View menu
        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="View", menu=view_menu)
        view_menu.add_command(label="Reset Robot Position", command=self._reset_robot)
        view_menu.add_checkbutton(label="Show Grid", command=self._toggle_grid)

        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self._show_about)

    def _create_layout(self) -> None:
        """Create the main GUI layout."""
        # Main container with paned window for resizable sections
        main_paned = tk.PanedWindow(self.root, orient=tk.HORIZONTAL, bg='#2b2b2b')
        main_paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Left side: Canvas
        canvas_frame = ttk.LabelFrame(main_paned, text="Maze Editor - Step 1: Draw your maze, Step 2: Run code!")
        main_paned.add(canvas_frame, minsize=400)

        # Canvas toolbar - Maze focused (pack FIRST so it's at top)
        canvas_toolbar = ttk.Frame(canvas_frame)
        canvas_toolbar.pack(fill=tk.X, padx=5, pady=2, side=tk.TOP)

        self.canvas = tk.Canvas(
            canvas_frame,
            width=self.CANVAS_WIDTH,
            height=self.CANVAS_HEIGHT,
            bg="#1a1a1a",
            highlightthickness=1,
            highlightbackground="#3c3c3c"
        )
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        ttk.Label(canvas_toolbar, text="Tools:", font=('Segoe UI', 10, 'bold')).pack(side=tk.LEFT, padx=5)

        self.mode_var = tk.StringVar(value="select")
        ttk.Radiobutton(
            canvas_toolbar, text="Select/Move", variable=self.mode_var,
            value="select", command=self._set_mode
        ).pack(side=tk.LEFT, padx=2)
        ttk.Radiobutton(
            canvas_toolbar, text="Draw Wall", variable=self.mode_var,
            value="wall", command=self._set_mode
        ).pack(side=tk.LEFT, padx=2)
        ttk.Radiobutton(
            canvas_toolbar, text="Draw Line (Follow)", variable=self.mode_var,
            value="line", command=self._set_mode
        ).pack(side=tk.LEFT, padx=2)

        ttk.Separator(canvas_toolbar, orient=tk.VERTICAL).pack(
            side=tk.LEFT, fill=tk.Y, padx=10
        )

        # Maze mode toggle
        self.maze_mode_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            canvas_toolbar, text="Maze Mode (Grid Snap)",
            variable=self.maze_mode_var, command=self._toggle_maze_mode
        ).pack(side=tk.LEFT, padx=5)

        ttk.Separator(canvas_toolbar, orient=tk.VERTICAL).pack(
            side=tk.LEFT, fill=tk.Y, padx=10
        )

        ttk.Button(
            canvas_toolbar, text="Clear Maze",
            command=self._clear_environment
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            canvas_toolbar, text="Reset Robot",
            command=self._reset_robot
        ).pack(side=tk.LEFT, padx=5)

        # Instructions label (at bottom of canvas frame)
        self.instruction_label = ttk.Label(
            canvas_frame,
            text="📝 INSTRUCTIONS: 1) Select 'Draw Wall' and create a maze  2) Place robot at start  3) Write or load EdPy code  4) Click Run!",
            foreground=self.colors['warning'],
            font=('Segoe UI', 10, 'bold')
        )
        self.instruction_label.pack(fill=tk.X, padx=5, pady=2, side=tk.BOTTOM)

        # Right side: Controls (scrollable)
        right_container = ttk.Frame(main_paned)
        main_paned.add(right_container, minsize=300)

        # Add scrollbar to right panel
        right_canvas = tk.Canvas(right_container, bg='#2b2b2b', highlightthickness=0)
        scrollbar = ttk.Scrollbar(right_container, orient=tk.VERTICAL, command=right_canvas.yview)
        right_frame = ttk.Frame(right_canvas)

        right_frame.bind(
            "<Configure>",
            lambda e: right_canvas.configure(scrollregion=right_canvas.bbox("all"))
        )

        right_canvas.create_window((0, 0), window=right_frame, anchor=tk.NW)
        right_canvas.configure(yscrollcommand=scrollbar.set)

        right_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Mouse wheel support for scrolling
        def _on_mousewheel(event):
            right_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        right_canvas.bind_all("<MouseWheel>", _on_mousewheel)

        # Code editor
        code_frame = ttk.LabelFrame(right_frame, text="EdPy Code Editor")
        code_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        self.code_editor = scrolledtext.ScrolledText(
            code_frame, width=40, height=20, wrap=tk.WORD,
            bg='#1e1e1e', fg='#d4d4d4',
            insertbackground='#ffffff',
            font=('Consolas', 10),
            relief=tk.FLAT,
            highlightthickness=1,
            highlightbackground='#3c3c3c',
            padx=10, pady=10
        )
        self.code_editor.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Load example code that matches the Edison tutorial exactly
        default_code = '''import Ed

Ed.DistanceUnits = Ed.CM
Ed.Tempo = Ed.TEMPO_MEDIUM

# Create the variable LedStatusBlink and set to 0
LedStatusBlink = 0
Ed.TimeWait(250, Ed.TIME_MILLISECONDS)
# turn on obstacle detection
Ed.ObstacleDetectionBeam(Ed.ON)
# start Edison driving, without a duration
Ed.Drive(Ed.FORWARD, Ed.SPEED_5, Ed.DISTANCE_UNLIMITED)

# loop forever
while True:
    # Flash the LED lights on and off
    LedStatusBlink = LedStatusBlink ^ 1  # XOR 1 to alternate between 0 and 1
    Ed.LeftLed(LedStatusBlink)
    Ed.RightLed(LedStatusBlink)
    Ed.TimeWait(150, Ed.TIME_MILLISECONDS)

    # Check for obstacles and drive away if any are detected
    if Ed.ReadObstacleDetection() == Ed.OBSTACLE_LEFT:
        Ed.LeftLed(Ed.ON)
        Ed.RightLed(Ed.OFF)
        Ed.PlayBeep()
        Ed.Drive(Ed.BACKWARD, Ed.SPEED_5, 3)
        Ed.Drive(Ed.SPIN_RIGHT, Ed.SPEED_5, 60)
        Ed.Drive(Ed.STOP, 0, 0)
        Ed.TimeWait(100, Ed.TIME_MILLISECONDS)
    elif Ed.ReadObstacleDetection() == Ed.OBSTACLE_RIGHT:
        Ed.RightLed(Ed.ON)
        Ed.LeftLed(Ed.OFF)
        Ed.PlayBeep()
        Ed.Drive(Ed.BACKWARD, Ed.SPEED_5, 3)
        Ed.Drive(Ed.SPIN_LEFT, Ed.SPEED_5, 60)
        Ed.Drive(Ed.STOP, 0, 0)
        Ed.TimeWait(100, Ed.TIME_MILLISECONDS)
    elif Ed.ReadObstacleDetection() == Ed.OBSTACLE_AHEAD:
        Ed.LeftLed(Ed.ON)
        Ed.RightLed(Ed.ON)
        Ed.PlayBeep()
        Ed.Drive(Ed.BACKWARD, Ed.SPEED_5, 3)
        Ed.Drive(Ed.Random(Ed.SPIN_RIGHT, Ed.SPIN_LEFT), Ed.SPEED_5, 160)
        Ed.Drive(Ed.STOP, 0, 0)
        Ed.TimeWait(100, Ed.TIME_MILLISECONDS)
    Ed.ReadObstacleDetection()  # clear the ReadObstacleDetection register
    Ed.Drive(Ed.FORWARD, Ed.SPEED_5, Ed.DISTANCE_UNLIMITED)
'''
        self.code_editor.insert("1.0", default_code)

        # Control buttons
        control_frame = ttk.Frame(right_frame)
        control_frame.pack(fill=tk.X, pady=5)

        self.run_button = ttk.Button(
            control_frame, text="▶ Run", command=self._run_code,
            style='Accent.TButton'
        )
        self.run_button.pack(side=tk.LEFT, padx=2)

        self.stop_button = ttk.Button(
            control_frame, text="⏹ Stop", command=self._stop_code,
            state=tk.DISABLED, style='Stop.TButton'
        )
        self.stop_button.pack(side=tk.LEFT, padx=2)

        # Sensor display
        sensor_frame = ttk.LabelFrame(right_frame, text="Sensors")
        sensor_frame.pack(fill=tk.X, pady=5)

        self.sensor_labels = {}
        sensors = [
            ("Position", "pos_label"),
            ("Heading", "heading_label"),
            ("Left LED", "left_led_label"),
            ("Right LED", "right_led_label"),
            ("Obstacles", "obstacle_label"),
            ("Line State", "line_label"),
        ]

        for text, key in sensors:
            row = ttk.Frame(sensor_frame)
            row.pack(fill=tk.X, padx=5, pady=2)
            ttk.Label(row, text=text + ":").pack(side=tk.LEFT)
            label = ttk.Label(row, text="--")
            label.pack(side=tk.RIGHT)
            self.sensor_labels[key] = label

        # Virtual inputs
        input_frame = ttk.LabelFrame(right_frame, text="Virtual Inputs")
        input_frame.pack(fill=tk.X, pady=5)

        # Keypad buttons
        keypad_frame = ttk.Frame(input_frame)
        keypad_frame.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(keypad_frame, text="Keypad:").pack(side=tk.LEFT)
        ttk.Button(
            keypad_frame, text="Triangle",
            command=lambda: self.robot_state.press_button(0x01)
        ).pack(side=tk.LEFT, padx=2)
        ttk.Button(
            keypad_frame, text="Round",
            command=lambda: self.robot_state.press_button(0x04)
        ).pack(side=tk.LEFT, padx=2)

        # Clap button
        clap_frame = ttk.Frame(input_frame)
        clap_frame.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(clap_frame, text="Sensors:").pack(side=tk.LEFT)
        ttk.Button(
            clap_frame, text="Clap!",
            command=self.robot_state.trigger_clap
        ).pack(side=tk.LEFT, padx=2)

        # Status bar
        self.status_var = tk.StringVar(value="Ready - Create your maze!")
        status_bar = ttk.Label(
            self.root, textvariable=self.status_var,
            relief=tk.SUNKEN, anchor=tk.W
        )
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def _create_bindings(self) -> None:
        """Create event bindings."""
        # Canvas mouse events for drawing
        self.canvas.bind("<Button-1>", self._on_canvas_click)
        self.canvas.bind("<B1-Motion>", self._on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_canvas_release)

        # Keyboard shortcuts
        self.root.bind("<F5>", lambda e: self._run_code())
        self.root.bind("<Escape>", lambda e: self._stop_code())

        # Window close
        self.root.protocol("WM_DELETE_WINDOW", self._on_exit)

    def _toggle_maze_mode(self) -> None:
        """Toggle maze mode with grid snapping."""
        self.maze_mode = self.maze_mode_var.get()
        if self.maze_mode:
            self._draw_grid()
            self.status_var.set("Maze Mode ON - Walls snap to grid")
        else:
            self._clear_grid()
            self.status_var.set("Maze Mode OFF - Free drawing")

    def _draw_grid(self) -> None:
        """Draw grid lines on canvas."""
        self._clear_grid()
        for x in range(0, self.CANVAS_WIDTH, self.GRID_SIZE):
            line = self.canvas.create_line(x, 0, x, self.CANVAS_HEIGHT, fill="#333333", tags="grid")
            self.grid_items.append(line)
        for y in range(0, self.CANVAS_HEIGHT, self.GRID_SIZE):
            line = self.canvas.create_line(0, y, self.CANVAS_WIDTH, y, fill="#333333", tags="grid")
            self.grid_items.append(line)
        self.canvas.tag_lower("grid")  # Put grid behind everything

    def _clear_grid(self) -> None:
        """Remove grid lines from canvas."""
        for item in self.grid_items:
            self.canvas.delete(item)
        self.grid_items.clear()

    def _toggle_grid(self) -> None:
        """Toggle grid visibility from menu."""
        if self.grid_items:
            self._clear_grid()
        else:
            self._draw_grid()

    def _snap_to_grid(self, x: float, y: float) -> Tuple[int, int]:
        """Snap coordinates to nearest grid point."""
        grid_x = round(x / self.GRID_SIZE) * self.GRID_SIZE
        grid_y = round(y / self.GRID_SIZE) * self.GRID_SIZE
        return grid_x, grid_y

    def _set_mode(self) -> None:
        """Set the drawing mode."""
        self.draw_mode = self.mode_var.get()
        self.status_var.set(f"Mode: {self.draw_mode}")

    def _on_canvas_click(self, event) -> None:
        """Handle canvas click."""
        x, y = event.x, event.y

        if self.draw_mode == "select":
            # Check if clicked on obstacle
            obs = self.environment.get_obstacle_at(x, y)
            if obs:
                self.environment.remove_obstacle_at(x, y)
                self._needs_full_redraw = True
                self.status_var.set("Obstacle removed")
        else:
            # Start drawing - snap to grid if maze mode
            if self.maze_mode:
                x, y = self._snap_to_grid(x, y)
            self.draw_start = (x, y)

    def _on_canvas_drag(self, event) -> None:
        """Handle canvas drag."""
        if self.draw_start is None or self.draw_mode == "select":
            return

        x1, y1 = self.draw_start
        x2, y2 = event.x, event.y

        # Snap to grid if maze mode
        if self.maze_mode:
            x2, y2 = self._snap_to_grid(x2, y2)

        # Remove previous temp shape
        if self.temp_shape:
            self.canvas.delete(self.temp_shape)

        # Draw new temp shape
        if self.draw_mode == "wall":
            self.temp_shape = self.canvas.create_rectangle(
                x1, y1, x2, y2, outline="#ff8c00", dash=(4, 4), width=2
            )
        elif self.draw_mode == "line":
            self.temp_shape = self.canvas.create_line(
                x1, y1, x2, y2, fill="white", width=4, dash=(4, 4)
            )

    def _on_canvas_release(self, event) -> None:
        """Handle canvas release."""
        if self.draw_start is None or self.draw_mode == "select":
            return

        x1, y1 = self.draw_start
        x2, y2 = event.x, event.y

        # Snap to grid if maze mode
        if self.maze_mode:
            x2, y2 = self._snap_to_grid(x2, y2)

        # Remove temp shape
        if self.temp_shape:
            self.canvas.delete(self.temp_shape)
            self.temp_shape = None

        # Add permanent shape
        if self.draw_mode == "wall":
            min_size = self.GRID_SIZE if self.maze_mode else 10
            if abs(x2-x1) >= min_size and abs(y2-y1) >= min_size:
                self.environment.add_obstacle(
                    RectObstacle(min(x1,x2), min(y1,y2), abs(x2-x1), abs(y2-y1))
                )
                self._needs_full_redraw = True
                self.status_var.set("Wall added - Build your maze!")
        elif self.draw_mode == "line":
            min_length = self.GRID_SIZE if self.maze_mode else 10
            if math.sqrt((x2-x1)**2 + (y2-y1)**2) >= min_length:
                self.environment.add_line(
                    LineSegment(x1, y1, x2, y2, thickness=6)
                )
                self._needs_full_redraw = True
                self.status_var.set("Line added - For line following!")

        self.draw_start = None

    def _draw_environment(self) -> None:
        """Draw all environment elements on the canvas (only when needed)."""
        if not self._needs_full_redraw:
            return

        # Clear environment items only
        self.canvas.delete("env")
        self._obstacle_items.clear()
        self._line_items.clear()

        # Draw lines (white for visibility on dark background)
        for line in self.environment.lines:
            item = self.canvas.create_line(
                line.x1, line.y1, line.x2, line.y2,
                fill="white", width=line.thickness,
                tags="env"
            )
            self._line_items.append(item)

        # Draw obstacles (maze walls - darker gray)
        for obs in self.environment.obstacles:
            if isinstance(obs, RectObstacle):
                item = self.canvas.create_rectangle(
                    obs.x, obs.y, obs.x + obs.width, obs.y + obs.height,
                    fill="#404040", outline="#606060", width=2, tags="env"
                )
                self._obstacle_items.append(item)
            elif isinstance(obs, CircleObstacle):
                item = self.canvas.create_oval(
                    obs.x - obs.radius, obs.y - obs.radius,
                    obs.x + obs.radius, obs.y + obs.radius,
                    fill="#404040", outline="#606060", tags="env"
                )
                self._obstacle_items.append(item)

        self._needs_full_redraw = False

    def _draw_robot(self) -> None:
        """Draw or update the robot on the canvas - Orange with wheels."""
        x, y, heading = self.robot_state.get_position()
        left_led, right_led = self.robot_state.get_led_states()
        ir_enabled = self.robot_state.is_obstacle_detection_enabled()

        # Check if robot needs redrawing
        pos_changed = self._last_robot_pos != (x, y)
        heading_changed = self._last_robot_heading != heading
        led_changed = (self._last_left_led != left_led or
                       self._last_right_led != right_led)
        ir_changed = self._last_ir_enabled != ir_enabled

        if not pos_changed and not heading_changed and not led_changed and not ir_changed:
            return  # No change, skip redraw

        # Update cached values
        self._last_robot_pos = (x, y)
        self._last_robot_heading = heading
        self._last_left_led = left_led
        self._last_right_led = right_led
        self._last_ir_enabled = ir_enabled

        # Calculate rotation
        rad = math.radians(heading)
        cos_h = math.cos(rad)
        sin_h = math.sin(rad)

        half_len = self.ROBOT_LENGTH / 2
        half_width = self.ROBOT_WIDTH / 2

        # Robot body corners
        corners = [
            (half_len, half_width),    # Front right
            (half_len, -half_width),   # Front left
            (-half_len, -half_width),  # Back left
            (-half_len, half_width),   # Back right
        ]

        rotated_corners = []
        for cx, cy in corners:
            rx = cx * cos_h - cy * sin_h + x
            ry = cx * sin_h + cy * cos_h + y
            rotated_corners.append((rx, ry))

        # Draw or update robot body (ORANGE)
        if "robot_body" in self._canvas_items:
            flat_coords = [coord for point in rotated_corners for coord in point]
            self.canvas.coords(self._canvas_items["robot_body"], *flat_coords)
        else:
            self._canvas_items["robot_body"] = self.canvas.create_polygon(
                rotated_corners, fill=self.colors['robot_orange'], outline=self.colors['robot_outline'],
                width=2, tags="robot"
            )

        # Draw wheels (small black squares at back)
        wheel_offset_x = -half_len / 2
        wheel_offset_y = half_width - 4
        wheel_size = 6

        # Left wheel
        left_wheel_x = x + (wheel_offset_x * cos_h - wheel_offset_y * sin_h)
        left_wheel_y = y + (wheel_offset_x * sin_h + wheel_offset_y * cos_h)
        # Right wheel
        right_wheel_x = x + (wheel_offset_x * cos_h - (-wheel_offset_y) * sin_h)
        right_wheel_y = y + (wheel_offset_x * sin_h + (-wheel_offset_y) * cos_h)

        if "left_wheel" in self._canvas_items:
            self.canvas.coords(
                self._canvas_items["left_wheel"],
                left_wheel_x - wheel_size/2, left_wheel_y - wheel_size/2,
                left_wheel_x + wheel_size/2, left_wheel_y + wheel_size/2
            )
        else:
            self._canvas_items["left_wheel"] = self.canvas.create_rectangle(
                left_wheel_x - wheel_size/2, left_wheel_y - wheel_size/2,
                left_wheel_x + wheel_size/2, left_wheel_y + wheel_size/2,
                fill="#222222", outline="#000000", tags="robot"
            )

        if "right_wheel" in self._canvas_items:
            self.canvas.coords(
                self._canvas_items["right_wheel"],
                right_wheel_x - wheel_size/2, right_wheel_y - wheel_size/2,
                right_wheel_x + wheel_size/2, right_wheel_y + wheel_size/2
            )
        else:
            self._canvas_items["right_wheel"] = self.canvas.create_rectangle(
                right_wheel_x - wheel_size/2, right_wheel_y - wheel_size/2,
                right_wheel_x + wheel_size/2, right_wheel_y + wheel_size/2,
                fill="#222222", outline="#000000", tags="robot"
            )

        # Draw heading indicator (nose)
        nose_len = half_len + 8
        nose_x = nose_len * cos_h + x
        nose_y = nose_len * sin_h + y

        if "robot_nose" in self._canvas_items:
            self.canvas.coords(self._canvas_items["robot_nose"], x, y, nose_x, nose_y)
        else:
            self._canvas_items["robot_nose"] = self.canvas.create_line(
                x, y, nose_x, nose_y,
                fill="#ff0000", width=3, arrow=tk.LAST, tags="robot"
            )

        # Draw LEDs
        led_offset = 10
        left_led_x = x + (-half_len/2 * cos_h - led_offset * sin_h)
        left_led_y = y + (-half_len/2 * sin_h + led_offset * cos_h)
        right_led_x = x + (-half_len/2 * cos_h + led_offset * sin_h)
        right_led_y = y + (-half_len/2 * sin_h - led_offset * cos_h)

        left_color = "#ff0000" if left_led else "#330000"
        right_color = "#ff0000" if right_led else "#330000"

        if "left_led" in self._canvas_items:
            self.canvas.coords(
                self._canvas_items["left_led"],
                left_led_x-3, left_led_y-3, left_led_x+3, left_led_y+3
            )
            self.canvas.itemconfig(self._canvas_items["left_led"], fill=left_color)
        else:
            self._canvas_items["left_led"] = self.canvas.create_oval(
                left_led_x-3, left_led_y-3, left_led_x+3, left_led_y+3,
                fill=left_color, outline="#000000", tags="robot"
            )

        if "right_led" in self._canvas_items:
            self.canvas.coords(
                self._canvas_items["right_led"],
                right_led_x-3, right_led_y-3, right_led_x+3, right_led_y+3
            )
            self.canvas.itemconfig(self._canvas_items["right_led"], fill=right_color)
        else:
            self._canvas_items["right_led"] = self.canvas.create_oval(
                right_led_x-3, right_led_y-3, right_led_x+3, right_led_y+3,
                fill=right_color, outline="#000000", tags="robot"
            )

        # Draw or update IR beam
        if ir_enabled:
            beam_len = 100
            beam_angle = 15  # Half-angle of cone

            left_rad = math.radians(heading - beam_angle)
            left_x = beam_len * math.cos(left_rad) + x
            left_y = beam_len * math.sin(left_rad) + y

            right_rad = math.radians(heading + beam_angle)
            right_x = beam_len * math.cos(right_rad) + x
            right_y = beam_len * math.sin(right_rad) + y

            if "ir_beam" in self._canvas_items:
                self.canvas.coords(
                    self._canvas_items["ir_beam"],
                    x, y, left_x, left_y, right_x, right_y
                )
                self.canvas.itemconfig(self._canvas_items["ir_beam"], state=tk.NORMAL)
            else:
                self._canvas_items["ir_beam"] = self.canvas.create_polygon(
                    x, y, left_x, left_y, right_x, right_y,
                    fill="", outline="#ff4444", stipple="gray50", tags="robot"
                )
        else:
            if "ir_beam" in self._canvas_items:
                self.canvas.itemconfig(self._canvas_items["ir_beam"], state=tk.HIDDEN)

    def _update_gui(self) -> None:
        """Update GUI elements periodically."""
        self._draw_environment()
        self._draw_robot()
        self._update_sensor_labels()

        # Schedule next update (lower frequency for better performance)
        self.root.after(100, self._update_gui)  # 10 Hz update

    def _update_sensor_labels(self) -> None:
        """Update sensor display labels."""
        x, y, heading = self.robot_state.get_position()
        left_led, right_led = self.robot_state.get_led_states()

        # Position
        self.sensor_labels["pos_label"].config(text=f"({x:.0f}, {y:.0f})")

        # Heading
        self.sensor_labels["heading_label"].config(text=f"{heading:.0f}")

        # LEDs
        self.sensor_labels["left_led_label"].config(
            text="ON" if left_led else "OFF",
            foreground="#ff4444" if left_led else "#666666"
        )
        self.sensor_labels["right_led_label"].config(
            text="ON" if right_led else "OFF",
            foreground="#ff4444" if right_led else "#666666"
        )

        # Obstacles
        obstacle = self.robot_state.read_obstacle_detection()
        obs_text = "None"
        if obstacle & 0x20:
            obs_text = "Left"
        elif obstacle & 0x10:
            obs_text = "Ahead"
        elif obstacle & 0x08:
            obs_text = "Right"
        self.sensor_labels["obstacle_label"].config(text=obs_text)

        # Line state
        line = self.robot_state.read_line_state()
        self.sensor_labels["line_label"].config(
            text="Black" if line else "White"
        )

    def _run_code(self) -> None:
        """Run the EdPy code from the editor."""
        code = self.code_editor.get("1.0", tk.END)
        if not code.strip():
            messagebox.showwarning("Empty Code", "Please enter some EdPy code to run.")
            return

        # Update UI
        self.run_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.status_var.set("Running...")

        # Start execution
        self.runner.execute(code)

    def _stop_code(self) -> None:
        """Stop the running code."""
        self.runner.stop()
        self.status_var.set("Stopped")

    def _on_code_error(self, error_msg: str) -> None:
        """Handle code execution error."""
        self.root.after(0, lambda: self._show_error(error_msg))

    def _show_error(self, error_msg: str) -> None:
        """Show error message (called from main thread)."""
        self.status_var.set("Error!")
        messagebox.showerror("Execution Error", error_msg)
        self._reset_buttons()

    def _on_code_complete(self) -> None:
        """Handle code completion."""
        self.root.after(0, self._reset_buttons)

    def _reset_buttons(self) -> None:
        """Reset button states after execution."""
        self.run_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.status_var.set("Ready")

    def _reset_robot(self) -> None:
        """Reset robot position and state."""
        self.robot_state.reset(400, 300, 0)
        self.status_var.set("Robot reset - Place at maze start!")

    def _clear_environment(self) -> None:
        """Clear all obstacles and lines."""
        if messagebox.askyesno("Confirm", "Clear all obstacles and lines?"):
            self.environment.clear()
            self._needs_full_redraw = True
            self.status_var.set("Maze cleared - Start building!")

    def _load_code(self) -> None:
        """Load code from file."""
        filename = filedialog.askopenfilename(
            title="Load EdPy Code",
            filetypes=[("Python files", "*.py"), ("All files", "*.*")]
        )
        if filename:
            try:
                with open(filename, 'r') as f:
                    code = f.read()
                self.code_editor.delete("1.0", tk.END)
                self.code_editor.insert("1.0", code)
                self.status_var.set(f"Loaded: {filename}")
            except Exception as e:
                messagebox.showerror("Error", f"Could not load file:\n{e}")

    def _save_code(self) -> None:
        """Save code to file."""
        filename = filedialog.asksaveasfilename(
            title="Save EdPy Code",
            defaultextension=".py",
            filetypes=[("Python files", "*.py"), ("All files", "*.*")]
        )
        if filename:
            try:
                code = self.code_editor.get("1.0", tk.END)
                with open(filename, 'w') as f:
                    f.write(code)
                self.status_var.set(f"Saved: {filename}")
            except Exception as e:
                messagebox.showerror("Error", f"Could not save file:\n{e}")

    def _show_about(self) -> None:
        """Show about dialog."""
        messagebox.showinfo(
            "About EdPy Robot Simulator",
            "EdPy Robot Simulator - Maze Edition v1.0\n\n"
            "A simulator for the Edison robot programming language.\n\n"
            "Maze Mode Features:\n"
            "- Grid-based wall drawing\n"
            "- Higher resolution canvas (1200x900)\n"
            "- Orange robot with wheels\n"
            "- Line following support\n\n"
            "Workflow:\n"
            "1. Draw your maze using 'Draw Wall' tool\n"
            "2. Optionally add lines for line-following\n"
            "3. Reset robot to starting position\n"
            "4. Write or load EdPy code\n"
            "5. Click Run to test!"
        )

    def _on_exit(self) -> None:
        """Clean up and exit."""
        self.robot_state.stop()
        self.runner.stop()
        self.root.destroy()

    def run(self) -> None:
        """Start the GUI main loop."""
        self.root.mainloop()


def main():
    """Main entry point for the simulator."""
    gui = SimulatorGUI()
    gui.run()


if __name__ == "__main__":
    main()
