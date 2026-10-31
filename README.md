# Automate Everything

An open-source automation tool: define rules that watch for conditions
(processes, files, time) and run actions (launch programs, run commands)
when they're met. Windows-first, Linux planned.

## Status

Early development. The process watcher + launcher backend and a NiceGUI
test console are working. The rule editor and drag-and-drop UI are next.

## Architecture

- `watch.py` — process detection and launch logic
- `automation_service.py` — threaded backend; owns the watcher loop,
  subprocess management, and an in-memory event log
- `app.py` — NiceGUI console; polls the service for snapshots, never
  touches `psutil` or `subprocess` directly
- `simulated_app.py` / `simulated_launch.py` — stand-ins for testing

## Requirements

- Python 3.10+
- `pip install psutil nicegui`

## Run

    python app.py

Open http://localhost:8080. Click **Run demo** to start the watcher and
the simulated target; the watcher launches `simulated_launch.py` when it
detects the target process.

CLI-only equivalent: `python watch.py`, then run `python simulated_app.py`
in another terminal.

## Roadmap

1. Rules as data (`rules.json`) with a condition/action registry
2. Rule editor in the UI
3. Drag-and-drop rule builder
4. Linux support