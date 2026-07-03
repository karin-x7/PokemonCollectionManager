"""Command-line entry point.

Until the GUI lands in Step 2, running the application performs the full
start-up sequence and prints a short status report. This makes the foundation
runnable and verifiable on its own.

Usage:
    python -m app.main
"""

from __future__ import annotations

import sys

from app import config
from app.bootstrap import BootstrapError, bootstrap


def main() -> int:
    """Run the bootstrap sequence and report the result.

    Returns:
        Process exit code (0 on success, 1 on failure).
    """
    try:
        database = bootstrap()
    except BootstrapError as exc:
        print(f"Startup failed: {exc}", file=sys.stderr)
        return 1

    try:
        version_row = database.connection.execute(
            "SELECT COALESCE(MAX(version), 0) AS v FROM schema_migrations"
        ).fetchone()
        schema_version = version_row["v"]

        print(f"{config.APP_NAME} v{config.APP_VERSION}")
        print(f"  Database:       {database.path}")
        print(f"  Schema version: {schema_version}")
        print(f"  Log file:       {config.LOG_FILE}")
        print("  Status:         foundation ready (GUI arrives in Step 2).")
        return 0
    finally:
        database.close()


if __name__ == "__main__":
    raise SystemExit(main())
