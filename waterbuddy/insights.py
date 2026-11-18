"""Patterns across days: the week, the month, the time of day and favourite drinks.

All of it is descriptive and kind. Nothing here counts streaks or treats a missed day as a loss
(WaterBuddy's safety rules), and nothing rewards drinking past the goal.
"""

from dataclasses import dataclass
from datetime import date, timedelta

from waterbuddy.drinks import by_kind, drink_type
from waterbuddy.store import DayRecord
from waterbuddy.tracker import Drink

PARTS = (("Morning", 5, 12), ("Afternoon", 12, 17), ("Evening", 17, 22), ("Night", 22, 29))


@dataclass(frozen=True)
class DayPoint:
    day: date
    total: int
    goal: int

    @property
    def met(self) -> bool:
        return self.goal > 0 and self.total >= self.goal


def all_days(history: dict[date, DayRecord], today: date, today_record: DayRecord) -> dict[date, DayRecord]:
    days = dict(history)
    days[today] = today_record
    return days


def last_n(days: dict[date, DayRecord], today: date, n: int, default_goal: int) -> list[DayPoint]:
    """The last n calendar days ending today, including days with nothing logged."""
    out = []
    for i in range(n - 1, -1, -1):
        d = today - timedelta(days=i)
        rec = days.get(d)
        out.append(DayPoint(d, rec.total if rec else 0, rec.goal if rec else default_goal))
    return out


def part_of_day(hour: int) -> str:
    h = hour if hour >= 5 else hour + 24
    for name, start, end in PARTS:
        if start <= h < end:
            return name
    return "Night"


def by_part(drinks: list[Drink]) -> dict[str, int]:
    out = {name: 0 for name, _, _ in PARTS}
    for d in drinks:
        out[part_of_day(d.at.hour)] += d.ml
    return out


@dataclass(frozen=True)
class Stats:
    days_logged: int
    days_at_goal: int
    average_ml: int          # per day that had something logged
    best_day: DayPoint | None


def stats(points: list[DayPoint]) -> Stats:
    logged = [p for p in points if p.total > 0]
    best = max(logged, key=lambda p: p.total, default=None)
    return Stats(
        days_logged=len(logged),
        days_at_goal=sum(p.met for p in points),
        average_ml=round(sum(p.total for p in logged) / len(logged)) if logged else 0,
        best_day=best,
    )


def observations(days: dict[date, DayRecord], today: date) -> list[str]:
    """A few plain sentences about the last 30 days (empty when there's too little to say)."""
    since = today - timedelta(days=29)
    drinks = [d for day, rec in days.items() if day >= since for d in rec.drinks]
    total = sum(d.ml for d in drinks)
    if len(drinks) < 3 or total <= 0:
        return []
    notes = []
    parts = by_part(drinks)
    top_part, top_ml = max(parts.items(), key=lambda kv: kv[1])
    notes.append(f"Most of your drinks come in the {top_part.lower()} ({round(top_ml * 100 / total)}% of the water you logged).")
    if parts["Afternoon"] * 100 / total < 15:
        notes.append("Afternoons are quiet. A glass with lunch is an easy way to spread your water out.")
    elif parts["Morning"] * 100 / total < 15:
        notes.append("Mornings are quiet. A glass when you wake up is a gentle start.")
    kinds = by_kind(drinks)
    fav, fav_ml = next(iter(kinds.items()))
    if fav != "water" or len(kinds) > 1:
        t = drink_type(fav)
        notes.append(f"Your most-logged drink is {t.label.lower()} {t.emoji} ({round(fav_ml * 100 / total)}%).")
    week = last_n(days, today, 7, 0)
    met = sum(p.met for p in week)
    if met:
        notes.append(f"You reached your goal on {met} of the last 7 days.")
    return notes
