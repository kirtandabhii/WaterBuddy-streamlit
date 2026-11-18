from datetime import date, datetime, timedelta

from waterbuddy import achievements, drinks, insights, store, themes
from waterbuddy.store import DayRecord, Saved
from waterbuddy.tracker import Drink

TODAY = date(2026, 11, 15)


def at(day: date, hour: int, minute: int = 0) -> datetime:
    return datetime(day.year, day.month, day.day, hour, minute)


# Drink types and caffeine
def test_caffeine_is_counted_per_drink_and_size():
    day = [Drink(250, at(TODAY, 8), "coffee"), Drink(500, at(TODAY, 15), "tea"), Drink(250, at(TODAY, 9))]
    assert drinks.caffeine_mg(day) == 90 + 80


def test_caffeine_note_is_gentle_for_children_and_warns_adults_over_the_limit():
    assert drinks.caffeine_note(0, child=False) is None
    assert "grown-up" in drinks.caffeine_note(40, child=True)
    assert "more than the 400 mg" in drinks.caffeine_note(450, child=False)
    assert "up to 400 mg" in drinks.caffeine_note(90, child=False)


def test_unknown_drink_types_fall_back_to_water():
    assert drinks.drink_type("lemonade").key == "water"


def test_drink_mix_is_sorted_largest_first():
    mix = drinks.by_kind([Drink(250, at(TODAY, 8), "tea"), Drink(500, at(TODAY, 9)), Drink(250, at(TODAY, 10), "tea")])
    assert list(mix.items()) == [("water", 500), ("tea", 500)] or list(mix.items()) == [("tea", 500), ("water", 500)]


# Saving in the browser
def test_saved_data_round_trips_through_json():
    s = Saved(age="18-64", goal_slider=2200, theme="moonlight", day=TODAY,
              drinks=[Drink(250, at(TODAY, 9), "tea")], celebrated=True, found=["water"],
              history={TODAY - timedelta(days=1): DayRecord(2000, [Drink(500, at(TODAY - timedelta(days=1), 10))])},
              badges={"first-drop": TODAY})
    back = store.from_json(store.to_json(s))
    assert back == s


def test_damaged_saved_data_falls_back_safely():
    assert store.from_json(None) == Saved()
    assert store.from_json({"v": 99}) == Saved()
    raw = store.to_json(Saved(day=TODAY, drinks=[Drink(250, at(TODAY, 9))]))
    raw["drinks"].append({"ml": "lots", "at": "yesterday"})
    raw["drinks"].append({"ml": -5, "at": "2026-11-15T10:00:00"})
    assert len(store.from_json(raw).drinks) == 1


def test_old_days_are_trimmed_when_saving():
    history = {TODAY - timedelta(days=i): DayRecord(2000, [Drink(250, at(TODAY - timedelta(days=i), 9))])
               for i in range(1, store.KEEP_DAYS + 20)}
    assert len(store.to_json(Saved(history=history))["history"]) == store.KEEP_DAYS


def test_a_new_day_files_yesterday_in_history():
    yesterday = TODAY - timedelta(days=1)
    s = Saved(day=yesterday, drinks=[Drink(250, at(yesterday, 9))], celebrated=True, found=["water"])
    assert store.roll_over(s, TODAY, 2000)
    assert s.day == TODAY and s.drinks == [] and not s.celebrated and s.found == []
    assert s.history[yesterday].total == 250
    assert not store.roll_over(s, TODAY, 2000)


# Insights
def _days(totals: dict[int, int], goal: int = 2000) -> dict[date, DayRecord]:
    return {TODAY - timedelta(days=ago): DayRecord(goal, [Drink(ml, at(TODAY - timedelta(days=ago), 10))])
            for ago, ml in totals.items()}


