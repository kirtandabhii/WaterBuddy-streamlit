"""WaterBuddy: a gentle daily water tracker with Ripple, a water spirit who lives in a forest spring.

Run with:  streamlit run app.py

- `waterbuddy/` holds the logic (goals, drinks, tracking, insights, badges, themes; tested in tests/)
  and the small HTML pieces.
- `spring_component/` is Ripple's 3D spring; `storage_component/` saves the data in the browser.
- `assets/style.css` is the look.
This file is the interface: the top bar, four pages (Today, Atlas, Insights, Badges), the sidebar,
and the session state that holds the day.
"""

import base64
import functools
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import altair as alt
import pandas as pd
import streamlit as st

from spring_component import spring
from storage_component import browser_storage
from waterbuddy import achievements, drinks, goals, insights, messages, store, themes, tracker, units, views
from waterbuddy.gauge import gauge_svg
from waterbuddy.store import DayRecord
from waterbuddy.summary import day_summary
from waterbuddy.tracker import Drink

st.set_page_config(page_title="WaterBuddy", page_icon="💧", layout="wide")

ROOT = Path(__file__).parent
PAGES = ["Today", "Atlas", "Insights", "Badges"]
FINDABLE = {"ripple": "Ripple", "water": "The water", "pad": "A lily pad", "spout": "The bamboo spout"}
SHORT_AGE = {"4-8": "4–8", "9-13": "9–13", "14-17": "14–17", "18-64": "18–64", "65+": "65+"}
KEEP_WIDGETS = ("age_pick", "goal_slider", "goal_sure", "custom_ml", "kind_pick")

# Where Ripple stands in the full-screen spring: to the right of the panel on wide screens,
# in the top half on phones (the panels scroll up over the lower half).
FRAMING = (-2.1, 0.45, 2.4)
FRAMING_NARROW = (0.0, -0.3, 2.6)
FRAMING_EXPLORE = (-2.5, 0.3, 2.0)


@functools.cache
def stylesheet() -> str:
    return (ROOT / "assets" / "style.css").read_text(encoding="utf-8")


@functools.cache
def poster_uri() -> str:
    data = (ROOT / "spring_component" / "frontend" / "dist" / "ripple-poster.webp").read_bytes()
    return "data:image/webp;base64," + base64.b64encode(data).decode()


def html(markup: str) -> None:
    st.markdown(markup, unsafe_allow_html=True)


def tile_key(age_key: str) -> str:
    return "age-" + age_key.replace("+", "plus")


# ---------- Time and session state ----------

def now() -> datetime:
    """The current time in the viewer's own timezone (the server may be in another one)."""
    zone = None
    try:
        if st.context.timezone:
            zone = ZoneInfo(st.context.timezone)
    except (ZoneInfoNotFoundError, ValueError):
        zone = None
    return datetime.now(zone).replace(tzinfo=None)


def start_day(state) -> None:
    """Clear everything that belongs to one day (a new date, or Reset day)."""
    state.day = now().date()
    state.drinks = []
    state.pour = None
    state.rise_from = None
    state.celebrated = False
    state.found = []
    state.quest_done = False


def file_today(state) -> None:
    """Keep the current day's drinks in history before the day changes."""
    if state.drinks:
        state.history[state.day] = DayRecord(state.goal, list(state.drinks))


def init_state() -> None:
    s = st.session_state
    if "day" not in s:
        start_day(s)
        s.age = None
        s.goal = 2000
        s.goal_slider = 2000
        s.goal_sure = False
        s.age_pick = None
        s.custom_ml = 200
        s.kind_pick = "water"
        s.theme = "spring"
        s.history = {}
        s.badges = {}
        s.pour_id = 0
        s.flash = []
        s.splash = False
        s.pops = []
        s.tip = None
        s.last_page = "Today"
        s.saved_loaded = False
        s.pending = None
        s.clear_store = False
    elif s.day != now().date():
        # A new day has begun while the app was open: yesterday is kept in history.
        file_today(s)
        start_day(s)
        say("🌅", "Good morning", "A new day has started.")
    if s.pending is not None:
        apply_saved(s, s.pending)
        s.pending = None
    # Streamlit forgets a widget's value while its page isn't shown. Re-saving these keeps them
    # when someone visits another page and comes back.
    for key in KEEP_WIDGETS:
        if key in s:
            s[key] = s[key]
    s.theme_pick = s.theme


