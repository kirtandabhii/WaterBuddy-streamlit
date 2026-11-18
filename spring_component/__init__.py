"""Ripple's 3D spring as a Streamlit custom component.

The spring is a React + three.js page (in `frontend/`), reused from the WaterBuddy web app.
Streamlit shows it in an iframe and passes it the day's numbers on every rerun. Python stays in
charge of the data: the component only draws it, pours each new drink from the bamboo spout,
and reports which things in the scene were tapped (for the Atlas quest). It never logs water.

The built files in `frontend/dist` are committed, because Streamlit Community Cloud runs
Python only. To work on the frontend, run `npm run dev` in `frontend/` and set
WATERBUDDY_SPRING_DEV=1 so Streamlit loads it from the Vite dev server instead.
"""

import os
from pathlib import Path
from typing import Any

import streamlit.components.v1 as components

_DIST = Path(__file__).parent / "frontend" / "dist"

if os.environ.get("WATERBUDDY_SPRING_DEV"):
    _component = components.declare_component("spring", url="http://localhost:5176")
else:
    _component = components.declare_component("spring", path=str(_DIST))


def spring(
    total_ml: int,
    goal_ml: int,
    *,
    explore: bool = False,
    pour: dict[str, Any] | None = None,
    height: int = 380,
    framing: tuple[float, float, float] | None = None,
    framing_narrow: tuple[float, float, float] | None = None,
    framing_explore: tuple[float, float, float] | None = None,
    reduced: bool = False,
    sound: bool = False,
    key: str | None = None,
) -> list[str]:
    """Show the spring and return the things found in it so far (ripple, water, pad, spout).

    `pour` describes the drink just logged: {"id", "from_ml", "to_ml", "reached_goal", "past_goal"}.
    A new `id` makes the spout pour it; the same id again does nothing, so reruns never repeat a pour.
    `height=0` fills the whole window, so the app can show the spring behind everything.
    `framing` / `framing_narrow` move the camera ([x, y, distance]) on wide and phone-width screens.
    """
    value = _component(
        total_ml=int(total_ml),
        goal_ml=int(goal_ml),
        explore=explore,
        pour=pour,
        height=int(height),
        framing=list(framing) if framing else None,
        framing_narrow=list(framing_narrow) if framing_narrow else None,
        framing_explore=list(framing_explore) if framing_explore else None,
        reduced=reduced,
        sound=sound,
        key=key,
        default=None,
    )
    if isinstance(value, dict):
        return [str(x) for x in value.get("found", [])]
    return []
