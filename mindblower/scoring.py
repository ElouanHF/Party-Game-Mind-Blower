"""Points per mark, the Mind blown giver bonus, totals and per-player breakdowns."""
from __future__ import annotations

from typing import Iterable

from . import config
from .models import Answer, Mark, Player

# Multiplier of the category's points for each mark.
MARK_MULTIPLIER = {
    Mark.CORRECT: 1.0,
    Mark.PARTLY: 0.5,
    Mark.WRONG: 0.0,
    Mark.MIND_BLOWN: 2.0,
}

# Marks that count as "right" for the share-based awards.
RIGHT_MARKS = {Mark.CORRECT, Mark.PARTLY, Mark.MIND_BLOWN}


def answer_points(answer: Answer) -> float:
    if answer.mark is None:
        return 0.0
    return config.CATEGORY_BY_KEY[answer.category].points * MARK_MULTIPLIER[answer.mark]


def giver_bonus(player: Player) -> float:
    return float(player.mind_blowns_given * config.MIND_BLOWN_GIVER_BONUS)


def breakdown(player: Player, answers: Iterable[Answer]) -> dict:
    """Everything the personal results screen shows."""
    own = [a for a in answers if a.asker_id == player.id]
    count = {m: sum(1 for a in own if a.mark == m) for m in Mark}
    answer_total = sum(answer_points(a) for a in own)
    bonus = giver_bonus(player)
    return {
        "submitted": len(own),
        "correct": count[Mark.CORRECT],
        "partly": count[Mark.PARTLY],
        "wrong": count[Mark.WRONG],
        "mind_blown": count[Mark.MIND_BLOWN],
        "giver_bonus": bonus,
        "points": round(answer_total + bonus, 1),
    }


def totals(players: Iterable[Player], answers: list[Answer]) -> dict[str, float]:
    return {p.id: breakdown(p, answers)["points"] for p in players}


def ranked(players: Iterable[Player], answers: list[Answer]) -> list[dict]:
    """Players best first. Ties share a rank (1, 2, 2, 4...)."""
    rows = sorted(
        ({"player": p, **breakdown(p, answers)} for p in players),
        key=lambda r: (-r["points"], r["player"].name.lower()),
    )
    rank = 0
    previous = None
    for position, row in enumerate(rows, start=1):
        if row["points"] != previous:
            rank = position
            previous = row["points"]
        row["rank"] = rank
    return rows