def apply_saved(s, saved: store.Saved) -> None:
    """Bring back what was saved in this browser (runs before any widget is drawn)."""
    today = now().date()
    if saved.age in SHORT_AGE:
        s.age = saved.age
        s.age_pick = saved.age
        s.goal_slider = min(goals.MAX_GOAL_ML, max(goals.MIN_GOAL_ML, saved.goal_slider))
        s.goal_sure = saved.goal_sure
    s.theme = saved.theme if saved.theme in themes.THEMES else "spring"
    s.history = saved.history
    update_goal()
    if saved.day == today:
        s.drinks = saved.drinks
        s.celebrated = saved.celebrated
        s.found = [f for f in saved.found if f in FINDABLE]
        s.quest_done = len(s.found) == len(FINDABLE)
    elif saved.day is not None and saved.drinks:
        s.history[saved.day] = DayRecord(s.goal, saved.drinks)
    # Badges already earned stay earned; anything the saved days now support is added quietly.
    s.badges = achievements.merge(saved.badges, achievements.evaluate(all_days(), False, today))


def snapshot() -> dict:
    s = st.session_state
    return store.to_json(store.Saved(
        age=s.age, goal_slider=int(s.goal_slider), goal_sure=bool(s.goal_sure), theme=s.theme,
        day=s.day, drinks=s.drinks, celebrated=s.celebrated, found=s.found,
        history=s.history, badges=s.badges,
    ))


def group() -> goals.AgeGroup | None:
    return goals.group_by_key(st.session_state.age) if st.session_state.age else None


def is_child() -> bool:
    g = group()
    return bool(g and g.child)


def update_goal() -> None:
    """The goal in use: the slider's value, unless it's unusual for the age group and not confirmed."""
    s, g = st.session_state, group()
    if not g:
        return
    wanted = int(s.goal_slider)
    s.goal = wanted if (not goals.goal_is_unusual(wanted, g.key) or s.goal_sure) else g.suggested_ml


def all_days() -> dict[date, DayRecord]:
    s = st.session_state
    return insights.all_days(s.history, s.day, DayRecord(s.goal, s.drinks))


def say(icon: str, head: str, detail: str = "") -> None:
    """Queue a short notice for the next redraw (callbacks can't draw)."""
    st.session_state.flash.append((icon, head, detail))


def toast(icon: str, head: str, detail: str = "") -> None:
    """A notice: a bold first line and an optional quieter second line (styled in style.css)."""
    st.toast(f"**{head}**" + (f"  \n{detail}" if detail else ""), icon=icon)


def check_badges() -> None:
    """Add any badge the data now supports, and celebrate the new ones."""
    s = st.session_state
    found = achievements.evaluate(all_days(), len(s.found) == len(FINDABLE), s.day)
    new = achievements.newly_earned(s.badges, found)
    s.badges = achievements.merge(s.badges, found)
    for badge in new:
        s.pops.append(badge.key)     # shown as the badge card, or as a toast (see show_flash)


# ---------- Actions (callbacks run before the page redraws) ----------

def choose_age(key: str) -> None:
    s = st.session_state
    s.age = key
    s.age_pick = key
    s.goal_slider = goals.suggested_goal(key)
    s.goal_sure = False


def on_age_pick() -> None:
    s = st.session_state
    if s.age_pick is None:          # clicking the chosen pill again: keep it chosen
        s.age_pick = s.age
        return
    choose_age(s.age_pick)


def on_kind_pick() -> None:
    if st.session_state.kind_pick is None:
        st.session_state.kind_pick = "water"


def on_theme_pick() -> None:
    s = st.session_state
    if s.theme_pick:
        s.theme = s.theme_pick


