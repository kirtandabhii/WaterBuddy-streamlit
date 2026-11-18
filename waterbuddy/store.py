"""What WaterBuddy keeps between visits, as plain JSON for the browser's local storage.

Nothing leaves the device: the app hands this JSON to a tiny component that writes it to the
browser's localStorage, and reads it back on the next visit.
"""

from dataclasses import dataclass, field
from datetime import date, datetime

from waterbuddy.drinks import DRINKS
from waterbuddy.tracker import Drink

VERSION = 1
KEEP_DAYS = 120   # older days are dropped so the saved data stays small


@dataclass
class DayRecord:
    goal: int
    drinks: list[Drink] = field(default_factory=list)

    @property
    def total(self) -> int:
        return sum(d.ml for d in self.drinks)

    @property
    def met(self) -> bool:
        return self.goal > 0 and self.total >= self.goal


@dataclass
class Saved:
    """Everything that survives a reload."""
    age: str | None = None
    goal_slider: int = 2000
    goal_sure: bool = False
    theme: str = "spring"
    day: date | None = None
    drinks: list[Drink] = field(default_factory=list)
    celebrated: bool = False
    found: list[str] = field(default_factory=list)
    history: dict[date, DayRecord] = field(default_factory=dict)
    badges: dict[str, date] = field(default_factory=dict)


def _drink_out(d: Drink) -> dict:
    return {"ml": d.ml, "at": d.at.isoformat(timespec="seconds"), "kind": d.kind}


def _drink_in(raw: dict) -> Drink | None:
    try:
        ml = int(raw["ml"])
        at = datetime.fromisoformat(str(raw["at"]))
    except (KeyError, TypeError, ValueError):
        return None
    if ml <= 0:
        return None
    kind = raw.get("kind", "water")
    return Drink(ml, at, kind if kind in DRINKS else "water")


def to_json(s: Saved) -> dict:
    history = dict(sorted(s.history.items())[-KEEP_DAYS:])
    return {
        "v": VERSION,
        "profile": {"age": s.age, "goal_slider": s.goal_slider, "goal_sure": s.goal_sure, "theme": s.theme},
        "day": s.day.isoformat() if s.day else None,
        "drinks": [_drink_out(d) for d in s.drinks],
        "celebrated": s.celebrated,
        "found": list(s.found),
        "history": {d.isoformat(): {"goal": r.goal, "drinks": [_drink_out(x) for x in r.drinks]}
                    for d, r in history.items()},
        "badges": {k: v.isoformat() for k, v in s.badges.items()},
    }


def from_json(raw: object) -> Saved:
    """Read saved data defensively: anything missing or damaged falls back to a fresh default."""
    s = Saved()
    if not isinstance(raw, dict) or raw.get("v") != VERSION:
        return s
    profile = raw.get("profile") or {}
    if isinstance(profile, dict):
        s.age = profile.get("age") if isinstance(profile.get("age"), str) else None
        try:
            s.goal_slider = int(profile.get("goal_slider", 2000))
        except (TypeError, ValueError):
            pass
        s.goal_sure = bool(profile.get("goal_sure", False))
        s.theme = str(profile.get("theme") or "spring")
    try:
        s.day = date.fromisoformat(raw["day"]) if raw.get("day") else None
    except (TypeError, ValueError):
        s.day = None
    s.drinks = [d for d in (_drink_in(x) for x in raw.get("drinks") or [] if isinstance(x, dict)) if d]
    s.celebrated = bool(raw.get("celebrated", False))
    s.found = [str(x) for x in raw.get("found") or []]
    for key, rec in (raw.get("history") or {}).items():
        try:
            day = date.fromisoformat(key)
            goal = int(rec.get("goal", 0))
        except (TypeError, ValueError, AttributeError):
            continue
        drinks = [d for d in (_drink_in(x) for x in rec.get("drinks") or [] if isinstance(x, dict)) if d]
        s.history[day] = DayRecord(goal, drinks)
    for key, when in (raw.get("badges") or {}).items():
        try:
            s.badges[str(key)] = date.fromisoformat(when)
        except (TypeError, ValueError):
            continue
    return s


def roll_over(s: Saved, today: date, goal: int) -> bool:
    """If the saved day is in the past, file its drinks in history and start today. True if it rolled."""
    if s.day == today:
        return False
    if s.day is not None and s.drinks:
        s.history[s.day] = DayRecord(goal, list(s.drinks))
    s.day = today
    s.drinks = []
    s.celebrated = False
    s.found = []
    return True
