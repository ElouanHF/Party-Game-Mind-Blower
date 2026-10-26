import pytest

from mindblower import config
from mindblower.game import Game, GameError
from mindblower.models import Mark, Phase
from conftest import HOST_KEY, answer_once


# ---------------------------------------------------------------- lobby

def test_host_must_join_first(questions, clock):
    game = Game(questions, HOST_KEY, clock=clock)
    with pytest.raises(GameError):
        game.join("Mia", "/s.jpg")
    with pytest.raises(GameError):
        game.join("Mia", "/s.jpg", host_key="WRONG")
    host = game.join("Sam", "/s.jpg", host_key=HOST_KEY)
    assert host.is_host
    assert not game.join("Mia", "/s.jpg").is_host


def test_bots_cannot_be_host(questions, clock):
    game = Game(questions, HOST_KEY, clock=clock)
    with pytest.raises(GameError):
        game.join("Bot", "/b.svg", host_key=HOST_KEY, is_bot=True)


def test_names_are_checked(make_game):
    game, _ = make_game(2)
    with pytest.raises(GameError, match="already here"):
        game.join("  mia ", "/s.jpg")
    with pytest.raises(GameError):
        game.join("   ", "/s.jpg")
    with pytest.raises(GameError):
        game.join("x" * (config.NAME_MAX_LENGTH + 1), "/s.jpg")


def test_needs_three_players_and_no_late_joiners(make_game):
    game, _ = make_game(2)
    with pytest.raises(GameError):
        game.start()
    game.join("Leo", "/s.jpg")
    game.start()
    assert game.phase == Phase.PARTY
    with pytest.raises(GameError, match="already started"):
        game.join("Late", "/s.jpg")


# ---------------------------------------------------------------- party

def test_skips_are_used_and_earned_back(make_game):
    game, players = make_game(3, start=True)
    p = players[0]
    a = game.pick_category(p.id, "small_talk")
    game.skip(p.id, a.id)
    assert (p.skips, p.skips_used, p.current) == (config.START_SKIPS - 1, 1, None)
    answer_once(game, p)
    assert p.skips == config.START_SKIPS
    answer_once(game, p)
    assert p.skips == config.MAX_SKIPS  # never above the max


def test_no_skips_left(make_game):
    game, players = make_game(3, start=True)
    p = players[0]
    p.skips = 0
    a = game.pick_category(p.id, "small_talk")
    with pytest.raises(GameError, match="No skips left"):
        game.skip(p.id, a.id)


def test_double_taps_count_once(make_game):
    game, players = make_game(3, start=True)
    p = players[0]
    a1 = game.pick_category(p.id, "small_talk")
    assert game.pick_category(p.id, "digging") is a1  # keeps the question already held
    game.submit_answer(p.id, a1.id, "first")
    assert game.submit_answer(p.id, a1.id, "again") is None
    assert game.answer_count(p.id) == 1


def test_answers_are_checked(make_game):
    game, players = make_game(3, start=True)
    p = players[0]
    a = game.pick_category(p.id, "small_talk")
    with pytest.raises(GameError):
        game.submit_answer(p.id, a.id, "   ")
    with pytest.raises(GameError):
        game.submit_answer(p.id, a.id, "x" * (config.ANSWER_MAX_LENGTH + 1))


# ---------------------------------------------------------------- grace period

def test_grace_lets_holders_finish_but_not_skip(make_game, clock):
    game, players = make_game(3, start=True)
    holding = game.pick_category(players[0].id, "small_talk")
    game.pick_category(players[1].id, "small_talk")
    deadline = game.end_party()
    assert game.phase == Phase.GRACE and deadline == clock.now + config.GRACE_SECONDS
    with pytest.raises(GameError):
        game.skip(players[0].id, holding.id)
    with pytest.raises(GameError):
        game.pick_category(players[2].id, "small_talk")  # no new questions
    game.submit_answer(players[0].id, holding.id, "just in time")
    assert game.phase == Phase.GRACE  # players[1] is still holding one
    game.finish_grace()
    assert game.phase == Phase.REVIEW
    assert players[1].current is None and len(game.answers) == 1  # the unsent one was dropped


