"""Plain data objects. No game rules live here."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from . import config


class Phase(str, Enum):
    LOBBY = "lobby"
    PARTY = "party"
    GRACE = "grace"          # 30 s to finish the question you're holding
    REVIEW = "review"        # everyone marks the answers about them
    HIGHLIGHTS = "highlights"  # Mind blown answers their authors chose to show
    RESULTS = "results"      # awards, then the podium, then the leaderboard


class Mark(str, Enum):
    CORRECT = "correct"
    PARTLY = "partly"
    WRONG = "wrong"
    MIND_BLOWN = "mind_blown"


@dataclass(frozen=True)
class Question:
    id: str
    category: str  # a key from config.CATEGORY_BY_KEY
    text: str      # contains "{player}" where the subject's name goes


@dataclass
class Assignment:
    """One question handed to one player, waiting for an answer."""
    id: str
    asker_id: str
    subject_id: str
    question_id: str
    category: str
    given_at: float


@dataclass
class Answer:
    id: str
    asker_id: str     # who wrote the answer (the author)
    subject_id: str   # who the question was about (the marker)
    question_id: str
    category: str
    text: str
    given_at: float
    submitted_at: float
    mark: Optional[Mark] = None
    show_on_tv: Optional[bool] = None  # author's Highlights choice; None = not chosen yet

    @property
    def seconds_taken(self) -> float:
        return self.submitted_at - self.given_at


@dataclass
class Player:
    id: str
    name: str
    selfie_url: str
    joined_at: float
    is_host: bool = False
    is_bot: bool = False
    skips: int = config.START_SKIPS
    skips_used: int = 0
    mind_blowns_left: int = config.MIND_BLOWNS_PER_MARKER
    all_mind_blowns_given_at: Optional[float] = None  # for the Hype Squad award
    current: Optional[Assignment] = None               # the question they're holding
    last_subject_id: Optional[str] = None              # never the same person twice in a row
    connections: int = 0                               # open browser tabs for this player
    mark_history: list = field(default_factory=list)   # answer ids, newest last, for Undo

    @property
    def connected(self) -> bool:
        return self.is_bot or self.connections > 0

    @property
    def mind_blowns_given(self) -> int:
        return config.MIND_BLOWNS_PER_MARKER - self.mind_blowns_left
