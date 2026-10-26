"""One small function per award.

Each function gets the players and answers and returns a list of
(player, subtext) winners. An empty list means nobody qualifies, and the
award is not shown. Ties share the award (up to AWARD_MAX_WINNERS people,
otherwise it's skipped because it wouldn't mean much); a player can win several.
"""
from __future__ import annotations

from fractions import Fraction
from typing import Callable

from . import config
from .models import Answer, Mark, Player
from .scoring import RIGHT_MARKS

Winners = list[tuple[Player, str]]


# ---------------------------------------------------------------- helpers

def _pick(scored: list[tuple[Player, object]], best: str) -> list[tuple[Player, object]]:
    """Players with the highest ('most') or lowest ('least') value.

    Returns nobody when every eligible player is tied, because then the
    award wouldn't mean anything.
    """
    if not scored:
        return []
    values = [v for _, v in scored]
    target = max(values) if best == "most" else min(values)
    winners = [(p, v) for p, v in scored if v == target]
    if len(scored) > 1 and len(winners) == len(scored):
        return []
    return winners


def _most_count(players: list[Player], count: Callable[[Player], int], label: str) -> Winners:
    """Whoever has the highest count (at least 1). Everyone at 0 counts towards 'all tied'."""
    scored = [(p, count(p)) for p in players]
    return [(p, f"{label}: {v}") for p, v in _pick(scored, "most") if v > 0]


def _own(answers: list[Answer], player: Player) -> list[Answer]:
    return [a for a in answers if a.asker_id == player.id]


def _about(answers: list[Answer], player: Player) -> list[Answer]:
    return [a for a in answers if a.subject_id == player.id]


def _right(answers: list[Answer]) -> int:
    return sum(1 for a in answers if a.mark in RIGHT_MARKS)


def _share_award(players, answers_for, best: str, label: str) -> Winners:
    scored = []
    for p in players:
        group = answers_for(p)
        if len(group) >= config.AWARD_MIN_ANSWERS:
            scored.append((p, Fraction(_right(group), len(group))))
    winners = _pick(scored, best)
    return [(p, f"{label}: {_right(answers_for(p))} of {len(answers_for(p))}") for p, _ in winners]


def format_duration(seconds: float) -> str:
    seconds = int(round(seconds))
    if seconds < 60:
        return f"{seconds} s"
    minutes, rest = divmod(seconds, 60)
    return f"{minutes} min {rest} s" if rest else f"{minutes} min"


# ---------------------------------------------------------------- the awards

def social_butterfly(players, answers) -> Winners:
    return _most_count(players, lambda p: len(_own(answers, p)), "Most answers submitted")


def mind_blower(players, answers) -> Winners:
    return _most_count(
        players,
        lambda p: sum(1 for a in _own(answers, p) if a.mark == Mark.MIND_BLOWN),
        "Most Mind blowns received",
    )


def hype_squad(players, answers) -> Winners:
    done = [(p, p.all_mind_blowns_given_at) for p in players if p.all_mind_blowns_given_at is not None]
    if not done:
        return []
    first = min(t for _, t in done)
    return [(p, f"First to hand out all {config.MIND_BLOWNS_PER_MARKER} Mind blowns")
            for p, t in done if t == first]


def daredevil(players, answers) -> Winners:
    return _most_count(
        players,
        lambda p: sum(1 for a in _own(answers, p) if a.category == "top_secret"),
        "Most Top Secret answers submitted",
    )


def quick_draw(players, answers) -> Winners:
    scored = []
    for p in players:
        own = _own(answers, p)
        if len(own) >= config.AWARD_MIN_ANSWERS:
            average = sum(a.seconds_taken for a in own) / len(own)
            scored.append((p, round(average)))
    return [(p, f"Fastest average answer: {format_duration(v)}") for p, v in _pick(scored, "least")]


def close_enough(players, answers) -> Winners:
    return _most_count(
        players,
        lambda p: sum(1 for a in _own(answers, p) if a.mark == Mark.PARTLY),
        "Most Partly right marks received",
    )


def picky_picker(players, answers) -> Winners:
    return _most_count(players, lambda p: p.skips_used, "Most skips used")


def most_wanted(players, answers) -> Winners:
    return _most_count(players, lambda p: len(_about(answers, p)), "Most questions asked about them")


def open_book(players, answers) -> Winners:
    return _share_award(players, lambda p: _about(answers, p), "most", "Most often guessed right")


def most_mysterious(players, answers) -> Winners:
    return _share_award(players, lambda p: _about(answers, p), "least", "Least often guessed right")


def were_you_even_listening(players, answers) -> Winners:
    return _share_award(players, lambda p: _own(answers, p), "least", "Fewest answers marked right")


# (key, title, function) in the order they are revealed.
AWARDS = [
    ("social_butterfly", "Social Butterfly", social_butterfly),
    ("mind_blower", "Mind Blower", mind_blower),
    ("hype_squad", "Hype Squad", hype_squad),
    ("daredevil", "Daredevil", daredevil),
    ("quick_draw", "Quick Draw", quick_draw),
    ("close_enough", "Close Enough", close_enough),
    ("picky_picker", "Picky Picker", picky_picker),
    ("most_wanted", "Most Wanted", most_wanted),
    ("open_book", "Open Book", open_book),
    ("most_mysterious", "Most Mysterious", most_mysterious),
    ("were_you_even_listening", "Were You Even Listening?", were_you_even_listening),
]


def compute_awards(players: list[Player], answers: list[Answer]) -> list[dict]:
    """All awards with winners, in reveal order, ending with Decorated."""
    results = []
    for key, title, fn in AWARDS:
        winners = fn(players, answers)
        if 0 < len(winners) <= config.AWARD_MAX_WINNERS:
            results.append({
                "key": key,
                "title": title,
                "winners": [{"player_id": p.id, "subtext": text} for p, text in winners],
            })

    # Decorated: most awards won (needs at least 2).
    tally = {p.id: 0 for p in players}
    for award in results:
        for w in award["winners"]:
            tally[w["player_id"]] += 1
    decorated = [(p, v) for p, v in _pick([(p, tally[p.id]) for p in players], "most") if v >= 2]
    if 0 < len(decorated) <= config.AWARD_MAX_WINNERS:
        results.append({
            "key": "decorated",
            "title": "Decorated",
            "winners": [{"player_id": p.id, "subtext": f"Most awards: {v}"} for p, v in decorated],
        })
    return results