from collections import Counter

import pytest

from mindblower import config
from mindblower.game import GameError
from conftest import answer_once


def test_never_yourself(make_game):
    game, players = make_game(4, start=True)
    for _ in range(6):
        for p in players:
            a = game.pick_category(p.id, "small_talk")
            assert a.subject_id != p.id
            game.submit_answer(p.id, a.id, "x")


def test_never_the_same_person_twice_in_a_row(make_game):
    game, players = make_game(4, start=True)
    host = players[0]
    previous = None
    for _ in range(20):
        a = game.pick_category(host.id, "digging")
        assert a.subject_id != previous
        previous = a.subject_id
        game.submit_answer(host.id, a.id, "x")


def test_disconnected_people_are_not_asked_about(make_game):
    game, players = make_game(4, start=True)
    gone = players[3]
    game.disconnect(gone.id)
    for _ in range(15):
        a = game.pick_category(players[0].id, "small_talk")
        assert a.subject_id != gone.id
        game.submit_answer(players[0].id, a.id, "x")


def test_spreads_questions_evenly(make_game):
    game, players = make_game(5, start=True)
    asker = players[0]
    subjects = Counter()
    for _ in range(12):
        subjects[answer_once(game, asker).subject_id] += 1
    assert max(subjects.values()) - min(subjects.values()) <= 1


def test_avoids_mobbing_one_person(make_game):
    game, players = make_game(6, start=True)
    held = [game.pick_category(p.id, "detective") for p in players]
    open_counts = Counter(a.subject_id for a in held)
    assert max(open_counts.values()) <= config.MAX_OPEN_QUESTIONS_PER_SUBJECT


def test_each_question_asked_about_each_person_once(make_game):
    game, players = make_game(3, start=True)
    seen = set()
    for _ in range(25):
        for p in players:
            try:
                a = game.pick_category(p.id, "top_secret")
            except GameError:
                continue
            pair = (a.subject_id, a.question_id)
            assert pair not in seen
            seen.add(pair)
            game.submit_answer(p.id, a.id, "x")


def test_category_greys_out_when_empty(make_game):
    game, players = make_game(3, start=True)
    asker = players[0]
    # Use up every small talk question about everyone else.
    for _ in range(100):
        try:
            answer_once(game, asker, "small_talk")
        except GameError:
            break
    options = {o["key"]: o["available"] for o in game.category_options(asker.id)}
    assert options["small_talk"] is False
    assert options["digging"] is True
    with pytest.raises(GameError):
        game.pick_category(asker.id, "small_talk")


def test_skipped_question_goes_back_into_the_pool(make_game):
    game, players = make_game(3, start=True)
    a = game.pick_category(players[0].id, "small_talk")
    pair = (a.subject_id, a.question_id)
    game.skip(players[0].id, a.id)
    assert pair not in game._taken_pairs()