def on_nav() -> None:
    s = st.session_state
    if s.nav is None:
        s.nav = s.last_page
    s.last_page = s.nav


def log_drink(ml: int, kind: str | None = None) -> None:
    s = st.session_state
    problem = tracker.validate_amount(ml)
    if problem:
        say("⚠️", "Can't log that", problem)
        return
    kind = kind or s.kind_pick or "water"
    goal = s.goal
    before = tracker.total_ml(s.drinks)
    after = before + ml
    s.drinks.append(Drink(ml, now(), kind))
    s.pour_id += 1
    s.rise_from = before
    reached = before < goal <= after
    s.pour = {
        "id": s.pour_id,
        "from_ml": before,
        "to_ml": after,
        "reached_goal": reached and not s.celebrated,
        "past_goal": before >= goal,
    }
    child = is_child()
    t = drinks.drink_type(kind)
    head = f"+{ml} ml {t.label.lower()}"
    if before >= goal:
        # Past the goal: logged accurately, but nothing rewards drinking more.
        say(t.emoji, head, messages.past_goal_message(child))
    else:
        milestone = tracker.crossed_milestone(before, after, goal)
        if milestone == 100 and not s.celebrated:
            s.celebrated = True      # one celebration a day, even after an Undo and a re-log
            s.splash = True
        say(t.emoji, head, messages.milestone_message(milestone, child) if milestone else "")
    check_badges()


def log_custom() -> None:
    log_drink(int(st.session_state.custom_ml or 0))


def undo_last() -> None:
    s = st.session_state
    if s.drinks:
        last = s.drinks.pop()
        s.pour = None                # the spring settles back to the true level
        say("↩️", "Removed", f"Your last drink ({last.ml} ml {drinks.drink_type(last.kind).label.lower()}).")


def reset_day() -> None:
    start_day(st.session_state)
    say("🔄", "Today reset", "Earlier days and badges are kept.")


def delete_everything() -> None:
    s = st.session_state
    start_day(s)
    s.history, s.badges, s.age, s.age_pick = {}, {}, None, None
    s.goal, s.goal_slider, s.goal_sure, s.theme, s.kind_pick = 2000, 2000, False, "spring", "water"
    s.clear_store = True
    say("🗑️", "Deleted", "Everything saved in this browser is gone.")


def another_tip() -> None:
    s = st.session_state
    s.tip = messages.random_tip(exclude=s.tip or messages.tip_of_the_day(s.day))


def show_flash() -> None:
    """Messages and moments queued by the callbacks, shown once."""
    s = st.session_state
    for icon, head, detail in s.flash:
        toast(icon, head, detail)
    s.flash = []
    # The newest badge gets its own card; any others (or all, with reduced motion) get a toast.
    carded = s.pops[-1] if s.pops and not s.splash and not s.reduced else None
    for key in s.pops:
        if key != carded:
            badge = achievements.BY_KEY[key]
            toast(badge.emoji, "Badge earned", badge.title)
    if s.splash:
        if not s.reduced:
            html(views.splash("You reached today's goal 🎉" if is_child() else "Goal reached for today"))
        s.splash = False
    elif s.pops and not s.reduced:
        html(views.badge_pop(achievements.BY_KEY[s.pops[-1]]))
    s.pops = []


# ---------- Frame: top bar, the spring behind everything, and the sidebar ----------

def top_bar() -> str:
    s = st.session_state
    with st.container(key="glass-top"):
        left, middle, right = st.columns([0.9, 1.6, 0.8], vertical_alignment="center")
        left.markdown(views.brand(), unsafe_allow_html=True)
        with middle:
            st.segmented_control("Page", PAGES, default="Today", key="nav", on_change=on_nav,
                                 label_visibility="collapsed", width="stretch")
        right.markdown(views.date_line(s.day, group()), unsafe_allow_html=True)
    return s.nav or s.last_page


