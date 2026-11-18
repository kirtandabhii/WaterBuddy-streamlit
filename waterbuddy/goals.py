"""Age groups and their suggested daily goals.

The numbers are suggestions for drinks (not total water), taken from the WaterBuddy web app's
goal table: EFSA 2010 adequate intakes for total water, assuming about a fifth comes from food,
and India's NIN 2024 guideline for adults. A goal is a starting point, never a prescription.
"""

from dataclasses import dataclass

EFSA_2010 = ("EFSA Scientific Opinion on Dietary Reference Values for water (2010)",
             "https://www.efsa.europa.eu/en/efsajournal/pub/1459")
NIN_2024 = ("ICMR-NIN Dietary Guidelines for Indians 2024, Guideline 14",
            "https://www.nin.res.in/dietaryguidelines/pdfjs/locale/DGI_2024.pdf")


@dataclass(frozen=True)
class AgeGroup:
    key: str
    label: str
    suggested_ml: int
    low_ml: int   # outside this range, the app asks "are you sure?"
    high_ml: int
    child: bool   # under 14: friendlier wording, and a grown-up should help set the goal
    why: str
    source: tuple[str, str]


AGE_GROUPS: list[AgeGroup] = [
    AgeGroup("4-8", "4 to 8 years", 1250, 800, 1800, True,
             "About 1.6 L of total water a day is the reference for ages 4 to 8. "
             "With about a fifth from food, that leaves roughly 1.25 L from drinks.", EFSA_2010),
    AgeGroup("9-13", "9 to 13 years", 1600, 1000, 2400, True,
             "About 1.9 L (girls) to 2.1 L (boys) of total water a day is the reference for ages 9 to 13. "
             "That is roughly 1.6 L from drinks.", EFSA_2010),
    AgeGroup("14-17", "14 to 17 years", 1800, 1200, 3000, False,
             "From 14, adult references apply: about 2.0 L (women) to 2.5 L (men) of total water a day. "
             "That is roughly 1.6 to 2.0 L from drinks.", EFSA_2010),
    AgeGroup("18-64", "18 to 64 years", 2000, 1200, 3500, False,
             "India's NIN 2024 guideline describes about 2 L of water a day for a healthy adult, "
             "and more in hot weather or with hard exercise.", NIN_2024),
    AgeGroup("65+", "65 or older", 1800, 1000, 3000, False,
             "Older adults use the same references as other adults: about 2.0 to 2.5 L of total water "
             "a day, roughly 1.6 to 2.0 L from drinks. Thirst can be weaker with age, so regular sips help.",
             EFSA_2010),
]

MIN_GOAL_ML = 500
MAX_GOAL_ML = 5000


def group_by_key(key: str) -> AgeGroup:
    for group in AGE_GROUPS:
        if group.key == key:
            return group
    raise KeyError(key)


def suggested_goal(key: str) -> int:
    return group_by_key(key).suggested_ml


def goal_is_unusual(goal_ml: int, key: str) -> bool:
    """True when a goal is outside the usual range for this age group (the app asks to confirm)."""
    group = group_by_key(key)
    return goal_ml < group.low_ml or goal_ml > group.high_ml
