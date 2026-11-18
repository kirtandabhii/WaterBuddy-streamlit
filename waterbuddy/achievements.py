"""Badges: small moments worth noticing. Once earned, a badge is never taken away.

Following WaterBuddy's safety rules there are no streaks (nothing is lost for a missed day), and
no badge rewards drinking past the goal. "Nice and steady" rewards pacing rather than volume.
"""

from dataclasses import dataclass
from datetime import date, timedelta

from waterbuddy.store import DayRecord
from waterbuddy.tracker import needs_sip_guard


@dataclass(frozen=True)
class Badge:
    key: str
    emoji: str
    title: str
    how: str


BADGES: list[Badge] = [
    Badge("first-drop", "💧", "First drop", "Log your first drink."),
    Badge("full-spring", "🌊", "Full spring", "Reach your daily goal."),
    Badge("early-bird", "🌅", "Early bird", "Have a drink before 9 in the morning."),
    Badge("halfway-noon", "🕛", "Halfway by noon", "Reach half your goal before 12 noon."),
    Badge("all-day", "☀️", "All-day sipper", "Drink in the morning, afternoon and evening of one day."),
    Badge("steady", "🐢", "Nice and steady", "Reach your goal without more than a litre in any hour."),
    Badge("taste-tester", "🍵", "Taste tester", "Log four different kinds of drink."),
    Badge("explorer", "🔍", "Spring explorer", "Find all four things in Ripple's spring (Atlas)."),
    Badge("three-days", "⭐", "Three good days", "Reach your goal on three days (any days)."),
    Badge("seven-days", "🏆", "Seven good days", "Reach your goal on seven days (any days)."),
    Badge("ten-litres", "🪣", "Ten litres", "Log 10 litres in total."),
]
BY_KEY = {b.key: b for b in BADGES}


def _day_badges(day: date, rec: DayRecord) -> set[str]:
    got: set[str] = set()
    if not rec.drinks:
        return got
    got.add("first-drop")
    drinks = sorted(rec.drinks, key=lambda d: d.at)
    if any(d.at.hour < 9 and d.at.hour >= 4 for d in drinks):
        got.add("early-bird")
    if rec.goal > 0 and sum(d.ml for d in drinks if d.at.hour < 12) * 2 >= rec.goal:
        got.add("halfway-noon")
    parts = {("m" if 4 <= d.at.hour < 12 else "a" if 12 <= d.at.hour < 17 else "e" if 17 <= d.at.hour < 23 else "n")
             for d in drinks}
    if {"m", "a", "e"} <= parts:
        got.add("all-day")
    if rec.met:
        got.add("full-spring")
        if not any(needs_sip_guard(drinks[: i + 1], d.at) for i, d in enumerate(drinks)):
            got.add("steady")
    return got


def evaluate(days: dict[date, DayRecord], found_all_today: bool, today: date) -> dict[str, date]:
    """Every badge the data supports, with the first day it was earned."""
    earned: dict[str, date] = {}
    kinds: set[str] = set()
    goal_days = 0
    litres = 0
    for day in sorted(days):
        rec = days[day]
        for key in _day_badges(day, rec):
            earned.setdefault(key, day)
        for d in sorted(rec.drinks, key=lambda d: d.at):
            kinds.add(d.kind)
            litres += d.ml
            if len(kinds) >= 4:
                earned.setdefault("taste-tester", day)
            if litres >= 10_000:
                earned.setdefault("ten-litres", day)
        if rec.met:
            goal_days += 1
            if goal_days >= 3:
                earned.setdefault("three-days", day)
            if goal_days >= 7:
                earned.setdefault("seven-days", day)
    if found_all_today:
        earned.setdefault("explorer", today)
    return earned


def newly_earned(before: dict[str, date], now: dict[str, date]) -> list[Badge]:
    """Badges in `now` that weren't in `before`, in display order."""
    return [b for b in BADGES if b.key in now and b.key not in before]


def merge(kept: dict[str, date], found: dict[str, date]) -> dict[str, date]:
    """Badges are never taken away: keep everything already earned, add anything new."""
    out = dict(kept)
    for key, day in found.items():
        out.setdefault(key, day)
    return out


def recently(earned: dict[str, date], today: date, days: int = 7) -> list[Badge]:
    return [b for b in BADGES if b.key in earned and today - earned[b.key] < timedelta(days=days)]
