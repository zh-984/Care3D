"""Check packaged initialization and graceful exit using isolated settings.

This exercises --smoke-test, which does not display the control panel or overlay.
It verifies packaging/startup, not real mouse input, game compatibility or efficacy.
"""

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile


def main():
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(errors="backslashreplace")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("exe", nargs="?", default="dist/Care3D_v2.exe")
    parser.add_argument("--timeout", type=float, default=60,
                        help="Startup/exit deadline in seconds (default: 60)")
    parser.add_argument("--optional-features", action="store_true",
                        help="Initialize with all optional modules enabled, including large fonts")
    args = parser.parse_args()
    if args.timeout <= 0:
        parser.error("Timeout must be positive")
    executable = Path(args.exe).resolve()
    if not executable.is_file():
        parser.error(f"Executable not found: {executable}")
    with tempfile.TemporaryDirectory(prefix="care3d-exe-check-") as temporary:
        environment = dict(os.environ, LOCALAPPDATA=temporary)
        directory = Path(temporary) / "Care3D"
        if args.optional_features:
            directory.mkdir()
            settings = dict(config_version=4, active_profile="balanced", font_scale=150,
                            edge_triangles_enabled=True, reference_columns_enabled=True,
                            safe_zones=[dict(x=.16, y=.78, w=.68, h=.18, label="Subtitle")])
            for key in ("game_library_enabled", "game_auto_switch_enabled", "safe_zones_enabled",
                        "comfort_enabled", "guide_enabled", "layout_enabled", "gamepad_enabled",
                        "gamepad_tuning_enabled", "controls_enabled", "controls_gamepad_enabled",
                        "controls_comfort_hold", "accessibility_enabled", "session_tools_enabled",
                        "session_recording_enabled", "break_reminder_enabled", "game_assistant_enabled"):
                settings[key] = True
            (directory / "config.json").write_text(json.dumps(settings), encoding="utf-8")
        output_path = Path(temporary) / "process-output.log"
        with output_path.open("wb") as output:
            process = subprocess.Popen([str(executable), "--smoke-test"], env=environment,
                                       stdout=output, stderr=subprocess.STDOUT)
            try:
                returncode = process.wait(timeout=args.timeout)
            except subprocess.TimeoutExpired:
                # Only terminate the process tree created by this test.
                subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
                process.wait(timeout=10)
                returncode = None
        if returncode != 0:
            for label, path in (("Application log", directory / "care3d.log"),
                                ("Process output", output_path)):
                content = path.read_text(encoding="utf-8", errors="replace") if path.exists() else "(not created)"
                print(f"{label}:\n{content[-8000:]}", file=sys.stderr)
            if returncode is None:
                raise RuntimeError(f"Packaged startup timed out after {args.timeout:g}s")
            raise RuntimeError(f"Executable exited with code {returncode}")
        log = (directory / "care3d.log").read_text(encoding="utf-8")
        if "UI event loop ready" not in log or "Shutdown complete" not in log:
            raise RuntimeError("Startup or shutdown checkpoint missing")
        if not (directory / "config.json").is_file() or (directory / "care3d.lock").exists():
            raise RuntimeError("Configuration save or instance cleanup failed")
    print("Packaged initialization, configuration save and shutdown passed" + (" (optional features enabled)." if args.optional_features else "."))


if __name__ == "__main__":
    main()
