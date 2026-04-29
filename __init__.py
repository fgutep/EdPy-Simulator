"""EdPy Robot Simulator - A simulator for the Edison robot programming language.

This package provides a complete simulation environment for testing EdPy code
before running it on the actual Edison robot.

Example usage:
    from simulator import SimulatorGUI

    gui = SimulatorGUI()
    gui.run()
"""

__version__ = "1.0.0"

from .environment import Environment, RectObstacle, CircleObstacle, LineSegment
from .robot_state import RobotState
from .ed_module import EdModule
from .runner import CodeRunner
from .gui import SimulatorGUI

__all__ = [
    'Environment',
    'RectObstacle',
    'CircleObstacle',
    'LineSegment',
    'RobotState',
    'EdModule',
    'CodeRunner',
    'SimulatorGUI',
]
