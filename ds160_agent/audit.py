from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any


def log_event(output_root: Path, event: str, details: dict[str, Any]) -> Path:
    """Append a privacy-conscious JSONL audit event.

    Events intentionally store counts and case identifiers, not full DS-160
    answers.
    """
    log_dir = output_root / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    path = log_dir / f"ds160-{datetime.now(timezone.utc).strftime('%Y-%m-%d')}.jsonl"
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "event": event,
        **details,
    }
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return path


def read_recent_events(output_root: Path, limit: int = 25) -> list[dict[str, Any]]:
    log_dir = output_root / "logs"
    if not log_dir.is_dir():
        return []
    paths = sorted(log_dir.glob("ds160-*.jsonl"), reverse=True)
    events: list[dict[str, Any]] = []
    for path in paths:
        for line in reversed(path.read_text(encoding="utf-8").splitlines()):
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue
            if len(events) >= limit:
                return events
    return events