def stage(page: str) -> list[str]:
    """Ripple's living spring, filling the window behind every page. Returns what was found (Atlas)."""
    s = st.session_state
    theme = themes.theme(s.theme)
    html(themes.css(theme))
    if not s.show3d:
        html(views.backdrop(poster_uri()))
        html(themes.overlay(theme, s.reduced))
        return []
    explore = page == "Atlas"
    total = tracker.total_ml(s.drinks)
    found = spring(total, s.goal, explore=explore, pour=s.pour, height=0, framing=FRAMING,
                   framing_narrow=FRAMING_NARROW, framing_explore=FRAMING_EXPLORE, reduced=s.reduced,
                   sound=s.sound, key="stage-explore" if explore else "stage")
    html(themes.overlay(theme, s.reduced))
    return found


def sidebar() -> None:
    s = st.session_state
    with st.sidebar:
        html('<p class="wb-eyebrow">Theme</p>')
        st.pills("Theme", list(themes.THEMES), key="theme_pick", on_change=on_theme_pick,
                 format_func=lambda k: f"{themes.THEMES[k].emoji} {themes.THEMES[k].label}",
                 label_visibility="collapsed")
        st.divider()
        html('<p class="wb-eyebrow">Tip of the day</p>')
        html(f'<p class="wb-tip">{s.tip or messages.tip_of_the_day(s.day)}</p>')
        st.button("Show another tip", on_click=another_tip, type="tertiary", icon=":material/refresh:")
        st.divider()

        with st.expander("Cups ⇄ ml ⇄ fl oz", icon=":material/swap_horiz:"):
            value = st.number_input("Amount", min_value=0.0, value=1.0, step=0.5, key="conv_value")
            a, b = st.columns(2)
            from_unit = a.selectbox("From", units.UNITS, index=1, key="conv_from")
            to_unit = b.selectbox("To", units.UNITS, index=0, key="conv_to")
            result = units.convert(value, from_unit, to_unit)
            st.metric("Equals", f"{result:,.0f} ml" if to_unit == "ml" else f"{result:,.1f} {to_unit}")
            st.caption("1 cup = 250 ml, a standard glass or steel tumbler. 1 US fl oz ≈ 29.6 ml.")

        with st.expander("Settings", icon=":material/tune:"):
            st.toggle("Show Ripple's 3D spring", value=True, key="show3d",
                      help="Turn this off on a slow device. The tracker works the same without it.")
            st.toggle("Sound in the spring", value=False, key="sound")
            st.toggle("Reduce motion", value=False, key="reduced")
            st.toggle("Larger text", value=False, key="large_text")
            with st.popover("Delete everything", icon=":material/delete:"):
                st.write("Delete your goal, every saved day and your badges from this browser? This can't be undone.")
                st.button("Yes, delete everything", on_click=delete_everything, type="primary")

        st.caption("Your drinks, past days and badges are saved only in this browser on this device. "
                   "Nothing is sent anywhere, and nothing syncs between devices.")


# ---------- Welcome (before an age group is chosen) ----------

def page_loading() -> None:
    with st.container(key="glass-welcome"):
        html('<p class="wb-eyebrow">WaterBuddy</p><p class="wb-h2">Opening your spring…</p>')
        st.caption("Looking for what you saved in this browser last time.")
        if st.button("Start without saved data", type="tertiary"):
            st.session_state.saved_loaded = True
            st.rerun()


def page_welcome() -> None:
    with st.container(key="hero"):
        panel, world = st.columns([1.3, 1], gap="large")
        with panel, st.container(key="glass-welcome"):
            html(views.welcome_intro())
            html('<p class="wb-h2" style="margin-top:1rem">How old are you?</p>')
            html(views.age_tile_css(goals.AGE_GROUPS))
            with st.container(key="ages"):
                for col, g in zip(st.columns(len(goals.AGE_GROUPS)), goals.AGE_GROUPS):
                    col.button(SHORT_AGE[g.key], key=tile_key(g.key), on_click=choose_age, args=(g.key,),
                               width="stretch", help=f"{g.label}: suggested {units.litres(g.suggested_ml)} a day")
        with world:
            html(views.bubble("Hi, I'm Ripple! Tell me how old you are, and we'll fill my spring together."))


