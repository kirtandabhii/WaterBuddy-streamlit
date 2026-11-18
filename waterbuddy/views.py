"""Small HTML pieces for the Streamlit pages (styled by assets/style.css).

Each function returns a string; app.py passes it to st.markdown. Keeping them here keeps app.py
about layout and behaviour, and lets the tests check what they show.
"""

from datetime import date
from html import escape

from waterbuddy.goals import AgeGroup
from waterbuddy.summary import DaySummary
from waterbuddy.tracker import Drink
from waterbuddy.units import litres

DROP_ICON = (
    '<svg width="30" height="34" viewBox="0 0 30 34" aria-hidden="true">'
    '<path d="M15 2C15 2 3 15 3 22a12 12 0 0 0 24 0C27 15 15 2 15 2Z" fill="#1e8c8a"/>'
    '<path d="M9 22a6 6 0 0 0 6 6" stroke="#ffffff" stroke-width="2.4" stroke-linecap="round" fill="none"/></svg>'
)


def nice_date(day: date) -> str:
    """Saturday 15 November (written out, so it works the same on every server)."""
    return f"{day:%A} {day.day} {day:%B}"


def brand() -> str:
    return f'<div class="wb-brand">{DROP_ICON}<span>WaterBuddy</span></div>'


def date_line(day: date, group: AgeGroup | None) -> str:
    text = nice_date(day)
    return f'<div class="wb-date">{escape(text)}</div>'


def welcome_intro() -> str:
    return (
        '<div class="wb-welcome">'
        '<p class="wb-eyebrow">Daily water companion · every age</p>'
        "<h1>Fill Ripple&rsquo;s spring, <em>one glass at a time.</em></h1>"
        '<p class="wb-lead">Tell WaterBuddy your age and it suggests a daily goal you can change. '
        "Log each drink and watch the water rise on the gauge and in Ripple&rsquo;s spring.</p>"
        '<ul class="wb-promises">'
        "<li><b>Goal</b>Suggested from your age group, with its source</li>"
        "<li><b>Calm</b>No streaks to lose, and no reward for drinking past your goal</li>"
        "<li><b>Private</b>Saved only in this browser, never sent anywhere</li>"
        "</ul></div>"
    )


def age_tile_css(groups: list[AgeGroup]) -> str:
    """Each age tile's caption ("1.25 L a day"), added under the age range by CSS."""
    rules = "".join(
        f'.st-key-age-{g.key.replace("+", "plus")} button::after {{ content: "{litres(g.suggested_ml)}"; }}'
        for g in groups
    )
    return f"<style>{rules}</style>"


def reading(total: int, goal: int, pct: int, remaining: int) -> str:
    """The big number, what's left and a thin bar."""
    if remaining > 0:
        left = f"<b>{remaining:,} ml</b> to go"
    elif total > goal:
        left = f"<b>{total - goal:,} ml</b> over your goal"
    else:
        left = "<b>goal reached</b>"
    return (
        '<div class="wb-reading">'
        '<p class="wb-eyebrow">Drunk today</p>'
        f'<p class="wb-total">{total:,}<small>ml</small></p>'
        f'<p class="wb-of">of {litres(goal)} · <b>{pct}%</b> · {left}</p>'
        f'<div class="wb-bar" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow="{pct}">'
        f'<span style="width:{pct}%"></span></div></div>'
    )


def ripple_says(line: str, avatar_uri: str) -> str:
    return (
        '<div class="wb-says">'
        f'<div class="wb-avatar" role="img" aria-label="Ripple" style="background-image:url({avatar_uri})"></div>'
        f"<p><span>Ripple</span>{escape(line)}</p></div>"
    )


def goal_compare(group: AgeGroup, goal: int) -> str:
    """Suggested goal and the person's own goal as two bars on one scale."""
    scale = max(group.suggested_ml, goal) or 1
    return (
        '<div class="wb-compare">'
        f'<div><span>Suggested</span><i style="width:{group.suggested_ml * 100 / scale:.0f}%"></i>'
        f"<b>{litres(group.suggested_ml)}</b></div>"
        f'<div class="you"><span>Your goal</span><i style="width:{goal * 100 / scale:.0f}%"></i>'
        f"<b>{litres(goal)}</b></div></div>"
    )


def drink_log(drinks: list[Drink], goal: int) -> str:
    """Today's drinks, newest first, each with its type; the one that reached the goal is marked."""
    from waterbuddy.drinks import drink_type

    if not drinks:
        return '<p class="wb-empty">Nothing yet. Your drinks will be listed here with the time you logged them.</p>'
    rows, running = [], 0
    for d in drinks:
        before, running = running, running + d.ml
        t = drink_type(d.kind)
        cls = ' class="goal"' if before < goal <= running else ""
        note = " · goal reached" if cls else ""
        rows.append(
            f"<li{cls}><time>{d.at.strftime('%H:%M')}</time>"
            f'<span class="wb-kind" title="{escape(t.label)}">{t.emoji} <span class="wb-kind-label">{escape(t.label)}</span></span>'
            f"<b>{d.ml:,} ml{note}</b></li>"
        )
    return '<ul class="wb-log">' + "".join(reversed(rows)) + "</ul>"


