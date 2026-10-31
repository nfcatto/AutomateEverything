"""NiceGUI test console for the process watcher.

Run with:

    python app.py

Then open http://localhost:8080. Click "Run demo" for a one-click test:
the watcher starts, the simulated app opens, and the watcher launches
simulated_launch.py when it detects the target process.
"""

from __future__ import annotations

import os

from nicegui import app, ui

from automation_service import APP_SCRIPT, LAUNCH_SCRIPT, AutomationService

service = AutomationService()
app.on_shutdown(service.shutdown)


def _badge(badge, text: str, color: str) -> None:
    badge.set_text(text)
    badge.props(f"color={color}")


@ui.page("/")
def index() -> None:
    ui.dark_mode(True)
    ui.add_css(
        """
        body { background: #0b1120; }
        .lab-card {
            background: rgba(15, 23, 42, 0.86);
            border: 1px solid #1e293b;
            border-radius: 16px;
        }
        .mono { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }
        """
    )

    with ui.header().classes("items-center justify-between px-6 py-3").style(
        "background: #0f172a; border-bottom: 1px solid #1e293b"
    ):
        with ui.row().classes("items-center gap-3"):
            ui.icon("precision_manufacturing").classes("text-2xl").style(
                "color: #34d399"
            )
            with ui.column().classes("gap-0"):
                ui.label("Automaton Everything").classes(
                    "text-lg font-semibold leading-tight"
                )
                ui.label("Process watcher test console").classes("text-xs").style(
                    "color: #94a3b8"
                )
        header_badge = ui.badge("WATCHER STOPPED").props("color=grey-7")

    with ui.column().classes("w-full max-w-5xl mx-auto p-4 md:p-6 gap-4"):
        ui.label(
            "Start the watcher, then start the simulated app. When the target "
            "process appears, the watcher launches simulated_launch.py automatically."
        ).classes("text-sm").style("color: #94a3b8")

        with ui.row().classes("w-full gap-4 items-stretch"):
            # ------------------------------------------------------- watcher card
            with ui.card().classes("lab-card flex-1 min-w-[300px] p-5 gap-3"):
                with ui.row().classes("items-center justify-between w-full"):
                    with ui.row().classes("items-center gap-2"):
                        ui.icon("visibility").style("color: #34d399")
                        ui.label("Watcher").classes("text-base font-semibold")
                    watch_badge = ui.badge("STOPPED").props("color=grey-7")

                with ui.grid(columns=2).classes("w-full gap-y-2 text-sm"):
                    ui.label("Target process").style("color: #94a3b8")
                    target_badge = ui.badge("not detected").props("color=grey-7")

                    ui.label("Launches").style("color: #94a3b8")
                    launch_label = ui.label("0").classes("mono text-sm")

                    ui.label("Poll interval").style("color: #94a3b8")
                    poll_input = (
                        ui.number(
                            value=0.5,
                            min=0.1,
                            max=5.0,
                            step=0.1,
                            format="%.1f",
                        )
                        .props("outlined dense dark suffix=s")
                        .classes("w-28")
                    )

                with ui.row().classes("w-full gap-2"):
                    watch_button = (
                        ui.button("Start watching", icon="visibility")
                        .props("unelevated color=primary")
                        .classes("flex-1")
                    )
                    demo_button = (
                        ui.button("Run demo", icon="play_arrow")
                        .props("unelevated color=positive")
                        .classes("flex-1")
                    )

                manual_button = ui.button(
                    "Launch program now", icon="rocket_launch"
                ).props("flat color=secondary")

            # ----------------------------------------------------- simulator card
            with ui.card().classes("lab-card flex-1 min-w-[300px] p-5 gap-3"):
                with ui.row().classes("items-center justify-between w-full"):
                    with ui.row().classes("items-center gap-2"):
                        ui.icon("terminal").style("color: #38bdf8")
                        ui.label("Simulated target").classes("text-base font-semibold")
                    sim_badge = ui.badge("idle").props("color=grey-7")

                ui.label("Target script").classes("text-xs uppercase tracking-wide").style(
                    "color: #64748b"
                )
                ui.label(str(APP_SCRIPT)).classes("mono text-xs break-all").style(
                    "color: #cbd5e1"
                )

                with ui.row().classes("items-end gap-2 w-full"):
                    duration_input = (
                        ui.number(value=8, min=1, max=300, step=1, format="%d")
                        .props("outlined dense dark label=Duration suffix=s")
                        .classes("w-36")
                    )
                    start_sim_button = (
                        ui.button("Start simulator", icon="play_arrow")
                        .props("unelevated color=primary")
                        .classes("flex-1")
                    )
                    stop_sim_button = (
                        ui.button(icon="stop")
                        .props("flat color=negative round")
                        .tooltip("Stop the simulated app")
                    )

                ui.separator()

                ui.label("Launched program").classes(
                    "text-xs uppercase tracking-wide"
                ).style("color: #64748b")
                ui.label(str(LAUNCH_SCRIPT)).classes("mono text-xs break-all").style(
                    "color: #cbd5e1"
                )
                ui.label(
                    "The watcher fires this once per appearance of the target."
                ).classes("text-xs").style("color: #64748b")

        # ------------------------------------------------------------- log card
        with ui.card().classes("lab-card w-full p-0 overflow-hidden"):
            with ui.row().classes(
                "w-full items-center justify-between px-5 py-3"
            ).style("border-bottom: 1px solid #1e293b"):
                with ui.row().classes("items-center gap-2"):
                    ui.icon("subject").style("color: #a78bfa")
                    ui.label("Event log").classes("font-semibold")
                clear_button = ui.button(icon="delete_sweep").props(
                    "flat dense color=grey-5"
                ).tooltip("Clear the log")

            log_view = ui.log(max_lines=400).classes(
                "w-full h-72 mono text-xs px-5 py-3"
            ).style("background: #020617")

        ui.label(
            "CLI equivalent: python watch.py   |   Simulator: python simulated_app.py 10"
        ).classes("mono text-xs").style("color: #475569")

    # ---------------------------------------------------------------- callbacks
    cursor = 0

    def refresh() -> None:
        nonlocal cursor

        snapshot = service.snapshot()

        _badge(
            header_badge,
            "WATCHER RUNNING" if snapshot.watching else "WATCHER STOPPED",
            "positive" if snapshot.watching else "grey-7",
        )
        _badge(
            watch_badge,
            "WATCHING" if snapshot.watching else "STOPPED",
            "positive" if snapshot.watching else "grey-7",
        )
        _badge(
            target_badge,
            "detected" if snapshot.target_running else "not detected",
            "positive" if snapshot.target_running else "grey-7",
        )
        _badge(
            sim_badge,
            f"running (pid {snapshot.simulator_pid})"
            if snapshot.simulator_pid is not None
            else "idle",
            "info" if snapshot.simulator_pid is not None else "grey-7",
        )

        launch_label.set_text(str(snapshot.launches))
        watch_button.set_text(
            "Stop watching" if snapshot.watching else "Start watching"
        )
        start_sim_button.set_enabled(snapshot.simulator_pid is None)
        stop_sim_button.set_enabled(snapshot.simulator_pid is not None)

        entries, cursor = service.logs_since(cursor)
        for entry in entries:
            log_view.push(
                f"{entry.when}  {entry.level.upper():<7}  {entry.message}"
            )

    def toggle_watcher() -> None:
        if service.snapshot().watching:
            service.stop_watching()
        else:
            service.start_watching()
        refresh()

    def run_demo() -> None:
        if not service.snapshot().watching:
            service.start_watching()

        if service.start_simulator(duration_input.value or 8):
            ui.notify("Demo started - watch for launch activity", type="positive")
        else:
            ui.notify("Simulator is already running", type="info")
        refresh()

    def start_simulator() -> None:
        if service.start_simulator(duration_input.value or 8):
            ui.notify("Simulated app started", type="positive")
        else:
            ui.notify("Simulator is already running", type="warning")
        refresh()

    def stop_simulator() -> None:
        if service.stop_simulator():
            ui.notify("Simulator stopped", type="warning")
        else:
            ui.notify("Simulator is not running", type="info")
        refresh()

    def manual_launch() -> None:
        try:
            proc = service.launch_now()
        except Exception as exc:
            ui.notify(f"Launch failed: {exc}", type="negative")
            return
        ui.notify(f"Launched simulated_launch.py (pid {proc.pid})", type="positive")
        refresh()

    def clear_log() -> None:
        nonlocal cursor
        cursor = service.clear_logs()
        log_view.clear()

    def change_interval(event) -> None:
        service.set_poll_interval(event.value)

    watch_button.on_click(toggle_watcher)
    demo_button.on_click(run_demo)
    start_sim_button.on_click(start_simulator)
    stop_sim_button.on_click(stop_simulator)
    manual_button.on_click(manual_launch)
    clear_button.on_click(clear_log)
    poll_input.on_value_change(change_interval)

    refresh()
    ui.timer(0.25, refresh)


if __name__ in {"__main__", "__mp_main__"}:
    ui.run(
        title="Automaton Everything - Watcher Lab",
        port=8080,
        reload=False,
        show=os.environ.get("AUTOMATON_SHOW", "1") != "0",
    )
