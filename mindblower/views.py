"""Turns game state into exactly what each screen needs.

A "view" is a plain dict sent to a screen after every change. Screens draw
whatever the latest view says, so a phone that reconnects is instantly
back in sync. Nothing here changes the game.
"""
from __future__ import annotations

from typing import Optional

from . import config
from .game import Game
from .models import Mark, Phase, Player


def person(p: Player) -> dict:
    return {"id": p.id, "name": p.name, "selfie": p.selfie_url,
            "is_host": p.is_host, "connected": p.connected}


def category_view(key: str) -> dict:
    c = config.CATEGORY_BY_KEY[key]
    return {"key": c.key, "name": c.name, "points": c.points}


def host_actions(game: Game) -> list[dict]:
    """The buttons the host sees (on their phone and on the TV)."""
    def button(action, label, enabled=True):
        return {"action": action, "label": label, "enabled": enabled}

    if game.phase == Phase.LOBBY:
        return [button("start", "Start game", game.can_start)]
    if game.phase == Phase.PARTY:
        return [button("end", "End party")]
    if game.phase == Phase.REVIEW:
        any_shown = any(a.mark == Mark.MIND_BLOWN and a.show_on_tv for a in game.answers.values())
        label = "Show highlights" if any_shown else "Show results"
        return [button("highlights", label, game.all_marked)]
    if game.phase in (Phase.HIGHLIGHTS, Phase.RESULTS):
        if game.at_last_step:
            return [button("new_game", "New game")]
        return [button("next", "Next")]
    return []


def _ms(t: Optional[float]) -> Optional[int]:
    return None if t is None else int(t * 1000)


# ---------------------------------------------------------------- ending steps

def step_view(game: Game) -> Optional[dict]:
    step = game.current_step
    if step is None:
        return None
    kind = step["kind"]
    players = game.players

    if kind == "highlight":
        a = game.answers[step["answer_id"]]
        return {"kind": kind,
                "number": game.reveal_index + 1,
                "of": sum(1 for s in game.reveal if s["kind"] == "highlight"),
                "template": game.questions[a.question_id].text,
                "subject": person(players[a.subject_id]),
                "author": person(players[a.asker_id]),
                "text": a.text}

    if kind == "award":
        award = game.results["awards"][step["index"]]
        return {"kind": kind,
                "number": step["index"] + 1,
                "of": len(game.results["awards"]),
                "title": award["title"],
                "winners": [{**person(players[w["player_id"]]), "subtext": w["subtext"]}
                            for w in award["winners"]]}

    # Podium and leaderboard: show every podium place revealed so far.
    revealed = {s["place"] for s in game.reveal[: game.reveal_index + 1] if s["kind"] == "podium"}
    podium = [{"place": p["place"], "points": p["points"],
               "players": [person(players[i]) for i in p["player_ids"]],
               "revealed": p["place"] in revealed or kind == "leaderboard"}
              for p in game.results["podium"]]
    view = {"kind": kind, "podium": podium, "just_revealed": step.get("place")}
    if kind == "leaderboard":
        view["rows"] = [{**person(players[r["player_id"]]), "rank": r["rank"], "points": r["points"]}
                        for r in game.results["leaderboard"]]
    return view


# ---------------------------------------------------------------- TV

def tv_view(game: Game, join_url: str, qr_svg: str, controls: bool, dev: bool) -> dict:
    reviewing = game.phase == Phase.REVIEW
    view = {
        "screen": "tv",
        "phase": game.phase.value,
        "host_joined": game.host is not None,
        "join_url": join_url,
        "qr": qr_svg if game.host is not None else None,
        "min_players": config.MIN_PLAYERS,
        "total_answers": len(game.answers),
        "players": [{**person(p),
                     "count": game.answer_count(p.id),
                     "to_mark": len(game.review_queue(p.id)) if reviewing else 0}
                    for p in game.players.values()],
        "controls": host_actions(game) if controls else [],
        "dev": dev and controls,
        "deadline": _ms(game.grace_deadline),
    }
    if reviewing:
        view["still_marking"] = [p.name for p in game.still_marking()]
        view["all_marked"] = game.all_marked
    if game.phase in (Phase.HIGHLIGHTS, Phase.RESULTS):
        view["step"] = step_view(game)
    return view


# ---------------------------------------------------------------- phone

def phone_view(game: Game, player_id: Optional[str]) -> dict:
    view = {"phase": game.phase.value, "host_joined": game.host is not None}
    p = game.players.get(player_id) if player_id else None
    if p is None:
        return {**view, "screen": "join", "can_join": game.phase == Phase.LOBBY,
                "name_max": config.NAME_MAX_LENGTH}

    view["me"] = {**person(p), "count": game.answer_count(p.id),
                  "skips": p.skips, "max_skips": config.MAX_SKIPS}
    view["host_controls"] = host_actions(game) if p.is_host else []

    if game.phase == Phase.LOBBY:
        return {**view, "screen": "lobby",
                "players": [person(x) for x in game.players.values()],
                "min_players": config.MIN_PLAYERS}

    if game.phase in (Phase.PARTY, Phase.GRACE):
        view["deadline"] = _ms(game.grace_deadline)
        if p.current is not None:
            a = p.current
            return {**view, "screen": "question",
                    "answer_max": config.ANSWER_MAX_LENGTH,
                    "can_skip": game.phase == Phase.PARTY and p.skips > 0,
                    "assignment": {"id": a.id,
                                   "category": category_view(a.category),
                                   "template": game.questions[a.question_id].text,
                                   "subject": person(game.players[a.subject_id])}}
        if game.phase == Phase.GRACE:
            return {**view, "screen": "grace_wait"}
        return {**view, "screen": "categories", "options": game.category_options(p.id)}

    if game.phase == Phase.REVIEW:
        queue = game.review_queue(p.id)
        total = sum(1 for a in game.answers.values() if a.subject_id == p.id)
        common = {"can_undo": bool(p.mark_history),
                  "mind_blowns_left": p.mind_blowns_left,
                  "mind_blowns_max": config.MIND_BLOWNS_PER_MARKER}
        if queue:
            a = queue[0]
            return {**view, **common, "screen": "mark",
                    "position": total - len(queue) + 1, "total": total,
                    "card": {"answer_id": a.id, "category": category_view(a.category),
                             "template": game.questions[a.question_id].text, "text": a.text}}
        pending = game.pending_highlight(p.id)
        if pending:
            return {**view, **common, "screen": "show_it",
                    "card": {"answer_id": pending.id,
                             "template": game.questions[pending.question_id].text,
                             "subject": person(game.players[pending.subject_id]),
                             "text": pending.text}}
        return {**view, **common, "screen": "review_done",
                "still_marking": len(game.still_marking()), "nothing_to_mark": total == 0}

    # Highlights and results: phones point at the TV, then show personal results.
    step = game.current_step or {}
    view.update(screen="ending", step_kind=step.get("kind"))
    if step.get("kind") == "leaderboard":
        row = next(r for r in game.results["leaderboard"] if r["player_id"] == p.id)
        view["results"] = {**row, "of": len(game.results["leaderboard"]),
                           "awards": game.awards_for(p.id)}
    return view
