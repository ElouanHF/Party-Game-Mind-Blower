"""Shared test helpers: a game with a fake clock and a few connected players."""
import random
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from mindblower.game import Game  # noqa: E402
from mindblower.questions import load_questions  # noqa: E402

HOST_KEY = "TEST01"


class FakeClock:
    def __init__(self):
        self.now = 1_000.0

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


@pytest.fixture
def questions():
    return load_questions(ROOT / "data" / "questions.json")


@pytest.fixture
def clock():
    return FakeClock()


@pytest.fixture
def make_game(questions, clock):
    """make_game(4) -> (game, [host, p2, p3, p4]), all connected, still in the lobby."""
    def _make(n=4, start=False, seed=1):
        game = Game(questions, HOST_KEY, rng=random.Random(seed), clock=clock)
        names = ["Sam", "Mia", "Leo", "Aroha", "Jack", "Priya", "Tom", "Ella", "Noah", "Zoe"]
        players = [game.join(names[0], "/s.jpg", host_key=HOST_KEY)]
        players += [game.join(name, "/s.jpg") for name in names[1:n]]
        for p in players:
            game.connect(p.id)
        if start:
            game.start()
        return game, players
    return _make


def answer_once(game, player, category="small_talk", text="An answer"):
    """Pick a category and answer it straight away."""
    assignment = game.pick_category(player.id, category)
    return game.submit_answer(player.id, assignment.id, text)
