import random
from datetime import date, datetime, timedelta

import pytest

from waterbuddy import goals, messages, tracker, units
from waterbuddy.tracker import Drink

NOON = datetime(2026, 11, 14, 12, 0)


# Goals
def test_every_age_group_has_a_goal_inside_its_own_range():
    for g in goals.AGE_GROUPS:
        assert g.low_ml <= g.suggested_ml <= g.high_ml
        assert g.source[1].startswith("https://")


def test_suggested_goals_follow_the_references():
    assert goals.suggested_goal("4-8") == 1250
    assert goals.suggested_goal("18-64") == 2000


def test_unusual_goal_is_flagged():
    assert goals.goal_is_unusual(4000, "4-8")
    assert goals.goal_is_unusual(500, "18-64")
    assert not goals.goal_is_unusual(2200, "18-64")


def test_unknown_group_raises():
    with pytest.raises(KeyError):
        goals.group_by_key("200+")


# Calculations
def test_total_remaining_and_percent():
    drinks = [Drink(250, NOON), Drink(500, NOON), Drink(250, NOON)]
    total = tracker.total_ml(drinks)
    assert total == 1000
    assert tracker.remaining_ml(total, 2000) == 1000
    assert tracker.percent(total, 2000) == 50


def test_percent_rounds_down_and_caps():
    assert tracker.percent(1999, 2000) == 99      # never shows 100% before the goal is met
    assert tracker.percent(2000, 2000) == 100
    assert tracker.percent(3000, 2000) == 100
    assert tracker.remaining_ml(3000, 2000) == 0
    assert tracker.percent(100, 0) == 0


def test_milestones():
    assert tracker.crossed_milestone(0, 250, 2000) is None
    assert tracker.crossed_milestone(250, 500, 2000) == 25
    assert tracker.crossed_milestone(750, 1000, 2000) == 50
    assert tracker.crossed_milestone(0, 1600, 2000) == 75     # a big drink reports the highest one
    assert tracker.crossed_milestone(1750, 2000, 2000) == 100
    assert tracker.crossed_milestone(2000, 2250, 2000) is None  # past the goal: nothing new


def test_validate_amount():
    assert tracker.validate_amount(250) is None
    assert tracker.validate_amount(0)
    assert tracker.validate_amount(-5)
    assert tracker.validate_amount(2500)


def test_sip_guard_counts_only_the_last_hour():
    drinks = [Drink(500, NOON - timedelta(minutes=90)), Drink(500, NOON - timedelta(minutes=30)), Drink(500, NOON)]
    assert tracker.ml_in_last_hour(drinks, NOON) == 1000
    assert not tracker.needs_sip_guard(drinks, NOON)
    drinks.append(Drink(250, NOON))
    assert tracker.needs_sip_guard(drinks, NOON)


def test_drinks_by_hour():
    drinks = [Drink(250, NOON), Drink(250, NOON + timedelta(minutes=10)), Drink(500, NOON - timedelta(hours=3))]
    assert tracker.drinks_by_hour(drinks) == {9: 500, 12: 500}


# Messages
def test_mood_follows_progress_and_age():
    assert messages.mood(0, child=False)[0] == "🐟"
    assert messages.mood(50, child=True)[1].startswith("Halfway")
    assert messages.mood(100, child=False)[0] == "🎉"
    assert messages.mood(60, child=False) == messages.mood(50, child=False)


def test_milestone_messages_exist_for_every_milestone():
    for m in tracker.MILESTONES:
        assert messages.milestone_message(m, child=True)
        assert messages.milestone_message(m, child=False)


def test_tips():
    assert messages.tip_of_the_day(date(2026, 11, 14)) == messages.tip_of_the_day(date(2026, 11, 14))
    assert messages.tip_of_the_day(date(2026, 11, 14)) != messages.tip_of_the_day(date(2026, 11, 15))
    first = messages.TIPS[0]
    assert messages.random_tip(exclude=first, rng=random.Random(1)) != first


# Units
def test_conversions():
    assert units.convert(2, "cups", "ml") == 500
    assert units.convert(500, "ml", "cups") == 2
    assert units.convert(1, "fl oz", "ml") == pytest.approx(29.57, abs=0.01)
    assert units.convert(250, "ml", "fl oz") == pytest.approx(8.45, abs=0.01)
    with pytest.raises(ValueError):
        units.to_ml(1, "gallons")


def test_litres():
    assert units.litres(2000) == "2 L"
    assert units.litres(1250) == "1.25 L"
    assert units.litres(1800) == "1.8 L"


# Gauge, views and end-of-day summary
from waterbuddy import views  # noqa: E402
from waterbuddy.gauge import BOTTOM, TOP, gauge_svg, level_y  # noqa: E402
from waterbuddy.summary import day_summary  # noqa: E402


def test_gauge_water_level_follows_progress_and_stops_at_the_goal():
    assert level_y(0, 2000) == BOTTOM
    assert level_y(1000, 2000) == (BOTTOM + TOP) / 2
    assert level_y(2000, 2000) == TOP
    assert level_y(3000, 2000) == TOP
    svg = gauge_svg(1000, 2000)
    assert 'aria-label="Water level: 1,000 ml of 2,000 ml, 50% of today\'s goal"' in svg
    assert svg.count('class="wb-mark on"') == 2      # the quarter and half marks are lit


def test_gauge_animates_up_from_the_previous_level():
    svg = gauge_svg(750, 2000, from_ml=500)
    assert f"--from:{level_y(500, 2000):.1f}px" in svg and f"--to:{level_y(750, 2000):.1f}px" in svg


def test_drink_log_marks_the_drink_that_reached_the_goal():
    drinks = [Drink(1500, NOON), Drink(500, NOON + timedelta(minutes=30)), Drink(250, NOON + timedelta(hours=1))]
    log = views.drink_log(drinks, 2000)
    assert log.count("goal reached") == 1
    assert log.index("13:00") < log.index("12:00")   # newest first


def test_reading_says_what_is_left_or_over():
    assert "500 ml</b> to go" in views.reading(1500, 2000, 75, 500)
    assert "250 ml</b> over your goal" in views.reading(2250, 2000, 100, 0)


def test_summary_of_an_empty_day_is_kind():
    s = day_summary([], 2000)
    assert s.drinks == 0 and s.first is None and not s.reached_goal
    assert "No drinks" in s.headline


def test_summary_counts_drinks_and_times():
    drinks = [Drink(250, NOON), Drink(500, NOON + timedelta(hours=2)), Drink(250, NOON - timedelta(hours=3))]
    s = day_summary(drinks, 2000)
    assert (s.total_ml, s.pct, s.drinks, s.average_ml, s.largest_ml) == (1000, 50, 3, 333, 500)
    assert (s.first, s.last) == ("09:00", "14:00")
    assert not s.reached_goal


def test_summary_at_goal_says_no_more_is_needed():
    s = day_summary([Drink(1000, NOON), Drink(1000, NOON)], 2000)
    assert s.reached_goal and s.pct == 100
    assert "Nothing more is needed" in s.note
