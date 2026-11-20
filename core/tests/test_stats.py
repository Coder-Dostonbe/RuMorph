"""Learning statistics (tilsim_core/stats.py)."""

import pytest

from tilsim_core.bridge import BridgeError, dispatch
from tilsim_core.stats import local_day, month, summary

TASHKENT = 300
NOW = "2026-11-21T10:00:00Z"            # 15:00 in Tashkent


def records():
    return {
        "reviews": [
            {"reviewed_at": "2026-11-21T05:00:00Z", "grade": 2},
            {"reviewed_at": "2026-11-21T05:01:00Z", "grade": 0},
            {"reviewed_at": "2026-11-20T20:00:00Z", "grade": 3},     # 01:00 on the 21st in Tashkent
            {"reviewed_at": "2026-11-10T08:00:00Z", "grade": 1},
        ],
        "readings": [{"read_at": "2026-11-19T08:00:00Z", "duration_ms": 600000}],
        "tests": [{"taken_at": "2026-11-21T06:00:00Z", "total": 10, "correct": 7}],
        "words": [{"created_at": "2026-11-21T04:00:00Z", "status": "learning"},
                  {"created_at": "2026-11-01T04:00:00Z", "status": "known"}],
        "cards": [
            {"due_at": "2026-11-21T09:00:00Z", "interval_days": 3, "last_review_at": "2026-11-18T09:00:00Z"},
            {"due_at": "2026-12-30T09:00:00Z", "interval_days": 30, "last_review_at": "2026-11-30T09:00:00Z"},
            {"due_at": "2026-11-21T04:00:00Z", "interval_days": 0, "last_review_at": None},
        ],
    }


def test_local_day_uses_the_offset():
    assert local_day("2026-11-20T20:00:00Z", TASHKENT) == "2026-11-21"
    assert local_day("2026-11-20T20:00:00Z", 0) == "2026-11-20"


def test_summary_counts_the_records():
    s = summary(records(), NOW, TASHKENT)
    assert s["today"] == "2026-11-21"
    assert s["words"] == {"total": 2, "known": 1, "learning": 1}
    assert s["cards"] == {"total": 3, "new": 1, "learning": 1, "mature": 1, "due_now": 1}
    assert s["today_done"]["reviews"] == 3 and s["today_done"]["reviews_right"] == 2
    assert s["today_done"]["tests"] == 1 and s["today_done"]["test_right"] == 7
    assert s["week"]["reviews"] == 3 and s["week"]["review_accuracy"] == 66.7
    assert s["week"]["test_accuracy"] == 70.0 and s["week"]["reading_minutes"] == 10
    assert s["week"]["active_days"] == 2 and s["month_active_days"] == 4
    assert len(s["last_14_days"]) == 14 and s["last_14_days"][-1]["day"] == "2026-11-21"


def test_no_records_gives_zeros_not_made_up_numbers():
    s = summary({}, NOW, TASHKENT)
    assert s["week"]["review_accuracy"] is None and s["week"]["test_accuracy"] is None
    assert s["cards"]["total"] == 0 and s["month_active_days"] == 0


def test_month_lists_every_day_with_due_cards():
    days = month(records(), 2026, 12, TASHKENT)
    assert len(days) == 31 and days[29]["day"] == "2026-12-30" and days[29]["due"] == 1
    assert len(month({}, 2028, 2, 0)) == 29


def test_ops_validate():
    assert dispatch("stats", {"records": records(), "now": NOW, "offset_minutes": TASHKENT})["cards"]["total"] == 3
    assert len(dispatch("calendar", {"records": {}, "year": 2026, "month": 11, "offset_minutes": 0})) == 30
    with pytest.raises(BridgeError):
        dispatch("stats", {"records": {"reviews": [{"grade": 2}]}, "now": NOW})
    with pytest.raises(BridgeError):
        dispatch("calendar", {"records": {}, "year": 2026, "month": 13})