# ---------- Today ----------

def page_today() -> None:
    s = st.session_state
    g = group()
    goal = s.goal
    total = tracker.total_ml(s.drinks)
    pct = tracker.percent(total, goal)
    remaining = tracker.remaining_ml(total, goal)
    rise_from, s.rise_from = s.rise_from, None

    with st.container(key="hero"):
        panel, world = st.columns([1, 1.05], gap="large")
        with panel, st.container(key="glass-today"):
            gauge_col, reading_col = st.columns([0.42, 1], vertical_alignment="center")
            gauge_col.markdown(gauge_svg(total, goal, from_ml=rise_from, still=s.reduced), unsafe_allow_html=True)
            reading_col.markdown(views.reading(total, goal, pct, remaining), unsafe_allow_html=True)
            st.pills("Drink", list(drinks.DRINKS), key="kind_pick", on_change=on_kind_pick,
                     format_func=lambda k: f"{drinks.DRINKS[k].emoji} {drinks.DRINKS[k].label}",
                     label_visibility="collapsed")
            with st.container(key="drinks"):
                row1, row2 = st.columns(2), st.columns(2)
                row1[0].button("150 ml", key="add-150", on_click=log_drink, args=(150,), width="stretch")
                row1[1].button("250 ml", key="add-250", on_click=log_drink, args=(250,), width="stretch")
                row2[0].button("500 ml", key="add-500", on_click=log_drink, args=(500,), width="stretch")
                with row2[1].popover("Other", key="custom-pop", width="stretch"):
                    st.number_input("Amount (ml)", min_value=0, max_value=5000, step=50, key="custom_ml")
                    st.button("Log this amount", on_click=log_custom, type="primary", width="stretch")
            with st.container(key="daytools"):
                undo, reset = st.columns(2)
                undo.button("Undo last drink", on_click=undo_last, disabled=not s.drinks, type="tertiary",
                            icon=":material/undo:")
                with reset.popover("Reset day", icon=":material/restart_alt:"):
                    st.write("Clear today's drinks and start the day again? Earlier days and badges are kept.")
                    st.button("Yes, reset today", on_click=reset_day, type="primary")
            if total >= goal and s.drinks:
                st.success(messages.past_goal_message(is_child()), icon=":material/water_drop:")
            if tracker.needs_sip_guard(s.drinks, now()):
                st.warning("Sip, don't rush: that's over a litre in the last hour. Small sips spread "
                           "through the day are easier on your body.", icon=":material/hourglass_top:")
            note = drinks.caffeine_note(drinks.caffeine_mg(s.drinks), is_child())
            if note:
                st.caption(f"☕ {note}")
        with world:
            face, line = messages.mood(pct, g.child)
            html(views.bubble(f"{line} {face}"))

    st.write("")
    goal_col, log_col = st.columns([1.2, 1], gap="large")
    with goal_col, st.container(key="glass-goal"):
        goal_card(g)
    with log_col, st.container(key="glass-log"):
        html('<p class="wb-h2">Today&rsquo;s drinks</p>')
        html(views.drink_log(s.drinks, goal))


def goal_card(g: goals.AgeGroup) -> None:
    s = st.session_state
    html('<p class="wb-h2">Your goal</p>')
    st.pills("Age group", list(SHORT_AGE), format_func=lambda k: SHORT_AGE[k], key="age_pick",
             on_change=on_age_pick)
    if g.child:
        st.info("Ask a grown-up to help you choose your goal.", icon=":material/family_restroom:")
    st.slider("Daily goal", min_value=goals.MIN_GOAL_ML, max_value=goals.MAX_GOAL_ML, step=50,
              key="goal_slider", format="%d ml",
              help="Start from the suggestion and adjust it. A doctor's advice always comes first.")
    wanted = int(s.goal_slider)
    if goals.goal_is_unusual(wanted, g.key):
        st.warning(f"{wanted:,} ml is outside the usual range for {g.label.lower()} "
                   f"({g.low_ml:,}–{g.high_ml:,} ml). Until you confirm, the suggested goal is used.")
        st.checkbox("Use this goal anyway (for example, a doctor suggested it)", key="goal_sure")
    html(views.goal_compare(g, s.goal))
    name, url = g.source
    st.caption(f"{g.why} A starting point, not a prescription. Source: [{name}]({url}).")


