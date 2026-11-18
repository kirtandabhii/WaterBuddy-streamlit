"""The water-level staff gauge: WaterBuddy's progress display.

Springs and rivers are measured with a staff gauge, a painted board with E-shaped marks that the
water rises up. Here the board runs from 0 at the bottom to the day's goal at the top, the water
climbs it as drinks are logged, and the quarter marks light up as they are passed.
"""

from waterbuddy.units import litres

TOP = 40        # y of the goal line on the board
BOTTOM = 440    # y of zero
BOARD_X, BOARD_W = 30, 76
BANDS = 10      # one E-shaped band per tenth of the goal


def level_y(total_ml: int, goal_ml: int) -> float:
    """The y coordinate of the water surface: BOTTOM when empty, TOP at (or past) the goal."""
    frac = 0.0 if goal_ml <= 0 else min(1.0, max(0.0, total_ml / goal_ml))
    return BOTTOM - frac * (BOTTOM - TOP)


def quarter_marks(goal_ml: int) -> list[tuple[int, str, int]]:
    """(percent, label, ml) for each labelled mark on the board."""
    return [(25, "¼", goal_ml // 4), (50, "½", goal_ml // 2), (75, "¾", goal_ml * 3 // 4), (100, "Goal", goal_ml)]


def _e_band(i: int) -> str:
    """One E-shaped marking: a spine with three teeth, alternating colours like a real gauge."""
    band_h = (BOTTOM - TOP) / BANDS
    y0 = BOTTOM - (i + 1) * band_h
    colour = "#123a40" if i % 2 == 0 else "#1e8c8a"
    tooth = band_h / 5
    x = BOARD_X + 8
    parts = [f'<rect x="{x}" y="{y0:.1f}" width="7" height="{band_h:.1f}" fill="{colour}"/>']
    for k in (0, 2, 4):
        parts.append(f'<rect x="{x}" y="{y0 + k * tooth:.1f}" width="26" height="{tooth:.1f}" fill="{colour}"/>')
    return "".join(parts)


def gauge_svg(total_ml: int, goal_ml: int, *, from_ml: int | None = None, still: bool = False) -> str:
    """The gauge as one line of SVG. `from_ml` animates the water up from an earlier level."""
    to_y = level_y(total_ml, goal_ml)
    from_y = level_y(from_ml, goal_ml) if from_ml is not None else to_y
    pct = 0 if goal_ml <= 0 else min(100, total_ml * 100 // goal_ml)
    label = f"Water level: {total_ml:,} ml of {goal_ml:,} ml, {pct}% of today's goal"

    marks = []
    for p, text, ml in quarter_marks(goal_ml):
        y = BOTTOM - p / 100 * (BOTTOM - TOP)
        reached = pct >= p
        cls = "wb-mark on" if reached else "wb-mark"
        amount = litres(ml) if p == 100 else f"{ml:,}"
        marks.append(
            f'<g class="{cls}"><line x1="{BOARD_X + BOARD_W - 30}" x2="{BOARD_X + BOARD_W}" y1="{y:.1f}" y2="{y:.1f}"/>'
            f'<text class="wb-mark-big" x="{BOARD_X + BOARD_W + 8}" y="{y + 6:.1f}">{text}</text>'
            f'<text class="wb-mark-ml" x="{BOARD_X + BOARD_W + 8}" y="{y + 22:.1f}">{amount}</text></g>'
        )

    # The water: a wide repeating wave over a deep body, clipped to the board.
    wave = "M-120 0 " + " ".join("q15 -7 30 0 t30 0" for _ in range(9)) + " V500 H-120 Z"
    water = (
        f'<g class="wb-water" style="--from:{from_y:.1f}px;--to:{to_y:.1f}px;transform:translateY({to_y:.1f}px)">'
        f'<path class="wb-wave wb-wave-back" d="{wave}"/>'
        f'<path class="wb-wave wb-wave-front" d="{wave}"/></g>'
    )
    board = f'<rect x="{BOARD_X}" y="20" width="{BOARD_W}" height="{BOTTOM - 20 + 6}" rx="6"'
    return (
        f'<svg class="wb-gauge{" wb-still" if still else ""}" viewBox="0 0 160 470" role="img" aria-label="{label}">'
        f'<defs><clipPath id="wb-board-clip">{board}/></clipPath></defs>'
        f'<rect x="{BOARD_X + BOARD_W / 2 - 5}" y="440" width="10" height="30" fill="#7a5a33"/>'
        f'{board} class="wb-board"/>'
        f'<g clip-path="url(#wb-board-clip)">{"".join(_e_band(i) for i in range(BANDS))}{water}</g>'
        f'{board} class="wb-board-edge"/>'
        f'{"".join(marks)}'
        f'</svg>'
    )
