"""logger.py — Structured logging utility for automation scripts.

Usage:
    from automations.utils.logger import Logger
    log = Logger("script_name")
    log.info("Something happened")
    log.warning("Careful!")
    log.error("Something broke")
    log.debug("Debug info")
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path


class Logger:
    """Simple structured logger with file + console output."""

    LOG_DIR = "automations/utils/logs"

    def __init__(self, name: str, log_to_file: bool = True, level: str = "info"):
        self.name = name
        self.log_to_file = log_to_file
        self.level = level
        self.levels = {"debug": 0, "info": 1, "warning": 2, "error": 3}
        self.current_level = self.levels.get(level, 1)

        if log_to_file:
            os.makedirs(self.LOG_DIR, exist_ok=True)
            self.log_file = Path(self.LOG_DIR) / f"{name}.log"

    def _format(self, level: str, message: str, **kwargs) -> dict:
        entry = {
            "timestamp": datetime.now().isoformat(),
            "level": level.upper(),
            "script": self.name,
            "message": message,
        }
        if kwargs:
            entry.update(kwargs)
        return entry

    def _should_log(self, level: str) -> bool:
        return self.levels.get(level, 1) >= self.current_level

    def _write(self, entry: dict):
        # Console output
        icons = {"INFO": "ℹ️", "WARNING": "⚠️", "ERROR": "❌", "DEBUG": "🔍"}
        icon = icons.get(entry["level"], "📝")
        print(f"{icon} [{entry['timestamp'][11:19]}] {entry['message']}", file=sys.stderr)

        # File output
        if self.log_to_file:
            with open(self.log_file, "a") as f:
                f.write(json.dumps(entry) + "\n")

    def debug(self, message: str, **kwargs):
        if self._should_log("debug"):
            self._write(self._format("debug", message, **kwargs))

    def info(self, message: str, **kwargs):
        if self._should_log("info"):
            self._write(self._format("info", message, **kwargs))

    def warning(self, message: str, **kwargs):
        if self._should_log("warning"):
            self._write(self._format("warning", message, **kwargs))

    def error(self, message: str, **kwargs):
        if self._should_log("error"):
            self._write(self._format("error", message, **kwargs))


# Quick standalone logging function for bash/scripts calling python
def log_message(script: str, message: str, level: str = "info"):
    """One-shot logging function for shell script integration."""
    logger = Logger(script, log_to_file=True)
    getattr(logger, level)(message)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Structured logger")
    parser.add_argument("script", help="Script name")
    parser.add_argument("message", help="Log message")
    parser.add_argument("--level", "-l", default="info", choices=["debug", "info", "warning", "error"])
    parser.add_argument("--json", "-j", action="store_true", help="Output as JSON only")
    args = parser.parse_args()

    if args.json:
        entry = {
            "timestamp": datetime.now().isoformat(),
            "level": args.level.upper(),
            "script": args.script,
            "message": args.message,
        }
        print(json.dumps(entry))
    else:
        log_message(args.script, args.message, args.level)
