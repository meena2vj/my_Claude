"""Append-only audit log of who accessed which tab/action and when.

Local-demo implementation: a gitignored CSV under logs/. In a real deployment
this would write to a centralized, tamper-evident audit store instead.
"""
import csv
from datetime import datetime, timezone
from pathlib import Path

LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_FILE = LOG_DIR / "audit.csv"
FIELDS = ["timestamp_utc", "username", "role", "action"]


def log_event(username: str, role: str, action: str) -> None:
    LOG_DIR.mkdir(exist_ok=True)
    is_new = not LOG_FILE.exists()
    with open(LOG_FILE, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        if is_new:
            writer.writeheader()
        writer.writerow({
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "username": username,
            "role": role,
            "action": action,
        })


def read_events(limit: int = 200) -> list[dict]:
    if not LOG_FILE.exists():
        return []
    with open(LOG_FILE, newline="") as f:
        rows = list(csv.DictReader(f))
    return rows[-limit:]