def test_grace_ends_early_when_everyone_has_answered(make_game):
    game, players = make_game(3, start=True)
    a = game.pick_category(players[0].id, "small_talk")
    game.end_party()
    game.submit_answer(players[0].id, a.id, "done")
    assert game.phase == Phase.REVIEW


def test_no_grace_when_nobody_holds_a_question(make_game):
    game, players = make_game(3, start=True)
    assert game.end_party() is None
    assert game.phase == Phase.REVIEW


# ---------------------------------------------------------------- review

def reviewing_game(make_game, rounds=3):
    game, players = make_game(4, start=True)
    for _ in range(rounds):
        for p in players:
            answer_once(game, p, "digging")
    game.end_party()
    return game, players


def test_you_only_mark_answers_about_you(make_game):
    game, players = reviewing_game(make_game)
    someone_elses = next(a for a in game.answers.values() if a.subject_id != players[0].id)
    with pytest.raises(GameError):
        game.mark(players[0].id, someone_elses.id, "correct")


def test_mind_blown_limit_and_undo(make_game):
    game, players = reviewing_game(make_game, rounds=4)
    marker = max(players, key=lambda p: len(game.review_queue(p.id)))
    queue = game.review_queue(marker.id)
    assert len(queue) >= 4
    for a in queue[:3]:
        game.mark(marker.id, a.id, "mind_blown")
    assert marker.mind_blowns_left == 0 and marker.all_mind_blowns_given_at is not None
    with pytest.raises(GameError, match="used all"):
        game.mark(marker.id, queue[3].id, "mind_blown")
    game.undo_mark(marker.id)
    assert marker.mind_blowns_left == 1 and queue[2].mark is None
    assert marker.all_mind_blowns_given_at is None


def test_highlights_locked_until_everything_is_marked(make_game):
    game, players = reviewing_game(make_game)
    with pytest.raises(GameError, match="finish marking"):
        game.show_highlights()
    for p in players:
        for a in game.review_queue(p.id):
            game.mark(p.id, a.id, "correct")
    game.show_highlights()
    assert game.phase in (Phase.HIGHLIGHTS, Phase.RESULTS)


def test_highlight_choice_and_ending_steps(make_game):
    game, players = reviewing_game(make_game)
    shown = None
    for p in players:
        for a in game.review_queue(p.id):
            mark = "mind_blown" if shown is None else "correct"
            game.mark(p.id, a.id, mark)
            if shown is None:
                shown = a
    author = game.players[shown.asker_id]
    assert game.pending_highlight(author.id) is shown
    with pytest.raises(GameError):
        game.choose_highlight(players[0].id if players[0] is not author else players[1].id, shown.id, True)
    game.choose_highlight(author.id, shown.id, True)

    game.show_highlights()
    kinds = [s["kind"] for s in game.reveal]
    assert kinds[0] == "highlight" and kinds.count("highlight") == 1
    assert kinds[-1] == "leaderboard"
    podium_places = [s["place"] for s in game.reveal if s["kind"] == "podium"]
    assert podium_places == sorted(podium_places, reverse=True)  # 3rd, 2nd, then 1st
    assert game.phase == Phase.HIGHLIGHTS
    while not game.at_last_step:
        game.advance()
    assert game.phase == Phase.RESULTS
    game.new_game()
    assert game.phase == Phase.LOBBY and not game.players


def test_undecided_highlights_stay_private(make_game):
    game, players = reviewing_game(make_game)
    for p in players:
        for a in game.review_queue(p.id):
            game.mark(p.id, a.id, "mind_blown" if p.mind_blowns_left else "correct")
    game.show_highlights()
    assert all(s["kind"] != "highlight" for s in game.reveal)


def test_fx_cues(make_game):
    game, players = make_game(3, start=True)
    game.drain_fx()
    answer_once(game, players[0])
    fx = game.drain_fx()
    assert fx == [{"type": "counter_up", "player_id": players[0].id, "count": 1}]
    assert game.drain_fx() == []
