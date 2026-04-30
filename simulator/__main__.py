"""Main entry point for running the simulator as a module.

Usage:
    python -m simulator
"""

from .gui import SimulatorGUI


def main():
    """Run the EdPy Robot Simulator."""
    gui = SimulatorGUI()
    gui.run()


if __name__ == "__main__":
    main()
