from mindblower.awards import compute_awards, format_duration
from mindblower.models import Answer, Mark, Player


def player(pid, **kw):
    return Player(id=pid, name=pid.upper(), selfie_url="", joined_at=0, **kw)


def answer(asker, subject, mark=Mark.CORRECT, category="small_talk", seconds=60):
    return Answer(id=f"{asker}{subject}{seconds}{category}{mark}", asker_id=asker, subject_id=subject,
                  question_id="q", category=category, text="t", given_at=0, submitted_at=seconds, mark=mark)


def by_key(awards):
    return {a["key"]: a for a in awards}


def winners(award):
    return sorted(w["player_id"] for w in award["winners"])


def test_social_butterfly_with_subtext():
    players = [player("a"), player("b"), player("c")]
    answers = [answer("a", "b"), answer("a", "c"), answer("b", "a")]
    award = by_key(compute_awards(players, answers))["social_butterfly"]
    assert winners(award) == ["a"]
    assert award["winners"][0]["subtext"] == "Most answers submitted: 2"


def test_ties_share_an_award():
    players = [player("a"), player("b"), player("c")]
    answers = [answer("a", "c", Mark.MIND_BLOWN), answer("b", "c", Mark.MIND_BLOWN)]
    assert winners(by_key(compute_awards(players, answers))["mind_blower"]) == ["a", "b"]


def test_no_award_when_everyone_ties():
    players = [player("a"), player("b")]
    answers = [answer("a", "b"), answer("b", "a")]
    assert "social_butterfly" not in by_key(compute_awards(players, answers))


def test_share_awards_need_three_answers():
    players = [player("a"), player("b"), player("c")]
    answers = [answer("a", "b", Mark.WRONG), answer("a", "c", Mark.WRONG)]  # only 2 answers
    keys = by_key(compute_awards(players, answers))
    assert "were_you_even_listening" not in keys


def test_were_you_even_listening_and_open_book():
    players = [player("a"), player("b"), player("c")]
    answers = ([answer("a", "c", Mark.WRONG) for _ in range(2)] + [answer("a", "c", Mark.CORRECT, seconds=5)]
               + [answer("b", "c", Mark.CORRECT, seconds=s) for s in (1, 2, 3)]
               + [answer("c", "a", Mark.WRONG, seconds=s) for s in (1, 2, 3)])
    awards = by_key(compute_awards(players, answers))
    listening = awards["were_you_even_listening"]
    assert winners(listening) == ["c"]
    assert listening["winners"][0]["subtext"] == "Fewest answers marked right: 0 of 3"


def test_hype_squad_is_first_to_give_all_mind_blowns():
    players = [player("a", all_mind_blowns_given_at=50.0), player("b", all_mind_blowns_given_at=20.0), player("c")]
    award = by_key(compute_awards(players, []))["hype_squad"]
    assert winners(award) == ["b"]


def test_one_player_can_win_several_and_decorated():
    players = [player("a", skips_used=4), player("b"), player("c")]
    answers = [answer("a", "b", Mark.MIND_BLOWN, "top_secret"), answer("a", "c", Mark.PARTLY, "top_secret"),
               answer("b", "a")]
    awards = by_key(compute_awards(players, answers))
    won_by_a = [k for k, a in awards.items() if "a" in winners(a)]
    assert {"social_butterfly", "mind_blower", "daredevil", "close_enough", "picky_picker"} <= set(won_by_a)
    assert winners(awards["decorated"]) == ["a"]
    assert awards["decorated"]["winners"][0]["subtext"].startswith("Most awards: ")
    assert list(awards)[-1] == "decorated"


def test_quick_draw_formats_time():
    assert format_duration(45) == "45 s"
    assert format_duration(100) == "1 min 40 s"
    assert format_duration(120) == "2 min"


def test_big_ties_are_skipped():
    players = [player(p) for p in "abcde"]
    answers = [answer(p, "e") for p in "abcd"]  # a, b, c and d each submitted 1
    assert "social_butterfly" not in by_key(compute_awards(players, answers))