"""Code runner module for EdPy Robot Simulator.

Provides a sandboxed environment for executing user EdPy code
with access to the simulated Ed module.
"""

import threading
import traceback
from typing import Optional, Callable
from .robot_state import RobotState
from .ed_module import EdModule


class CodeRunner:
    """Executes EdPy code in a sandboxed environment."""

    def __init__(self, state: RobotState):
        self.state = state
        self._stop_requested = False
        self.ed = EdModule(state, self)
        self._execution_thread: Optional[threading.Thread] = None
        self._running = False
        self.on_error: Optional[Callable[[str], None]] = None
        self.on_complete: Optional[Callable[[], None]] = None

    def execute(self, code: str) -> bool:
        """Execute EdPy code in a separate thread.

        Args:
            code: The EdPy source code to execute

        Returns:
            True if execution started successfully, False otherwise
        """
        if self._running:
            return False

        self._stop_requested = False
        self._running = True

        self._execution_thread = threading.Thread(
            target=self._run_code,
            args=(code,),
            daemon=True
        )
        self._execution_thread.start()
        return True

    def _run_code(self, code: str) -> None:
        """Internal method to run the code."""
        try:
            print("[DEBUG] Starting code execution...")

            # Create execution environment with Ed module
            exec_globals = {
                '__name__': '__main__',
                'Ed': self.ed,
            }

            # Add Python built-ins that EdPy supports
            exec_globals['ord'] = ord
            exec_globals['chr'] = chr
            exec_globals['len'] = len
            exec_globals['abs'] = abs
            exec_globals['range'] = range
            exec_globals['enumerate'] = enumerate
            exec_globals['zip'] = zip
            exec_globals['print'] = print

            # Execute the code
            exec(code, exec_globals)
            print("[DEBUG] Code execution completed normally.")

        except Exception as e:
            print(f"[DEBUG] EXCEPTION CAUGHT: {type(e).__name__}: {str(e)}")
            error_msg = f"Error executing code: {type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
            if self.on_error:
                self.on_error(error_msg)
            else:
                print(error_msg)

        finally:
            self._running = False
            if self.on_complete:
                self.on_complete()

    def stop(self) -> None:
        """Request the running code to stop.

        Note: This cannot force-stop the code immediately due to Python's
        GIL. The code will stop at the next Python bytecode instruction.
        """
        print("[DEBUG] Stop requested")
        self._stop_requested = True

        # Reset motor states to stop the robot
        self.state.set_left_motor(0xC0)  # STOP
        self.state.set_right_motor(0xC0)  # STOP

    def is_running(self) -> bool:
        """Check if code is currently running."""
        return self._running

    def wait_for_completion(self, timeout: Optional[float] = None) -> bool:
        """Wait for code execution to complete.

        Args:
            timeout: Maximum time to wait in seconds, or None for infinite

        Returns:
            True if execution completed, False if timeout occurred
        """
        if self._execution_thread and self._execution_thread.is_alive():
            self._execution_thread.join(timeout=timeout)
            return not self._execution_thread.is_alive()
        return True
