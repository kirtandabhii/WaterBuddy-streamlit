"""What Ripple says: mood by progress, milestone messages and daily tips, worded for each age."""

import random
from datetime import date

# (minimum percent, emoji, line for children, line for everyone else)
MOODS = [
    (100, "🎉", "You did it! Ripple's spring is full!", "Goal reached. Nice work today."),
    (75, "🤩", "Almost there! Ripple is doing a happy wiggle!", "Three quarters done. The finish is close."),
    (50, "😄", "Halfway! Ripple's spring is half full!", "Halfway there. Keep sipping through the day."),
    (25, "🙂", "Good start! The water is rising!", "A good start. A glass with your next meal keeps it going."),
    (1, "💧", "First sips! Ripple noticed!", "You've started. Small sips add up."),
    (0, "🐟", "Ripple is waiting by the spring. Ready for your first glass?", "Ready when you are. Log your first drink."),
]

MILESTONE_MESSAGES = {
    25: ("Great! You reached 25%! 🌱", "25% of your goal. Good start."),
    50: ("Great! You reached 50%! 🌊", "Halfway: 50% of your goal."),
    75: ("Wow, 75%! Nearly there! ⭐", "75% done. Nearly there."),
    100: ("You reached your goal! Ripple is celebrating! 🎉", "Goal reached for today. Well done."),
}

PAST_GOAL = ("You've reached your goal already. Only drink more if you're thirsty! 💙",
             "Goal reached. No need for more unless you're thirsty.")

TIPS = [
    "Water in food counts too: fruit, vegetables, dal, curd and soups all add to your day.",
    "Feeling thirsty is a fine signal to drink. There's no need to force water down when you aren't.",
    "Hot days and exercise raise how much you need. Sip a little more then, and have a glass after a workout.",
    "Keep a bottle where you can see it: on your desk, by your bed or in your bag.",
    "Pale straw-coloured urine usually means you're drinking enough. Very dark can mean you need more.",
    "Small sips through the day are easier on your body than a lot at once.",
    "Tea, coffee and milk count toward your fluids as well. Plain water is the easiest everyday choice.",
    "More isn't better. Once you've reached your goal for the day, you're done.",
    "A glass with each meal is an easy habit to hang on to.",
    "Children and older people often feel less thirsty. Offering water with meals and snacks helps.",
    "If a doctor has given you a fluid limit, use that as your goal. It matters more than any app's suggestion.",
    "Sugary and energy drinks add fluid but also sugar. Water is the everyday default.",
    "Water doesn't need to be cold. Drink it however you like it.",
    "Feeling unwell with vomiting, diarrhoea or fever? Small, frequent sips help; see a doctor if it lasts.",
]


def mood(pct: int, child: bool) -> tuple[str, str]:
    """Ripple's emoji and line for the current percentage."""
    for minimum, emoji, kid_line, line in MOODS:
        if pct >= minimum:
            return emoji, kid_line if child else line
    return MOODS[-1][1], MOODS[-1][2] if child else MOODS[-1][3]


def milestone_message(milestone: int, child: bool) -> str:
    kid_line, line = MILESTONE_MESSAGES[milestone]
    return kid_line if child else line


def past_goal_message(child: bool) -> str:
    return PAST_GOAL[0] if child else PAST_GOAL[1]


def tip_of_the_day(day: date) -> str:
    """The same tip all day, the next one tomorrow."""
    return TIPS[day.toordinal() % len(TIPS)]


def random_tip(exclude: str | None = None, rng: random.Random | None = None) -> str:
    """A different tip at random (for the "Another tip" button)."""
    choices = [t for t in TIPS if t != exclude] or TIPS
    return (rng or random).choice(choices)
