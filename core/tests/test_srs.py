"""Spaced repetition (tilsim_core/srs.py) and its bridge ops."""

import pytest

from tilsim_core.bridge import dispatch
from tilsim_core.srs import AGAIN, EASY, GOOD, HARD, CardState, new_card, parse_time, preview, queue, review

NOW = "2026-11-21T08:00:00.000Z"


def days_between(a, b):
    return (parse_time(b) - parse_time(a)).total_seconds() / 86400


def test_good_answers_space_out_1_3_then_times_ease():
    card = new_card(NOW)
    card = review(card, GOOD, NOW)
    assert card.interval_days == 1 and card.reps == 1 and days_between(NOW, card.due_at) == 1
    card = review(card, GOOD, card.due_at)
    assert card.interval_days == 3
    card = review(card, GOOD, card.due_at)
    assert card.interval_days == 7.5 and card.ease == 2.5


def test_again_relearns_in_ten_minutes_and_counts_a_lapse_only_for_learned_cards():
    fresh = review(new_card(NOW), AGAIN, NOW)
    assert fresh.lapses == 0 and fresh.reps == 0 and round(days_between(NOW, fresh.due_at) * 1440) == 10
    learned = review(review(new_card(NOW), GOOD, NOW), GOOD, NOW)
    lapsed = review(learned, AGAIN, NOW)
    assert lapsed.lapses == 1 and lapsed.reps == 0 and lapsed.interval_days == 0 and lapsed.ease == 2.3


def test_hard_and_easy_change_the_ease():
    card = review(review(new_card(NOW), GOOD, NOW), GOOD, NOW)        # interval 3
    hard = review(card, HARD, NOW)
    easy = review(card, EASY, NOW)
    assert hard.interval_days == 3.6 and hard.ease == 2.35
    assert easy.interval_days == round(3 * 2.65 * 1.3, 2) and easy.ease == 2.65
    assert review(new_card(NOW), EASY, NOW).interval_days == 4


def test_ease_never_drops_below_1_3():
    card = new_card(NOW)
    for _ in range(20):
        card = review(card, AGAIN, NOW)
    assert card.ease == 1.3


def test_preview_lists_every_grade():
    days = preview(new_card(NOW), NOW)
    assert days[GOOD] == 1 and days[EASY] == 4 and days[HARD] == 1 and 0 < days[AGAIN] < 0.01


def test_queue_puts_due_reviews_first_then_new_cards_up_to_the_limit():
    reviewed = review(new_card(NOW), GOOD, "2026-11-19T08:00:00Z")    # due 11-20, overdue
    later = review(new_card(NOW), EASY, NOW)                          # due in 4 days
    cards = [("new1", new_card(NOW)), ("due", reviewed), ("later", later), ("new2", new_card(NOW)),
             ("new3", new_card(NOW))]
    assert queue(cards, NOW, new_limit=2, new_seen_today=0) == ["due", "new1", "new2"]
    assert queue(cards, NOW, new_limit=2, new_seen_today=2) == ["due"]


def test_times_need_a_time_zone():
    with pytest.raises(ValueError):
        review(new_card(NOW), GOOD, "2026-11-21T08:00:00")


def test_round_trip_through_dict():
    card = review(new_card(NOW), GOOD, NOW)
    assert CardState.from_dict(card.to_dict()) == card


def test_bridge_ops():
    card = new_card(NOW).to_dict()
    after = dispatch("srs_review", {"card": card, "grade": 2, "now": NOW})["card"]
    assert after["interval_days"] == 1 and after["reps"] == 1
    assert dispatch("srs_preview", {"card": card, "now": NOW})["days"]["3"] == 4
    ids = dispatch("srs_queue", {"cards": [{"id": "a", **card}], "now": NOW, "new_limit": 5})["ids"]
    assert ids == ["a"]
    words = dispatch("words", {"ids": ["книга|NOUN,inan,femn", "nope"], "lang": "uz"})
    assert list(words) == ["книга|NOUN,inan,femn"]
    assert [f["form"] for f in words["книга|NOUN,inan,femn"]["key_forms"]] == ["книги", "книги", "книг"]


@pytest.mark.parametrize("args", [
    {"card": {}, "grade": 2, "now": NOW}, {"card": new_card(NOW).to_dict(), "grade": 5, "now": NOW},
    {"card": new_card(NOW).to_dict(), "grade": True, "now": NOW}, {"card": new_card(NOW).to_dict(), "grade": 2, "now": "x"},
])
def test_review_validates(args):
    from tilsim_core.bridge import BridgeError

    with pytest.raises(BridgeError):
        dispatch("srs_review", args)
