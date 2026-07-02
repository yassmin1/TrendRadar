"""Cost controls for paid API calls."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class DailyBudgetExceeded(RuntimeError):
    """Raised when a daily API request budget has been reached."""


class DailyRequestBudget:
    """Track daily request usage in a small JSON file."""

    def __init__(self, name: str, daily_limit: int, state_dir: str | Path = "data/state") -> None:
        self.name = name
        self.daily_limit = max(daily_limit, 0)
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.path = self.state_dir / f"{name}_daily_budget.json"

    def consume(self, amount: int = 1) -> None:
        """Consume budget before a paid request."""
        state = self._load()
        today = datetime.now(UTC).date().isoformat()
        if state.get("date") != today:
            state = {"date": today, "used": 0}
        if state["used"] + amount > self.daily_limit:
            raise DailyBudgetExceeded(f"{self.name} daily budget reached: {state['used']}/{self.daily_limit}")
        state["used"] += amount
        self.path.write_text(json.dumps(state, indent=2), encoding="utf-8")

    def remaining(self) -> int:
        """Return remaining requests for today."""
        state = self._load()
        today = datetime.now(UTC).date().isoformat()
        if state.get("date") != today:
            return self.daily_limit
        return max(self.daily_limit - int(state.get("used", 0)), 0)

    def _load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"date": datetime.now(UTC).date().isoformat(), "used": 0}
        return json.loads(self.path.read_text(encoding="utf-8"))


class JsonResponseCache:
    """File cache for API responses."""

    def __init__(self, cache_dir: str | Path = "data/cache") -> None:
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def load(self, namespace: str, key: dict[str, Any], ttl_minutes: int) -> list[dict[str, Any]] | None:
        """Return cached pages if they exist and are fresh."""
        path = self._path(namespace, key)
        if not path.exists() or ttl_minutes <= 0:
            return None
        payload = json.loads(path.read_text(encoding="utf-8"))
        created_at = datetime.fromisoformat(payload["created_at"])
        age_minutes = (datetime.now(UTC) - created_at).total_seconds() / 60
        if age_minutes > ttl_minutes:
            return None
        pages = payload.get("pages", [])
        return pages if isinstance(pages, list) else None

    def save(self, namespace: str, key: dict[str, Any], pages: list[dict[str, Any]]) -> Path:
        """Save response pages to the cache."""
        path = self._path(namespace, key)
        path.write_text(
            json.dumps({"created_at": datetime.now(UTC).isoformat(), "pages": pages}, indent=2),
            encoding="utf-8",
        )
        return path

    def _path(self, namespace: str, key: dict[str, Any]) -> Path:
        digest = hashlib.sha256(json.dumps(key, sort_keys=True, default=str).encode("utf-8")).hexdigest()[:24]
        return self.cache_dir / f"{namespace}_{digest}.json"