def quest(found: list[str], names: dict[str, str]) -> str:
    items = "".join(
        f'<li class="found"><i>✓</i>{escape(name)}</li>' if key in found else f"<li><i></i>{escape(name)}</li>"
        for key, name in names.items()
    )
    return (
        f'<p class="wb-count">{len(found)}<small> of {len(names)} found</small></p>'
        f'<ul class="wb-quest">{items}</ul>'
    )


def summary_head(s: DaySummary, day: date) -> str:
    return (
        '<div class="wb-summary-head">'
        f'<p class="wb-eyebrow">End of day · {nice_date(day)}</p>'
        f"<h1>{escape(s.headline)}</h1>"
        f'<p class="wb-lead">{escape(s.note)}</p></div>'
    )


def summary_stats(s: DaySummary) -> str:
    cells = [
        ("Drinks", str(s.drinks)),
        ("Average", f"{s.average_ml:,} ml" if s.drinks else "–"),
        ("Largest", f"{s.largest_ml:,} ml" if s.drinks else "–"),
        ("First", s.first or "–"),
        ("Last", s.last or "–"),
    ]
    inner = "".join(f"<div><dt>{k}</dt><dd>{v}</dd></div>" for k, v in cells)
    return f'<dl class="wb-stats">{inner}</dl>'


def splash(message: str) -> str:
    """The once-a-day goal moment: droplets fall and a card fades in and out."""
    drops = "".join(
        f'<i style="left:{(i * 37) % 100}%;animation-delay:{(i * 0.13) % 1.1:.2f}s"></i>'
        for i in range(36)
    )
    return f'<div class="wb-splash" aria-hidden="true">{drops}<p>{escape(message)}</p></div>'


def bubble(line: str, speaker: str = "Ripple") -> str:
    """Ripple's speech bubble, floating in the spring above its head."""
    return f'<div class="wb-bubble" role="status"><b>{escape(speaker)}</b>{escape(line)}</div>'


def dock_level(total: int, goal: int, pct: int) -> str:
    """The compact reading in the Atlas dock."""
    return f'<p class="wb-dock-level">{total:,} ml <small>of {litres(goal)} · {pct}%</small></p>'


def backdrop(image_uri: str) -> str:
    """A still picture of the spring behind the page, used when 3D is turned off."""
    return f'<div class="wb-backdrop" style="background-image:url({image_uri})"></div>'


def month_dots(points) -> str:
    """The last 30 days as dots: full for a day at goal, half for a day with some water."""
    cells = []
    for p in points:
        state = "full" if p.met else "half" if p.total > 0 else "empty"
        label = f"{nice_date(p.day)}: {p.total:,} ml" + (" (goal reached)" if p.met else "")
        cells.append(f'<li class="{state}" title="{escape(label)}"><span>{p.day.day}</span></li>')
    return f'<ol class="wb-dots" aria-label="Last 30 days">{"".join(cells)}</ol>'


def share_bars(rows: list[tuple[str, int]], unit: str = "ml") -> str:
    """Labelled horizontal bars that share one scale (drink mix, time of day)."""
    top = max((v for _, v in rows), default=0) or 1
    total = sum(v for _, v in rows) or 1
    items = "".join(
        f'<div><span>{escape(name)}</span><i style="width:{v * 100 / top:.0f}%"></i>'
        f"<b>{round(v * 100 / total)}%</b></div>"
        for name, v in rows
    )
    return f'<div class="wb-compare wb-share">{items}</div>'


def observation_list(notes: list[str]) -> str:
    if not notes:
        return ('<p class="wb-empty">Log a few drinks over a couple of days and patterns will show up here: '
                "when you drink most, your favourite drinks and how your week is going.</p>")
    return '<ul class="wb-notes">' + "".join(f"<li>{escape(n)}</li>" for n in notes) + "</ul>"


def badge_grid(badges, earned: dict) -> str:
    cards = []
    for b in badges:
        when = earned.get(b.key)
        if when:
            cards.append(
                f'<li class="earned"><span class="wb-badge-icon">{b.emoji}</span><b>{escape(b.title)}</b>'
                f"<small>{escape(b.how)}</small><em>Earned {nice_date(when)}</em></li>"
            )
        else:
            cards.append(
                f'<li><span class="wb-badge-icon">{b.emoji}</span><b>{escape(b.title)}</b>'
                f"<small>{escape(b.how)}</small><em>Not yet</em></li>"
            )
    return f'<ul class="wb-badges">{"".join(cards)}</ul>'


def badge_pop(badge) -> str:
    """The moment a badge is earned: it pops in, shines, and fades."""
    return (
        '<div class="wb-pop" aria-hidden="true"><div>'
        f'<span class="wb-pop-icon">{badge.emoji}</span>'
        f"<p>Badge earned</p><b>{escape(badge.title)}</b></div></div>"
    )
