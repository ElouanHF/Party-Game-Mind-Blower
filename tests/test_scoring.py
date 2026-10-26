import pytest

from mindblower import config
from mindblower.models import Answer, Mark, Player
from mindblower.scoring import answer_points, breakdown, giver_bonus, ranked


def make_answer(category, mark, asker="a", subject="b"):
    return Answer(id="x", asker_id=asker, subject_id=subject, question_id="q", category=category,
                  text="t", given_at=0, submitted_at=1, mark=mark)


@pytest.mark.parametrize("category,points", [("small_talk", 1), ("digging", 2), ("detective", 3), ("top_secret", 4)])
def test_every_mark_in_every_category(category, points):
    assert answer_points(make_answer(category, Mark.CORRECT)) == points
    assert answer_points(make_answer(category, Mark.PARTLY)) == points / 2
    assert answer_points(make_answer(category, Mark.WRONG)) == 0
    assert answer_points(make_answer(category, Mark.MIND_BLOWN)) == points * 2
    assert answer_points(make_answer(category, None)) == 0


def test_half_points_are_allowed():
    assert answer_points(make_answer("detective", Mark.PARTLY)) == 1.5


def test_giver_bonus_is_one_point_per_mind_blown_given():
    p = Player(id="a", name="A", selfie_url="", joined_at=0)
    assert giver_bonus(p) == 0
    p.mind_blowns_left = config.MIND_BLOWNS_PER_MARKER - 2
    assert giver_bonus(p) == 2


def test_breakdown_adds_answers_and_bonus():
    p = Player(id="a", name="A", selfie_url="", joined_at=0, mind_blowns_left=2)
    answers = [make_answer("top_secret", Mark.MIND_BLOWN), make_answer("small_talk", Mark.PARTLY),
               make_answer("digging", Mark.WRONG), make_answer("digging", Mark.CORRECT, asker="other")]
    b = breakdown(p, answers)
    assert b["points"] == 8 + 0.5 + 0 + 1
    assert (b["submitted"], b["mind_blown"], b["partly"], b["wrong"]) == (3, 1, 1, 1)


def test_ties_share_a_rank():
    players = [Player(id=i, name=i, selfie_url="", joined_at=0) for i in "abc"]
    answers = [make_answer("digging", Mark.CORRECT, asker="a"), make_answer("digging", Mark.CORRECT, asker="b")]
    ranks = {row["player"].id: row["rank"] for row in ranked(players, answers)}
    assert ranks == {"a": 1, "b": 1, "c": 3}
