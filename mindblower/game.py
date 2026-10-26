"""The Game: phases and every rule. No web code lives here.

Every public method either changes the game or raises GameError with a
friendly message for the player. Actions name the thing they act on
(an assignment id, an answer id), so a double tap is harmless.

The server wraps every call in `with game.lock:`.
"""
from __future__ import annotations

import random
import secrets
import threading
import time
from collections import Counter
from typing import Callable, Optional

from . import awards, config, matching, scoring
from .models import Answer, Assignment, Mark, Phase, Player, Question


class GameError(Exception):
    """Something the player tried that isn't allowed right now. The message is shown to them."""


def new_id() -> str:
    return secrets.token_urlsafe(8)


class Game:
    def __init__(
        self,
        questions: list[Question],
        host_key: str,
        rng: Optional[random.Random] = None,
        clock: Callable[[], float] = time.time,
    ):
        self.lock = threading.RLock()
        self.questions = {q.id: q for q in questions}
        self.questions_by_category = {
            c.key: [q for q in questions if q.category == c.key] for c in config.CATEGORIES
        }
        self.host_key = host_key
        self.rng = rng or random.Random()
        self.clock = clock
        self._fx: list[dict] = []
        self._reset_state()

    def _reset_state(self) -> None:
        self.phase = Phase.LOBBY
        self.players: dict[str, Player] = {}        # in join order
        self.answers: dict[str, Answer] = {}        # in submit order
        self.open: dict[str, Assignment] = {}       # questions being held right now
        self.grace_deadline: Optional[float] = None
        self.results: Optional[dict] = None
        self.reveal: list[dict] = []
        self.reveal_index = 0

    # ------------------------------------------------------------ helpers

    def drain_fx(self) -> list[dict]:
        """One-off animation/sound cues since the last call."""
        fx, self._fx = self._fx, []
        return fx

    def _emit(self, kind: str, **data) -> None:
        self._fx.append({"type": kind, **data})

    def _require(self, *phases: Phase) -> None:
        if self.phase not in phases:
            raise GameError("That can't be done right now.")

    def player(self, player_id: str) -> Player:
        p = self.players.get(player_id)
        if p is None:
            raise GameError("We couldn't find you. Try refreshing the page.")
        return p

    @property
    def host(self) -> Optional[Player]:
        return next((p for p in self.players.values() if p.is_host), None)

    def answers_by(self, player_id: str) -> list[Answer]:
        return [a for a in self.answers.values() if a.asker_id == player_id]

    def answer_count(self, player_id: str) -> int:
        return sum(1 for a in self.answers.values() if a.asker_id == player_id)

    # ------------------------------------------------------------ connections

    def connect(self, player_id: str) -> None:
        if player_id in self.players:
            self.players[player_id].connections += 1

    def disconnect(self, player_id: str) -> None:
        if player_id in self.players:
            p = self.players[player_id]
            p.connections = max(0, p.connections - 1)

    # ------------------------------------------------------------ lobby

    def join(self, name: str, selfie_url: str, host_key: Optional[str] = None,
             is_bot: bool = False) -> Player:
        if self.phase != Phase.LOBBY:
            raise GameError("The game has already started, so new players can't join.")
        name = " ".join((name or "").split())
        if not name:
            raise GameError("Please enter your name.")
        if len(name) > config.NAME_MAX_LENGTH:
            raise GameError(f"Names can be up to {config.NAME_MAX_LENGTH} characters.")

        becomes_host = False
        if self.host is None:
            if is_bot or host_key != self.host_key:
                raise GameError("Hang on, the host needs to join first.")
            becomes_host = True

        twin = next((p for p in self.players.values() if p.name.lower() == name.lower()), None)
        if twin:
            raise GameError(f'Someone called {twin.name} is already here. '
                            f'Add your last initial, e.g. "{twin.name} K".')

        player = Player(id=new_id(), name=name, selfie_url=selfie_url,
                        joined_at=self.clock(), is_host=becomes_host, is_bot=is_bot)
        self.players[player.id] = player
        self._emit("joined", player_id=player.id)
        return player

    @property
    def can_start(self) -> bool:
        return self.phase == Phase.LOBBY and len(self.players) >= config.MIN_PLAYERS

    def start(self) -> None:
        self._require(Phase.LOBBY)
        if not self.can_start:
            raise GameError(f"You need at least {config.MIN_PLAYERS} players to start.")
        self.phase = Phase.PARTY
        self._emit("start")

    # ------------------------------------------------------------ party

    def _taken_pairs(self) -> set[tuple[str, str]]:
        pairs = {(a.subject_id, a.question_id) for a in self.answers.values()}
        pairs |= {(x.subject_id, x.question_id) for x in self.open.values()}
        return pairs

    def category_options(self, player_id: str) -> list[dict]:
        """The four category buttons, greyed out when nothing is left in them."""
        asker = self.player(player_id)
        taken = self._taken_pairs()
        options = []
        for c in config.CATEGORIES:
            free = matching.available_by_subject(
                asker, self.players.values(), self.questions_by_category[c.key], taken)
            options.append({"key": c.key, "name": c.name, "points": c.points,
                            "blurb": c.blurb, "available": bool(free)})
        return options

    def pick_category(self, player_id: str, category: str) -> Assignment:
        self._require(Phase.PARTY)
        asker = self.player(player_id)
        if asker.current is not None:
            return asker.current  # double tap: keep the question they already have
        if category not in config.CATEGORY_BY_KEY:
            raise GameError("Unknown category.")

        everything = list(self.answers.values()) + list(self.open.values())
        choice = matching.choose(
            asker=asker,
            players=self.players.values(),
            category_questions=self.questions_by_category[category],
            taken=self._taken_pairs(),
            open_counts=Counter(x.subject_id for x in self.open.values()),
            pair_counts=Counter((x.asker_id, x.subject_id) for x in everything),
            subject_counts=Counter(x.subject_id for x in everything),
            seen_question_ids={x.question_id for x in everything if x.asker_id == asker.id},
            rng=self.rng,
        )
        if choice is None:
            raise GameError("No questions left in that category right now. Try another one.")
        subject_id, question = choice
        assignment = Assignment(id=new_id(), asker_id=asker.id, subject_id=subject_id,
                                question_id=question.id, category=category,
                                given_at=self.clock())
        self.open[assignment.id] = assignment
        asker.current = assignment
        return assignment

    def skip(self, player_id: str, assignment_id: str) -> None:
        if self.phase == Phase.GRACE:
            raise GameError("No skipping in the last 30 seconds. Answer it if you can!")
        self._require(Phase.PARTY)
        p = self.player(player_id)
        if p.current is None or p.current.id != assignment_id:
            return  # already skipped or answered
        if p.skips <= 0:
            raise GameError("No skips left. Answer this one to earn a skip back.")
        p.skips -= 1
        p.skips_used += 1
        self.open.pop(p.current.id, None)  # the question goes back into the pool
        p.current = None

    def submit_answer(self, player_id: str, assignment_id: str, text: str) -> Optional[Answer]:
        self._require(Phase.PARTY, Phase.GRACE)
        p = self.player(player_id)
        if p.current is None or p.current.id != assignment_id:
            return None  # already submitted (double tap)
        text = " ".join((text or "").split())
        if not text:
            raise GameError("Type an answer first.")
        if len(text) > config.ANSWER_MAX_LENGTH:
            raise GameError(f"Keep it under {config.ANSWER_MAX_LENGTH} characters.")

        held = p.current
        answer = Answer(id=new_id(), asker_id=p.id, subject_id=held.subject_id,
                        question_id=held.question_id, category=held.category, text=text,
                        given_at=held.given_at, submitted_at=self.clock())
        self.answers[answer.id] = answer
        self.open.pop(held.id, None)
        p.current = None
        p.last_subject_id = held.subject_id
        p.skips = min(config.MAX_SKIPS, p.skips + 1)
        self._emit("counter_up", player_id=p.id, count=self.answer_count(p.id))

        if self.phase == Phase.GRACE and not self.open:
            self.finish_grace()  # everyone holding a question has answered
        return answer

    def end_party(self) -> Optional[float]:
        """Starts the grace period. Returns the deadline, or None if it was skipped."""
        self._require(Phase.PARTY)
        if not self.open:
            self._begin_review()
            return None
        self.phase = Phase.GRACE
        self.grace_deadline = self.clock() + config.GRACE_SECONDS
        self._emit("end_party")
        return self.grace_deadline

    def finish_grace(self) -> None:
        if self.phase == Phase.GRACE:
            self._begin_review()

    def _begin_review(self) -> None:
        for p in self.players.values():
            p.current = None  # unsent answers are dropped
        self.open.clear()
        self.grace_deadline = None
        self.phase = Phase.REVIEW
        self._emit("times_up")

    # ------------------------------------------------------------ review

    def review_queue(self, player_id: str) -> list[Answer]:
        """Unmarked answers about this player, oldest first."""
        return [a for a in self.answers.values() if a.subject_id == player_id and a.mark is None]

    def still_marking(self) -> list[Player]:
        return [p for p in self.players.values() if self.review_queue(p.id)]

    @property
    def all_marked(self) -> bool:
        return all(a.mark is not None for a in self.answers.values())

    def mark(self, player_id: str, answer_id: str, mark: str) -> None:
        self._require(Phase.REVIEW)
        p = self.player(player_id)
        a = self.answers.get(answer_id)
        if a is None or a.subject_id != p.id:
            raise GameError("That answer isn't yours to mark.")
        if a.mark is not None:
            return  # double tap
        try:
            mark = Mark(mark)
        except ValueError:
            raise GameError("Unknown mark.") from None
        if mark == Mark.MIND_BLOWN:
            if p.mind_blowns_left <= 0:
                raise GameError(f"You've used all {config.MIND_BLOWNS_PER_MARKER} Mind blowns.")
            p.mind_blowns_left -= 1
            if p.mind_blowns_left == 0:
                p.all_mind_blowns_given_at = self.clock()
        a.mark = mark
        p.mark_history.append(a.id)
        self._emit("mark", marker_id=p.id, author_id=a.asker_id, mark=mark.value,
                   remaining=len(self.review_queue(p.id)))

    def undo_mark(self, player_id: str) -> None:
        self._require(Phase.REVIEW)
        p = self.player(player_id)
        if not p.mark_history:
            raise GameError("Nothing to undo.")
        a = self.answers[p.mark_history.pop()]
        if a.mark == Mark.MIND_BLOWN:
            p.mind_blowns_left += 1
            p.all_mind_blowns_given_at = None
        a.mark = None
        a.show_on_tv = None
        self._emit("undo", marker_id=p.id, remaining=len(self.review_queue(p.id)))

    def pending_highlight(self, player_id: str) -> Optional[Answer]:
        """A Mind blown answer by this player that they haven't decided about yet."""
        return next((a for a in self.answers.values()
                     if a.asker_id == player_id and a.mark == Mark.MIND_BLOWN
                     and a.show_on_tv is None), None)

    def choose_highlight(self, player_id: str, answer_id: str, show: bool) -> None:
        self._require(Phase.REVIEW)
        a = self.answers.get(answer_id)
        if a is None or a.asker_id != player_id or a.mark != Mark.MIND_BLOWN:
            raise GameError("That answer can't be shown.")
        a.show_on_tv = bool(show)

    # ------------------------------------------------------------ ending

    def show_highlights(self) -> None:
        self._require(Phase.REVIEW)
        if not self.all_marked:
            raise GameError("Everyone needs to finish marking first.")
        self.results = self._build_results()
        self.reveal = self._build_reveal_steps()
        self.reveal_index = 0
        self._sync_ending_phase()
        self._emit("reveal", step=self.current_step)

    @property
    def current_step(self) -> Optional[dict]:
        if not self.reveal:
            return None
        return self.reveal[self.reveal_index]

    @property
    def at_last_step(self) -> bool:
        return self.reveal_index >= len(self.reveal) - 1

    def advance(self) -> None:
        self._require(Phase.HIGHLIGHTS, Phase.RESULTS)
        if self.at_last_step:
            return
        self.reveal_index += 1
        self._sync_ending_phase()
        self._emit("reveal", step=self.current_step)

    def _sync_ending_phase(self) -> None:
        step = self.current_step
        self.phase = Phase.HIGHLIGHTS if step and step["kind"] == "highlight" else Phase.RESULTS

    def _build_results(self) -> dict:
        players = list(self.players.values())
        answers = list(self.answers.values())
        rows = scoring.ranked(players, answers)
        leaderboard = [{"player_id": r["player"].id, "rank": r["rank"],
                        **{k: v for k, v in r.items() if k not in ("player", "rank")}} for r in rows]

        # Podium: the top three distinct scores; tied players share a step.
        distinct = sorted({r["points"] for r in leaderboard}, reverse=True)[:3]
        podium = [{"place": i + 1,
                   "points": pts,
                   "player_ids": [r["player_id"] for r in leaderboard if r["points"] == pts]}
                  for i, pts in enumerate(distinct)]
        return {
            "leaderboard": leaderboard,
            "podium": podium,
            "awards": awards.compute_awards(players, answers),
        }

    def _build_reveal_steps(self) -> list[dict]:
        shown = [a.id for a in self.answers.values()
                 if a.mark == Mark.MIND_BLOWN and a.show_on_tv]
        self.rng.shuffle(shown)
        steps = [{"kind": "highlight", "answer_id": aid} for aid in shown]
        steps += [{"kind": "award", "index": i} for i in range(len(self.results["awards"]))]
        steps += [{"kind": "podium", "place": p["place"]} for p in reversed(self.results["podium"])]
        steps.append({"kind": "leaderboard"})
        return steps

    def awards_for(self, player_id: str) -> list[dict]:
        if not self.results:
            return []
        won = []
        for award in self.results["awards"]:
            for w in award["winners"]:
                if w["player_id"] == player_id:
                    won.append({"title": award["title"], "subtext": w["subtext"]})
        return won

    def new_game(self) -> None:
        """Back to an empty lobby. The host joins first again with the same host link."""
        self._reset_state()
        self._emit("reset")
