"""Fake players for testing on your own.

Bots join as soon as the host is in, then play like slow, slightly random
humans: pick categories, "chat" for a while, answer, sometimes skip, mark
answers about them and decide on highlights. `speed` divides every wait.
"""
from __future__ import annotations

import random
import time
from pathlib import Path
from typing import Callable

from . import config
from .game import Game, GameError
from .models import Mark, Phase

BOT_NAMES = [
    "Mia", "Leo", "Aroha", "Jack", "Priya", "Tom", "Ella", "Noah", "Zoe", "Kai",
    "Ruby", "Finn", "Ana", "Sione", "Lily", "Max", "Isla", "Hemi", "Grace", "Oscar",
    "Nina", "Ben", "Tui", "Sofia", "Eli", "Maya", "Rangi", "Chloe", "Sam", "Ivy",
]

BOT_ANSWERS = [
    "Pineapple on everything", "A volcano scientist", "Anything by Queen, loudly",
    "Cats, obviously", "Late, always late", "Dancing in the kitchen", "Never been, but wants to",
    "Something with dinosaurs", "Spicy noodles", "The beach at sunrise", "Too many podcasts",
    "Juggling, badly", "A tiny garden on the balcony", "The one with the dragons",
    "Ice cream for breakfast", "Collecting mugs", "Board game nights", "Midnight, give or take",
    "Wanted to be a pilot", "Burnt the toast. Twice.",
]

SKIN = ["#F6D2B5", "#E8B58F", "#C98B61", "#9C6440", "#6E4429", "#F1C7A0"]
HAIR = ["#3B2416", "#1E1410", "#8A4B22", "#D9A441", "#B5532A", "#5A3A2A"]
BACK = ["#FFD9BD", "#FFE7A8", "#FFC9B0", "#FDE2CF", "#FFD0A1", "#FBE3B8"]
SHIRT = ["#FF8A3D", "#8B5CF6", "#2FBF71", "#F2545B", "#FFB020", "#4A90E2"]
HAIRSTYLES = [
    '<path d="M26 46 Q26 20 50 20 Q74 20 74 46 Q66 32 50 32 Q34 32 26 46Z" fill="{h}"/>',
    '<path d="M24 50 Q22 18 50 18 Q78 18 76 50 L78 78 Q72 60 72 46 Q60 34 40 36 Q30 44 28 60 L22 78Z" fill="{h}"/>',
    '<circle cx="50" cy="30" r="22" fill="{h}"/><circle cx="32" cy="36" r="12" fill="{h}"/>'
    '<circle cx="68" cy="36" r="12" fill="{h}"/>',
    '<path d="M27 44 Q30 22 50 22 Q72 22 73 44 L70 40 Q60 30 44 34 Q34 36 30 46Z" fill="{h}"/>'
    '<circle cx="50" cy="16" r="9" fill="{h}"/>',
]


