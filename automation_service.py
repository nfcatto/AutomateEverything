"""Threaded watcher/launcher backend for the NiceGUI test console.

The UI never touches psutil or subprocess directly. It calls this service and
polls snapshots, so the watcher can keep running without blocking the server.
"""

from __future__ import annotations

import subprocess
import sys
import threading
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from watch import LAUNCH_SCRIPT, TARGET, target_running

HERE = Path(__file__).resolve().parent
APP_SCRIPT = HERE / TARGET


@dataclass(frozen=True)
class Snapshot:
    """A consistent view of the service state for the UI."""

    watching: bool
    target_running: bool
    launches: int
    simulator_pid: int | None
    poll_interval: float


@dataclass(frozen=True)
class LogEntry:
    seq: int
    when: str
    level: str
    message: str


class AutomationService:
    def __init__(self, poll_interval: float = 0.5) -> None:
        self._lock = threading.RLock()
        self._stop_event = threading.Event()
        self._watch_thread: threading.Thread | None = None
        self._watching = False
        self._target_running = False
        self._launches = 0
        self._poll_interval = self._clamp_interval(poll_interval)
        self._simulator: subprocess.Popen[str] | None = None
        self._launched: list[subprocess.Popen[str]] = []
        self._logs: deque[LogEntry] = deque(maxlen=500)
        self._log_seq = 0

    # ------------------------------------------------------------------ state
    def snapshot(self) -> Snapshot:
        with self._lock:
            simulator = self._simulator
            simulator_pid = (
                simulator.pid
                if simulator is not None and simulator.poll() is None
                else None
            )
            return Snapshot(
                watching=self._watching,
                target_running=self._target_running,
                launches=self._launches,
                simulator_pid=simulator_pid,
                poll_interval=self._poll_interval,
            )

    def set_poll_interval(self, seconds: float) -> float:
        with self._lock:
            self._poll_interval = self._clamp_interval(seconds)
            return self._poll_interval

    @staticmethod
    def _clamp_interval(seconds: float) -> float:
        try:
            value = float(seconds)
        except (TypeError, ValueError):
            value = 0.5
        return max(0.1, min(10.0, value))

    # --------------------------------------------------------------- watching
    def start_watching(self) -> bool:
        with self._lock:
            if self._watch_thread is not None and self._watch_thread.is_alive():
                return False
            self._stop_event.clear()
            self._watching = True
            thread = threading.Thread(
                target=self._watch_loop,
                name="automaton-watcher",
                daemon=True,
            )
            self._watch_thread = thread

        thread.start()
        self.log("Watcher started", "success")
        return True

    def stop_watching(self) -> bool:
        with self._lock:
            thread = self._watch_thread
            if thread is None or not thread.is_alive():
                self._watching = False
                return False
            self._stop_event.set()

        self.log("Stopping watcher...", "warn")
        thread.join(timeout=2.0)
        return True

    def _watch_loop(self) -> None:
        already_launched = False
        self.log(f"Looking for {TARGET} every poll interval", "info")

        try:
            while not self._stop_event.is_set():
                try:
                    running = target_running()
                except Exception as exc:  # keep the watcher alive on scan errors
                    self.log(f"Process scan failed: {exc}", "error")
                    running = False

                with self._lock:
                    changed = running != self._target_running
                    self._target_running = running
                    interval = self._poll_interval

                if changed:
                    self.log(
                        f"Target detected: {TARGET}" if running else "Target closed",
                        "success" if running else "muted",
                    )

                if running and not already_launched:
                    self.log("Target detected - launching simulated_launch.py", "launch")
                    try:
                        proc = self._spawn_launch()
                    except Exception as exc:
                        self.log(f"Launch failed: {exc}", "error")
                    else:
                        with self._lock:
                            self._launches += 1
                        self.log(f"Launched simulated_launch.py (pid {proc.pid})", "launch")
                        already_launched = True
                elif not running:
                    already_launched = False

                self._stop_event.wait(interval)
        finally:
            with self._lock:
                self._watching = False
                self._target_running = target_running()
            self.log("Watcher stopped", "muted")

    # ---------------------------------------------------------------- launching
    def launch_now(self) -> subprocess.Popen[str]:
        """Launch the target program once, without waiting for detection."""
        proc = self._spawn_launch()
        with self._lock:
            self._launches += 1
        self.log(f"Manual launch of simulated_launch.py (pid {proc.pid})", "launch")
        return proc

    def _spawn_launch(self) -> subprocess.Popen[str]:
        proc = subprocess.Popen(
            [sys.executable, str(LAUNCH_SCRIPT)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )
        with self._lock:
            self._launched = [p for p in self._launched if p.poll() is None]
            self._launched.append(proc)

        threading.Thread(
            target=self._read_output,
            args=(proc, "[launch]"),
            name=f"automaton-launch-{proc.pid}",
            daemon=True,
        ).start()
        return proc

    # --------------------------------------------------------------- simulator
    def start_simulator(self, duration: float = 8) -> bool:
        with self._lock:
            if self._simulator is not None and self._simulator.poll() is None:
                return False

        try:
            seconds = max(1, min(300, int(duration)))
        except (TypeError, ValueError):
            seconds = 8

        proc = subprocess.Popen(
            [sys.executable, str(APP_SCRIPT), str(seconds)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )
        with self._lock:
            self._simulator = proc

        self.log(f"Simulator started (pid {proc.pid}, {seconds}s)", "sim")
        threading.Thread(
            target=self._watch_simulator,
            args=(proc,),
            name=f"automaton-simulator-{proc.pid}",
            daemon=True,
        ).start()
        return True

    def stop_simulator(self) -> bool:
        with self._lock:
            proc = self._simulator
        if proc is None or proc.poll() is not None:
            return False

        self.log("Stopping simulator...", "warn")
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()
        return True

    def _watch_simulator(self, proc: subprocess.Popen[str]) -> None:
        self._read_output(proc, "[app]")
        with self._lock:
            if self._simulator is proc:
                self._simulator = None

    def _read_output(self, proc: subprocess.Popen[str], prefix: str) -> None:
        try:
            if proc.stdout is not None:
                for line in proc.stdout:
                    text = line.strip()
                    if text:
                        self.log(f"{prefix} {text}", "muted")
        finally:
            code = proc.wait()
            self.log(f"{prefix} exited (code {code})", "muted")

    # -------------------------------------------------------------------- logs
    def log(self, message: str, level: str = "info") -> None:
        stamp = datetime.now().strftime("%H:%M:%S")
        with self._lock:
            self._log_seq += 1
            self._logs.append(LogEntry(self._log_seq, stamp, level, message))

    def logs_since(self, seq: int) -> tuple[list[LogEntry], int]:
        with self._lock:
            entries = [entry for entry in self._logs if entry.seq > seq]
            return entries, self._log_seq

    def clear_logs(self) -> int:
        with self._lock:
            self._logs.clear()
            return self._log_seq

    # ----------------------------------------------------------------- cleanup
    def shutdown(self) -> None:
        self._stop_event.set()
        self.stop_simulator()

        with self._lock:
            processes = [*self._launched]
            if self._simulator is not None:
                processes.append(self._simulator)

        for proc in processes:
            if proc.poll() is None:
                proc.terminate()
