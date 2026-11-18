"""App themes. Each one changes the mood of Ripple's world as well as the accent colours.

The 3D spring is tinted with a CSS filter and a light overlay (cheap: no second scene), and some
themes add a few drifting particles: fireflies at night, petals in Blossom. Panels stay light so
text keeps its contrast; every accent below passes WCAG AA as white-on-accent (buttons) and as
accent-on-panel (labels), checked against the scene's darkest shadow.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Theme:
    key: str
    label: str
    emoji: str
    accent: str        # bars, borders, found chips
    accent_deep: str   # buttons and small coloured text (AA on the panels and with white text)
    glow: str          # soft highlight
    world_filter: str  # CSS filter on the 3D spring
    overlay: str       # CSS background laid over the spring
    particles: str     # "", "fireflies" or "petals"


THEMES: dict[str, Theme] = {
    t.key: t
    for t in [
        Theme("spring", "Spring", "🌿", "#1e8c8a", "#136866", "#5fd3d0", "none", "none", ""),
        Theme("sunset", "Sunset", "🌅", "#d0643c", "#a63f27", "#ffb38a",
              "sepia(0.3) saturate(1.35) hue-rotate(-14deg) brightness(1.04)",
              "linear-gradient(180deg, rgba(255, 150, 90, 0.30), rgba(255, 196, 120, 0.06) 55%, rgba(120, 40, 60, 0.18))",
              ""),
        Theme("moonlight", "Moonlight", "🌙", "#5a67d8", "#3d47a8", "#9db4ff",
              "brightness(0.5) saturate(0.7) hue-rotate(18deg) contrast(1.08)",
              "radial-gradient(900px 500px at 75% 10%, rgba(170, 190, 255, 0.22), transparent 70%), rgba(14, 22, 64, 0.35)",
              "fireflies"),
        Theme("blossom", "Blossom", "🌸", "#d0578e", "#a8336b", "#ffb3cf",
              "saturate(1.08) brightness(1.05) hue-rotate(-8deg)",
              "linear-gradient(180deg, rgba(255, 182, 210, 0.30), rgba(255, 220, 235, 0.10) 60%, transparent)",
              "petals"),
    ]
}


def theme(key: str) -> Theme:
    return THEMES.get(key, THEMES["spring"])


def css(t: Theme) -> str:
    """The theme's colours and its effect on the spring behind the page."""
    return (
        "<style>"
        f":root {{ --jade: {t.accent}; --jade-deep: {t.accent_deep}; --aqua: {t.glow}; }}"
        f".st-key-stage iframe, .st-key-stage-explore iframe {{ filter: {t.world_filter}; }}"
        "</style>"
    )


def overlay(t: Theme, reduced: bool) -> str:
    """The light laid over the spring, plus drifting particles for some themes."""
    if t.overlay == "none" and not t.particles:
        return ""
    bits = ""
    if t.particles and not reduced:
        cls = "wb-firefly" if t.particles == "fireflies" else "wb-petal"
        count = 18 if t.particles == "fireflies" else 14
        bits = "".join(
            f'<i class="{cls}" style="left:{(i * 53) % 100}%;top:{(i * 37) % 90 + 5}%;'
            f'animation-delay:{(i * 0.71) % 6:.2f}s;animation-duration:{7 + (i % 5) * 1.6:.1f}s"></i>'
            for i in range(count)
        )
    background = "" if t.overlay == "none" else f' style="background:{t.overlay}"'
    return f'<div class="wb-mood" aria-hidden="true"{background}>{bits}</div>'