def cartoon_face(seed: int) -> str:
    """A simple invented cartoon face, used as a bot's selfie."""
    r = random.Random(seed)
    s, h, b, shirt = r.choice(SKIN), r.choice(HAIR), r.choice(BACK), r.choice(SHIRT)
    hair = r.choice(HAIRSTYLES).format(h=h)
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
<rect width="100" height="100" fill="{b}"/>
<path d="M22 100 Q22 76 50 76 Q78 76 78 100Z" fill="{shirt}"/>
<rect x="43" y="64" width="14" height="14" rx="6" fill="{s}"/>
<ellipse cx="50" cy="48" rx="23" ry="25" fill="{s}"/>{hair}
<circle cx="41" cy="50" r="3" fill="#3A2418"/><circle cx="59" cy="50" r="3" fill="#3A2418"/>
<circle cx="35" cy="58" r="4" fill="#F28B82" opacity=".45"/><circle cx="65" cy="58" r="4" fill="#F28B82" opacity=".45"/>
<path d="M43 59 Q50 66 57 59" stroke="#3A2418" stroke-width="2.6" fill="none" stroke-linecap="round"/></svg>"""


def random_mark(rng: random.Random, mind_blowns_left: int) -> Mark:
    marks = [Mark.CORRECT, Mark.PARTLY, Mark.WRONG, Mark.MIND_BLOWN]
    weights = [50, 20, 20, 10 if mind_blowns_left > 0 else 0]
    return rng.choices(marks, weights)[0]


def mark_everything(game: Game, rng: random.Random) -> int:
    """Dev shortcut: marks every unmarked answer at random. Returns how many."""
    count = 0
    for p in list(game.players.values()):
        for a in game.review_queue(p.id):
            game.mark(p.id, a.id, random_mark(rng, p.mind_blowns_left).value)
            count += 1
    return count


class BotManager:
    def __init__(self, game: Game, socketio, uploads_dir: Path, on_change: Callable[[], None],
                 speed: float = 1.0, rng: random.Random | None = None):
        self.game = game
        self.socketio = socketio
        self.uploads_dir = uploads_dir
        self.on_change = on_change
        self.speed = max(0.1, speed)
        self.rng = rng or random.Random()
        self.waiting_to_join = 0      # bots requested before the host arrived
        self.next_move: dict[str, float] = {}
        self._started = False

    # -------------------------------------------------- control

    def request(self, count: int) -> None:
        """Add bots now if the host is in, otherwise as soon as they are."""
        self.waiting_to_join += count
        self._join_waiting()

    def act_now(self) -> None:
        for pid in self.next_move:
            self.next_move[pid] = 0

    def start(self) -> None:
        if not self._started:
            self._started = True
            self.socketio.start_background_task(self._loop)

    # -------------------------------------------------- internals

    def _wait(self, low: float, high: float) -> float:
        return time.time() + self.rng.uniform(low, high) / self.speed

    def _join_waiting(self) -> bool:
        g = self.game
        if not self.waiting_to_join or g.host is None or g.phase != Phase.LOBBY:
            return False
        taken = {p.name.lower() for p in g.players.values()}
        names = [n for n in BOT_NAMES if n.lower() not in taken]
        joined = 0
        for i in range(self.waiting_to_join):
            name = names[i] if i < len(names) else f"Bot {len(g.players) + 1}"
            seed = self.rng.randrange(1_000_000)
            filename = f"bot-{seed}.svg"
            (self.uploads_dir / filename).write_text(cartoon_face(seed), encoding="utf-8")
            try:
                g.join(name, f"/uploads/{filename}", is_bot=True)
                joined += 1
            except GameError:
                break
        self.waiting_to_join = 0
        return joined > 0

    def _loop(self) -> None:
        while True:
            self.socketio.sleep(0.25)
            with self.game.lock:
                changed = self._join_waiting() | self.tick(time.time())
                if changed:
                    self.on_change()

    def tick(self, now: float) -> bool:
        """Let every bot whose turn has come make one move. Returns True if anything changed."""
        g = self.game
        changed = False
        for bot in [p for p in g.players.values() if p.is_bot]:
            if self.next_move.setdefault(bot.id, self._wait(1, 4)) > now:
                continue
            try:
                changed |= self._move(bot)
            except GameError:
                self.next_move[bot.id] = self._wait(1, 3)
        return changed

    def _move(self, bot) -> bool:
        g = self.game
        if g.phase == Phase.PARTY and bot.current is None:
            keys = [c.key for c in config.CATEGORIES]
            self.rng.shuffle(keys)
            for key in keys:
                try:
                    g.pick_category(bot.id, key)
                    break
                except GameError:
                    continue
            self.next_move[bot.id] = self._wait(5, 20)  # time spent "chatting"
            return True

        if g.phase in (Phase.PARTY, Phase.GRACE) and bot.current is not None:
            if g.phase == Phase.PARTY and bot.skips > 0 and self.rng.random() < 0.15:
                g.skip(bot.id, bot.current.id)
            else:
                g.submit_answer(bot.id, bot.current.id, self.rng.choice(BOT_ANSWERS))
            self.next_move[bot.id] = self._wait(1, 3)
            return True

        if g.phase == Phase.REVIEW:
            queue = g.review_queue(bot.id)
            if queue:
                g.mark(bot.id, queue[0].id, random_mark(self.rng, bot.mind_blowns_left).value)
                self.next_move[bot.id] = self._wait(1, 4)
                return True
            pending = g.pending_highlight(bot.id)
            if pending:
                g.choose_highlight(bot.id, pending.id, self.rng.random() < 0.7)
                self.next_move[bot.id] = self._wait(1, 2)
                return True

        self.next_move[bot.id] = self._wait(0.5, 1)
        return False
