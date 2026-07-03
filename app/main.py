"""Command-line entry point.

Runs the start-up sequence and launches the graphical interface. Pass
``--check`` to only run the bootstrap and print a status report (no GUI),
which is handy for CI and quick health checks.

Usage:
    python -m app.main            # launch the GUI
    python -m app.main --check    # bootstrap only, print status, exit
"""

from __future__ import annotations

import sys

from app import config
from app.bootstrap import BootstrapError, bootstrap


def _print_status(database) -> None:
    """Print a short bootstrap status report."""
    schema_version = database.connection.execute(
        "SELECT COALESCE(MAX(version), 0) AS v FROM schema_migrations"
    ).fetchone()["v"]
    print(f"{config.APP_NAME} v{config.APP_VERSION}")
    print(f"  Database:       {database.path}")
    print(f"  Schema version: {schema_version}")
    print(f"  Log file:       {config.LOG_FILE}")


def main(argv: list[str] | None = None) -> int:
    """Bootstrap the application and either report status or launch the GUI."""
    args = sys.argv[1:] if argv is None else argv
    check_only = "--check" in args

    try:
        database = bootstrap()
    except BootstrapError as exc:
        print(f"Startup failed: {exc}", file=sys.stderr)
        return 1

    try:
        if check_only:
            _print_status(database)
            print("  Status:         bootstrap OK (--check, no GUI).")
            return 0

        # Import here so headless/CLI use does not require Qt.
        from app.ui.app import run_gui

        return run_gui(database)
    finally:
        database.close()


if __name__ == "__main__":
    raise SystemExit(main())
