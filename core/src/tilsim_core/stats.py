"""Learning statistics for the dashboard and the calendar, from the learner's own records.

Input is what the device stores: card reviews, reading sessions, test results,
saved words and the cards' due times. Nothing is estimated: every number is a
count or a share of those records. Days are the learner's local calendar days
(the app passes its UTC offset).

- day(): per local day, what was done (reviews and how many were right, reading
  sessions and minutes, tests and how many answers were right, words added),
  and how many cards fall due that day.
- summary(): totals for the dashboard — words (learning / known), cards (new,
  learning, mature: interval of 21 days or more), due now, reviews today, review
  accuracy and active days in the last 7 / 30 days, reading minutes this week.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta

from .srs import parse_time

MATURE_DAYS = 21


def local_day(iso: str, offset_minutes: int) -> str:
    """The local calendar day of a UTC time, for a UTC offset in minutes (Tashkent: +300)."""
    return (parse_time(iso) + timedelta(minutes=offset_minutes)).date().isoformat()


def _empty() -> dict:
    return {"reviews": 0, "reviews_right": 0, "readings": 0, "reading_minutes": 0, "tests": 0,
            "test_answers": 0, "test_right": 0, "words_added": 0, "due": 0}


def days(records: dict, offset_minutes: int) -> dict[str, dict]:
    """Local day → what happened that day (and how many cards fall due that day)."""
    out: dict[str, dict] = defaultdict(_empty)
    for r in records.get("reviews", []):
        d = out[local_day(r["reviewed_at"], offset_minutes)]
        d["reviews"] += 1
        d["reviews_right"] += int(r["grade"]) >= 2
    for r in records.get("readings", []):
        d = out[local_day(r["read_at"], offset_minutes)]
        d["readings"] += 1
        d["reading_minutes"] += round(int(r.get("duration_ms", 0)) / 60000)
    for r in records.get("tests", []):
        d = out[local_day(r["taken_at"], offset_minutes)]
        d["tests"] += 1
        d["test_answers"] += int(r["total"])
        d["test_right"] += int(r["correct"])
    for r in records.get("words", []):
        out[local_day(r["created_at"], offset_minutes)]["words_added"] += 1
    for c in records.get("cards", []):
        if c.get("last_review_at"):
            out[local_day(c["due_at"], offset_minutes)]["due"] += 1
    return dict(out)


def _active(day: dict) -> bool:
    return bool(day["reviews"] or day["readings"] or day["tests"] or day["words_added"])


def summary(records: dict, now: str, offset_minutes: int) -> dict:
    at = parse_time(now)
    today = date.fromisoformat(local_day(now, offset_minutes))
    per_day = days(records, offset_minutes)

    def window(n: int) -> list[dict]:
        return [per_day.get((today - timedelta(days=i)).isoformat(), _empty()) for i in range(n)]

    week, month = window(7), window(30)
    words = records.get("words", [])
    cards = records.get("cards", [])
    reviews_week = sum(d["reviews"] for d in week)
    right_week = sum(d["reviews_right"] for d in week)
    answers_week = sum(d["test_answers"] for d in week)
    test_right_week = sum(d["test_right"] for d in week)
    return {
        "today": today.isoformat(),
        "words": {"total": len(words), "known": sum(w.get("status") == "known" for w in words),
                  "learning": sum(w.get("status") != "known" for w in words)},
        "cards": {
            "total": len(cards),
            "new": sum(not c.get("last_review_at") for c in cards),
            "learning": sum(bool(c.get("last_review_at")) and float(c["interval_days"]) < MATURE_DAYS for c in cards),
            "mature": sum(float(c["interval_days"]) >= MATURE_DAYS for c in cards),
            "due_now": sum(bool(c.get("last_review_at")) and parse_time(c["due_at"]) <= at for c in cards),
        },
        "today_done": per_day.get(today.isoformat(), _empty()),
        "week": {
            "reviews": reviews_week,
            "review_accuracy": round(100 * right_week / reviews_week, 1) if reviews_week else None,
            "test_accuracy": round(100 * test_right_week / answers_week, 1) if answers_week else None,
            "reading_minutes": sum(d["reading_minutes"] for d in week),
            "active_days": sum(_active(d) for d in week),
        },
        "month_active_days": sum(_active(d) for d in month),
        "last_14_days": [{"day": (today - timedelta(days=i)).isoformat(),
                          **per_day.get((today - timedelta(days=i)).isoformat(), _empty())} for i in range(13, -1, -1)],
    }


def month(records: dict, year: int, month_number: int, offset_minutes: int) -> list[dict]:
    """Every day of a month with its activity and due cards (for the calendar)."""
    per_day = days(records, offset_minutes)
    first = date(year, month_number, 1)
    following = date(year + (month_number == 12), month_number % 12 + 1, 1)
    out = []
    d = first
    while d < following:
        out.append({"day": d.isoformat(), **per_day.get(d.isoformat(), _empty())})
        d += timedelta(days=1)
    return out


__all__ = ["MATURE_DAYS", "days", "local_day", "month", "summary"]
