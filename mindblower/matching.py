"""Chooses who to ask about and which question to ask. Pure functions, no state.

Rules (from the design doc):
- never yourself, never someone disconnected, never the same person twice in a row
- prefer people this player has asked about least, then people the room has asked about least
- avoid anyone with MAX_OPEN_QUESTIONS_PER_SUBJECT open questions about them (relaxed if needed)
- each question is asked about each person at most once per game
"""
from __future__ import annotations

import random
from collections import Counter
from typing import Iterable, Optional

from . import config
from .models import Player, Question


def available_by_subject(
    asker: Player,
    players: Iterable[Player],
    category_questions: list[Question],
    taken: set[tuple[str, str]],
) -> dict[str, list[Question]]:
    """For each person you could ask about, the questions still free for them."""
    result: dict[str, list[Question]] = {}
    for p in players:
        if p.id == asker.id or not p.connected:
            continue
        free = [q for q in category_questions if (p.id, q.id) not in taken]
        if free:
            result[p.id] = free
    return result


def choose(
    asker: Player,
    players: Iterable[Player],
    category_questions: list[Question],
    taken: set[tuple[str, str]],
    open_counts: Counter,
    pair_counts: Counter,
    subject_counts: Counter,
    seen_question_ids: set[str],
    rng: random.Random,
) -> Optional[tuple[str, Question]]:
    """Returns (subject_id, question) or None if nothing is left in this category."""
    options = available_by_subject(asker, players, category_questions, taken)
    if not options:
        return None

    ids = sorted(options)  # sorted so a seeded rng gives repeatable results
    ids = [i for i in ids if i != asker.last_subject_id] or ids
    ids = [i for i in ids if open_counts[i] < config.MAX_OPEN_QUESTIONS_PER_SUBJECT] or ids

    def fairness(subject_id: str) -> tuple[int, int]:
        return pair_counts[(asker.id, subject_id)], subject_counts[subject_id]

    best = min(fairness(i) for i in ids)
    subject_id = rng.choice([i for i in ids if fairness(i) == best])

    free = options[subject_id]
    fresh = [q for q in free if q.id not in seen_question_ids] or free
    return subject_id, rng.choice(fresh)