def test_week_includes_empty_days_and_marks_goal_days():
    week = insights.last_n(_days({0: 2000, 2: 500}), TODAY, 7, 2000)
    assert [p.day for p in week][-1] == TODAY and len(week) == 7
    assert [p.total for p in week] == [0, 0, 0, 0, 500, 0, 2000]
    assert [p.met for p in week][-1]


def test_stats_average_only_counts_days_with_drinks():
    m = insights.stats(insights.last_n(_days({0: 2000, 1: 1000}), TODAY, 30, 2000))
    assert (m.days_logged, m.days_at_goal, m.average_ml, m.best_day.total) == (2, 1, 1500, 2000)


def test_observations_describe_the_time_of_day_and_favourite_drink():
    days = {TODAY: DayRecord(2000, [Drink(500, at(TODAY, 8), "tea"), Drink(500, at(TODAY, 9), "tea"),
                                    Drink(250, at(TODAY, 19))])}
    notes = insights.observations(days, TODAY)
    assert notes[0].startswith("Most of your drinks come in the morning (80%")
    assert any("Afternoons are quiet" in n for n in notes)
    assert any("tea or chai" in n for n in notes)


def test_no_observations_from_too_little_data():
    assert insights.observations({TODAY: DayRecord(2000, [Drink(250, at(TODAY, 9))])}, TODAY) == []


def test_late_night_drinks_count_as_night():
    assert insights.part_of_day(23) == "Night" and insights.part_of_day(2) == "Night"
    assert insights.part_of_day(5) == "Morning"


# Badges
def test_first_day_badges():
    day = DayRecord(2000, [Drink(250, at(TODAY, 8)), Drink(1000, at(TODAY, 11)), Drink(500, at(TODAY, 14)),
                           Drink(250, at(TODAY, 19))])
    got = achievements.evaluate({TODAY: day}, False, TODAY)
    assert {"first-drop", "early-bird", "halfway-noon", "all-day", "full-spring", "steady"} <= set(got)
    assert "three-days" not in got and "explorer" not in got


def test_steady_needs_pacing_not_just_the_goal():
    rushed = DayRecord(2000, [Drink(1000, at(TODAY, 10)), Drink(1000, at(TODAY, 10, 30))])
    got = achievements.evaluate({TODAY: rushed}, False, TODAY)
    assert "full-spring" in got and "steady" not in got


def test_goal_day_badges_count_any_days_not_streaks():
    got = achievements.evaluate(_days({0: 2000, 5: 2000, 20: 2000, 3: 100}), False, TODAY)
    assert got["three-days"] == TODAY


def test_taste_tester_and_ten_litres_and_explorer():
    kinds = ["water", "tea", "coffee", "milk"]
    days = {TODAY - timedelta(days=i): DayRecord(2500, [Drink(2500, at(TODAY - timedelta(days=i), 9), kinds[i])])
            for i in range(4)}
    got = achievements.evaluate(days, True, TODAY)
    assert got["taste-tester"] == TODAY and got["ten-litres"] == TODAY and got["explorer"] == TODAY


def test_badges_are_never_taken_away():
    kept = {"full-spring": TODAY - timedelta(days=3)}
    merged = achievements.merge(kept, {})
    assert merged == kept
    assert achievements.newly_earned(kept, {"full-spring": TODAY, "first-drop": TODAY})[0].key == "first-drop"


def test_no_badge_rewards_drinking_past_the_goal():
    for badge in achievements.BADGES:
        assert "more than" not in badge.how or "litre in any hour" in badge.how


# Themes
def test_every_theme_has_css_and_unknown_themes_fall_back():
    for t in themes.THEMES.values():
        assert t.accent_deep in themes.css(t)
    assert themes.theme("neon").key == "spring"
    assert themes.overlay(themes.theme("spring"), reduced=False) == ""
    assert "wb-firefly" in themes.overlay(themes.theme("moonlight"), reduced=False)
    assert "wb-firefly" not in themes.overlay(themes.theme("moonlight"), reduced=True)
