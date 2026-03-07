"""launchd plist generator — creates macOS Launch Agent for background operation."""
from __future__ import annotations

from pathlib import Path
from string import Template


_PLIST_TEMPLATE = Template("""\
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>$label</string>
    <key>ProgramArguments</key>
    <array>
        <string>$python_path</string>
        <string>-m</string>
        <string>concierge.background.runner</string>
    </array>
    <key>WorkingDirectory</key>
    <string>$working_dir</string>
    <key>StartInterval</key>
    <integer>$interval_seconds</integer>
    <key>RunAtLoad</key>
    <$run_at_load/>
    <key>StandardOutPath</key>
    <string>$log_dir/concierge-bg.log</string>
    <key>StandardErrorPath</key>
    <string>$log_dir/concierge-bg-error.log</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>$path_env</string>
    </dict>
</dict>
</plist>
""")


def generate_plist(
    label: str = "com.bureau.concierge",
    working_dir: str | Path = ".",
    python_path: str = "/usr/bin/env python3",
    interval_seconds: int = 3600,  # 1 hour default
    run_at_load: bool = True,
    log_dir: str | Path | None = None,
    path_env: str | None = None,
) -> str:
    """Generate a launchd plist XML string for the Concierge background runner.

    Args:
        label: Bundle identifier for the launch agent
        working_dir: Working directory for the daemon
        python_path: Path to Python interpreter
        interval_seconds: How often to run (in seconds)
        run_at_load: Whether to run immediately when loaded
        log_dir: Directory for log files (defaults to ~/Library/Logs/bureau)
        path_env: PATH environment variable value
    """
    if log_dir is None:
        log_dir = Path.home() / "Library" / "Logs" / "bureau"
    if path_env is None:
        path_env = "/usr/local/bin:/usr/bin:/bin"

    return _PLIST_TEMPLATE.substitute(
        label=label,
        working_dir=str(working_dir),
        python_path=python_path,
        interval_seconds=interval_seconds,
        run_at_load="true" if run_at_load else "false",
        log_dir=str(log_dir),
        path_env=path_env,
    )


def install_plist(
    plist_content: str,
    label: str = "com.bureau.concierge",
) -> Path:
    """Write plist to ~/Library/LaunchAgents/ and return the path.

    Does NOT load the agent — caller should run:
        launchctl load <path>
    """
    agents_dir = Path.home() / "Library" / "LaunchAgents"
    agents_dir.mkdir(parents=True, exist_ok=True)

    plist_path = agents_dir / f"{label}.plist"
    plist_path.write_text(plist_content)
    return plist_path
