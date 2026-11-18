"""Daily intake calculations: totals, what's left, percentage, milestones and the sip guard."""

from dataclasses import dataclass
from datetime import datetime, timedelta

MILESTONES = (25, 50, 75, 100)
MAX_SINGLE_LOG_ML = 2000          # one entry bigger than this is almost certainly a typo
SIP_GUARD_ML = 1000               # more than this within an hour: "Sip, don't rush"
SIP_GUARD_WINDOW = timedelta(hours=1)


@dataclass(frozen=True)
class Drink:
    ml: int
    at: datetime
    kind: str = "water"   # a key from waterbuddy.drinks.DRINKS


def total_ml(drinks: list[Drink]) -> int:
    return sum(d.ml for d in drinks)


def remaining_ml(total: int, goal: int) -> int:
    return max(0, goal - total)


def percent(total: int, goal: int) -> int:
    """Whole percent of the goal, rounded down (so 100% only once the goal is really met), capped at 100."""
    if goal <= 0:
        return 0
    return min(100, (total * 100) // goal)


def fill_fraction(total: int, goal: int) -> float:
    """0..1, for the progress bar."""
    return percent(total, goal) / 100


def crossed_milestone(before: int, after: int, goal: int) -> int | None:
    """The highest milestone passed by a drink that took the total from `before` to `after`."""
    p0, p1 = percent(before, goal), percent(after, goal)
    passed = [m for m in MILESTONES if p0 < m <= p1]
    return passed[-1] if passed else None


def validate_amount(ml: int) -> str | None:
    """None if the amount can be logged, otherwise a friendly reason it can't."""
    if ml <= 0:
        return "Enter an amount above 0 ml."
    if ml > MAX_SINGLE_LOG_ML:
        return f"That's more than {MAX_SINGLE_LOG_ML} ml in one go. Log each drink separately."
    return None


def ml_in_last_hour(drinks: list[Drink], now: datetime) -> int:
    return sum(d.ml for d in drinks if timedelta(0) <= now - d.at <= SIP_GUARD_WINDOW)


def needs_sip_guard(drinks: list[Drink], now: datetime) -> bool:
    """More than a litre within the last hour: suggest slowing down."""
    return ml_in_last_hour(drinks, now) > SIP_GUARD_ML


def drinks_by_hour(drinks: list[Drink]) -> dict[int, int]:
    """Millilitres per hour of the day, for the day's chart."""
    hours: dict[int, int] = {}
    for d in drinks:
        hours[d.at.hour] = hours.get(d.at.hour, 0) + d.ml
    return dict(sorted(hours.items()))