# ---------- Atlas ----------

def quest_card(leaving: bool) -> None:
    """Today's Atlas quest. `leaving` is the moment all four are found: the card fades out."""
    s = st.session_state
    with st.container(key="glass-quest"):
        if leaving:
            html('<style>.st-key-glass-quest { animation: wb-in 0.8s cubic-bezier(0.2, 0.8, 0.2, 1) both, '
                 'wb-quest-out 0.7s ease 2.6s forwards; }</style>')
        html('<p class="wb-eyebrow">Atlas · today&rsquo;s quest</p>'
             '<p class="wb-h2">Find the four things that respond</p>'
             '<p class="wb-lead" style="font-size:1rem">Drag to look around; pinch or scroll to come closer. '
             "Tap Ripple, the water, a lily pad and the bamboo spout.</p>")
        html(views.quest(s.found, FINDABLE))
        if not s.show3d:
            st.caption("The 3D spring is turned off in Settings, so there's nothing to explore right now.")


def page_atlas(found: list[str]) -> None:
    s = st.session_state
    added = False
    for thing in found:
        if thing in FINDABLE and thing not in s.found:
            s.found.append(thing)
            added = True
    just_done = len(s.found) == len(FINDABLE) and not s.quest_done
    if just_done:
        s.quest_done = True
        toast("🌟", "Quest complete", "You found all four things in the spring.")
    if added:
        check_badges()
        show_flash()

    # Once all four are found the quest card has done its job: it shows the full tick list for a
    # moment, fades away, and stays gone (the spring is left clear) until tomorrow's quest.
    if just_done or not s.quest_done:
        quest_card(leaving=just_done)

    total = tracker.total_ml(s.drinks)
    with st.container(key="glass-dock"):
        html(views.dock_level(total, s.goal, tracker.percent(total, s.goal)))
        st.button("Pour 250 ml of water", key="pour-atlas", on_click=log_drink, args=(250, "water"),
                  width="stretch", disabled=not group(),
                  help=None if group() else "Choose your age group on Today first.")
        st.caption("Exploring never logs water; only Pour does.")


# ---------- Insights ----------

