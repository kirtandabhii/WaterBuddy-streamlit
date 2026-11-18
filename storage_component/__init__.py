"""Saving WaterBuddy in the browser, between visits.

A tiny Streamlit component (plain HTML, no build step) that reads and writes the browser's
localStorage. Streamlit itself forgets everything when the tab is reloaded; this keeps the
person's goal, today's drinks, past days and badges on their own device. Nothing is sent to
a server.
"""

from pathlib import Path
from typing import Any

import streamlit.components.v1 as components

_component = components.declare_component("wb_storage", path=str(Path(__file__).parent / "frontend"))


def browser_storage(save: Any = None, *, key: str = "store") -> tuple[bool, Any]:
    """Returns (loaded, saved data). `save` is written to the browser when it's not None.

    `loaded` is False until the browser has answered (the first rerun after the page opens).
    Pass save="__clear__" to delete the saved data.
    """
    value = _component(save=save, key=key, default=None)
    if isinstance(value, dict) and value.get("loaded"):
        return True, value.get("data")
    return False, None
