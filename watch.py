"""Watch for the simulated app and launch another program when it appears.

Fill in the two TODO functions, then run:

    python watch.py

In a second terminal, start the target:

    python simulated_app.py
"""

import os
import subprocess
import sys
import time
from pathlib import Path

import psutil

HERE = Path(__file__).parent
TARGET = "simulated_app.py"
LAUNCH_SCRIPT = HERE / "simulated_launch.py"


def target_running() -> bool:
    """Return True if a process running simulated_app.py exists."""
    target = TARGET.lower()

    for proc in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            if proc.info["pid"] == os.getpid():
                continue

            # cmdline can be None for processes we are not allowed to inspect.
            cmdline = proc.info.get("cmdline") or []

            # Compare the executable/script name instead of doing a substring
            # match, so a command like `python -c "print('simulated_app.py')"`
            # does not count as the target app.
            if any(Path(part).name.lower() == target for part in cmdline):
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue

    return False


def launch_program() -> subprocess.Popen:
    """Start the second program without blocking the watcher."""
    return subprocess.Popen([sys.executable, str(LAUNCH_SCRIPT)])


def main() -> None:
    print(f"Watching for {TARGET} ... (Ctrl+C to stop)")
    already_launched = False

    while True:
        running = target_running()

        if running and not already_launched:
            print("Target detected - launching!")
            launch_program()
            already_launched = True
        elif not running:
            already_launched = False

        time.sleep(0.5)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nWatcher stopped.")