def page_insights() -> None:
    s = st.session_state
    theme = themes.theme(s.theme)
    blur = (theme.world_filter + " " if theme.world_filter != "none" else "") + "blur(16px) saturate(1.1)"
    html(f"<style>.st-key-stage iframe {{ filter: {blur}; transform: scale(1.06); }}</style>")

    days = all_days()
    summary = day_summary(s.drinks, s.goal)
    with st.container(key="glass-summary"):
        html(views.summary_head(summary, s.day))
        html(views.summary_stats(summary))

    st.write("")
    week_col, notes_col = st.columns([1.5, 1], gap="large")
    week = insights.last_n(days, s.day, 7, s.goal)
    with week_col, st.container(key="glass-week"):
        html('<p class="wb-h2">This week</p>')
        data = pd.DataFrame({
            "Day": [p.day.strftime("%a %d") for p in week],
            "ml": [p.total for p in week],
            "Goal": [p.goal for p in week],
            "At goal": ["Goal reached" if p.met else "Not yet" for p in week],
        })
        bars = alt.Chart(data).mark_bar(cornerRadiusTopLeft=8, cornerRadiusTopRight=8, size=34).encode(
            x=alt.X("Day:N", sort=None, title=None, axis=alt.Axis(labelAngle=0)),
            y=alt.Y("ml:Q", title="ml"),
            color=alt.Color("At goal:N", scale=alt.Scale(domain=["Goal reached", "Not yet"],
                                                         range=[theme.accent_deep, "#9fb8b2"]),
                            legend=alt.Legend(orient="top", title=None)),
            tooltip=["Day", "ml", "Goal"],
        )
        goal_ticks = alt.Chart(data).mark_tick(color="#0f3439", thickness=2, size=40).encode(
            x=alt.X("Day:N", sort=None), y="Goal:Q")
        st.altair_chart((bars + goal_ticks).properties(height=260, background="transparent")
                        .configure_view(strokeWidth=0), use_container_width=True)
        st.caption("The dark tick on each day is that day's goal.")
    with notes_col, st.container(key="glass-notes"):
        html('<p class="wb-h2">What stands out</p>')
        html(views.observation_list(insights.observations(days, s.day)))

    st.write("")
    month_col, mix_col, log_col = st.columns([1.1, 1, 1], gap="large")
    month = insights.last_n(days, s.day, 30, s.goal)
    m = insights.stats(month)
    with month_col, st.container(key="glass-month"):
        html('<p class="wb-h2">Last 30 days</p>')
        html(views.month_dots(month))
        best = f" · best day {m.best_day.total:,} ml" if m.best_day else ""
        st.caption(f"{m.days_at_goal} days at goal · {m.days_logged} days logged · "
                   f"about {m.average_ml:,} ml on a logged day{best}. Full dot: goal reached; half dot: some water.")
    recent = [d for day, rec in days.items() if (s.day - day).days < 30 for d in rec.drinks]
    with mix_col, st.container(key="glass-mix"):
        html('<p class="wb-h2">Your drinks</p>')
        mix = drinks.by_kind(recent)
        if mix:
            html(views.share_bars([(f"{drinks.drink_type(k).emoji} {drinks.drink_type(k).label}", v)
                                   for k, v in mix.items()]))
            html('<p class="wb-h2" style="font-size:1.15rem;margin-top:1rem">Time of day</p>')
            html(views.share_bars(list(insights.by_part(recent).items())))
        else:
            html(views.observation_list([]))
    with log_col, st.container(key="glass-entries"):
        html('<p class="wb-h2">Today</p>')
        html(views.drink_log(s.drinks, s.goal))
        rows = [f"{d.at.isoformat(timespec='minutes')},{d.ml},{d.kind}"
                for day in sorted(days) for d in days[day].drinks]
        if rows:
            st.download_button("Download all my drinks (CSV)", "time,ml,drink\n" + "\n".join(rows),
                               file_name=f"waterbuddy-{s.day}.csv", mime="text/csv", icon=":material/download:")


# ---------- Badges ----------

def page_badges() -> None:
    s = st.session_state
    earned = len([b for b in achievements.BADGES if b.key in s.badges])
    with st.container(key="glass-badges"):
        html('<p class="wb-eyebrow">Badges</p>'
             f'<p class="wb-h2" style="font-size:2.2rem">{earned} of {len(achievements.BADGES)} earned</p>'
             '<p class="wb-lead">Small moments worth noticing. Badges are never taken away, there are no '
             "streaks to keep up, and none of them rewards drinking more than your goal.</p>")
        html(views.badge_grid(achievements.BADGES, s.badges))


# ---------- Main ----------

def main() -> None:
    init_state()
    update_goal()
    html(f"<style>{stylesheet()}</style>")
    sidebar()
    if st.session_state.large_text:
        html("<style>.stMarkdown p, .stMarkdown li, label p { font-size: 1.15em !important; }</style>")
    show_flash()
    page = top_bar()
    found = stage(page)
    s = st.session_state
    if not s.saved_loaded:
        page_loading()
    elif page == "Today":
        page_today() if group() else page_welcome()
    elif page == "Atlas":
        page_atlas(found)
    elif page == "Insights":
        page_insights()
    else:
        page_badges()

    # Save to (or read from) this browser. Last on the page, so it saves this run's changes too.
    if s.clear_store:
        browser_storage("__clear__")
        s.clear_store = False
    else:
        loaded, raw = browser_storage(snapshot() if s.saved_loaded else None)
        if loaded and not s.saved_loaded:
            s.saved_loaded = True
            s.pending = store.from_json(raw)
            st.rerun()


main()
