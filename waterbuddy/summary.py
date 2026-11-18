"""The end-of-day summary: a short, kind look back at the day's drinks."""

from dataclasses import dataclass

from waterbuddy.tracker import Drink, percent, total_ml
from waterbuddy.units import litres


@dataclass(frozen=True)
class DaySummary:
    total_ml: int
    goal_ml: int
    pct: int
    drinks: int
    average_ml: int
    largest_ml: int
    first: str | None   # "08:15"
    last: str | None
    reached_goal: bool
    headline: str
    note: str


def day_summary(drinks: list[Drink], goal_ml: int) -> DaySummary:
    total = total_ml(drinks)
    pct = percent(total, goal_ml)
    count = len(drinks)
    times = sorted(d.at for d in drinks)
    reached = total >= goal_ml

    if count == 0:
        headline = "No drinks logged yet today."
        note = "That's fine. Log a glass whenever you have one; tomorrow is a fresh start either way."
    elif reached:
        headline = f"Goal reached: {litres(total)} of {litres(goal_ml)}."
        note = "Well done. Nothing more is needed today unless you're thirsty."
    else:
        headline = f"{litres(total)} of {litres(goal_ml)} ({pct}%)."
        note = ("Every glass counts. Food adds water too, so a day a little under the goal is "
                "nothing to worry about. Tomorrow starts fresh.")

    return DaySummary(
        total_ml=total,
        goal_ml=goal_ml,
        pct=pct,
        drinks=count,
        average_ml=round(total / count) if count else 0,
        largest_ml=max((d.ml for d in drinks), default=0),
        first=times[0].strftime("%H:%M") if times else None,
        last=times[-1].strftime("%H:%M") if times else None,
        reached_goal=reached,
        headline=headline,
        note=note,
    )
