"""Every tunable number in one place.

Change values here rather than hunting through the code.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Category:
    key: str
    name: str
    points: int
    blurb: str  # one short line shown under the category button


# Ordered easiest -> hardest. Points are for a Correct mark.
CATEGORIES = (
    Category("small_talk", "Small Talk", 1, "Comes up in any chat"),
    Category("digging", "Digging", 2, "Needs a bit of steering"),
    Category("detective", "Detective", 3, "Nobody brings it up"),
    Category("top_secret", "Top Secret", 4, "A bit shy to admit"),
)
CATEGORY_BY_KEY = {c.key: c for c in CATEGORIES}

# Players
MIN_PLAYERS = 3
NAME_MAX_LENGTH = 20

# Party phase
START_SKIPS = 3
MAX_SKIPS = 3
MAX_OPEN_QUESTIONS_PER_SUBJECT = 2  # avoid mobbing one person
ANSWER_MAX_LENGTH = 100
GRACE_SECONDS = 30

# Review phase
MIND_BLOWNS_PER_MARKER = 3
MIND_BLOWN_GIVER_BONUS = 1  # points to the marker for each Mind blown handed out

# Awards
AWARD_MIN_ANSWERS = 3  # for the "share marked right" awards and Quick Draw

# Selfies
SELFIE_MAX_BYTES = 3 * 1024 * 1024
SELFIE_TYPES = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}
