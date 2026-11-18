"""Drink types: what someone can log, and the caffeine that comes with it.

Every drink here counts fully toward the day's fluids. Water, tea, coffee, milk and juice are all
part of "water from beverages" in the reference values (EFSA 2010), and studies of how well drinks
hydrate find tea and coffee at normal amounts close to water (Maughan et al. 2016). So the goal is
never discounted by drink; what changes is the caffeine and, for juice, the sugar note.

Caffeine amounts are approximate (USDA FoodData Central typical values, rounded); they vary a lot
with how a drink is made. Limits are from EFSA's 2015 opinion on caffeine safety: up to 400 mg a
day for healthy adults, and about 3 mg per kg of body weight a day for children and teenagers.
"""

from dataclasses import dataclass

from waterbuddy.tracker import Drink


@dataclass(frozen=True)
class DrinkType:
    key: str
    label: str
    emoji: str
    caffeine_per_250ml: int   # mg, approximate
    note: str = ""


DRINKS: dict[str, DrinkType] = {
    d.key: d
    for d in [
        DrinkType("water", "Water", "💧", 0),
        DrinkType("tea", "Tea or chai", "🍵", 40, "About 40 mg of caffeine per cup; it varies with strength."),
        DrinkType("coffee", "Coffee", "☕", 90, "About 90 mg of caffeine per cup; instant has less, espresso more."),
        DrinkType("milk", "Milk", "🥛", 0),
        DrinkType("juice", "Juice", "🧃", 0, "Counts toward your fluids, but it also adds sugar. Water is the everyday choice."),
        DrinkType("buttermilk", "Buttermilk", "🫗", 0),
        DrinkType("coconut", "Coconut water", "🥥", 0),
    ]
}

ADULT_CAFFEINE_LIMIT_MG = 400
CAFFEINE_SOURCE = ("EFSA Scientific Opinion on the safety of caffeine (2015)",
                   "https://www.efsa.europa.eu/en/efsajournal/pub/4102")


def drink_type(key: str) -> DrinkType:
    return DRINKS.get(key, DRINKS["water"])


def caffeine_mg(drinks: list[Drink]) -> int:
    """Approximate caffeine in these drinks."""
    return round(sum(drink_type(d.kind).caffeine_per_250ml * d.ml / 250 for d in drinks))


def caffeine_note(mg: int, child: bool) -> str | None:
    """A gentle note about today's caffeine, or None when there's nothing to say."""
    if mg <= 0:
        return None
    if child:
        return (f"About {mg} mg of caffeine today. Children are better off with water, milk and other "
                "caffeine-free drinks; ask a grown-up about tea and coffee.")
    if mg > ADULT_CAFFEINE_LIMIT_MG:
        return (f"About {mg} mg of caffeine today, more than the {ADULT_CAFFEINE_LIMIT_MG} mg a day "
                "considered safe for most healthy adults. Water or milk is a good next drink.")
    return f"About {mg} mg of caffeine today (most healthy adults: up to {ADULT_CAFFEINE_LIMIT_MG} mg a day)."


def by_kind(drinks: list[Drink]) -> dict[str, int]:
    """Millilitres per drink type, largest first."""
    out: dict[str, int] = {}
    for d in drinks:
        out[d.kind] = out.get(d.kind, 0) + d.ml
    return dict(sorted(out.items(), key=lambda kv: -kv[1]))
