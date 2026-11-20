"""Spaced repetition for flashcards: SM-2 with four answer buttons.

The learner grades each answer: 0 again (forgot), 1 hard, 2 good, 3 easy. The
card's interval grows by its ease factor after each correct answer and starts
again after a lapse, as in SuperMemo-2 (Wozniak, 1990) and the Anki variant of
it:

- again: back to the start; seen again in 10 minutes; ease − 0.20; a lapse is
  counted if the card had been learned.
- hard: interval × 1.2 (at least 1 day); ease − 0.15.
- good: 1 day, then 3 days, then interval × ease.
- easy: 4 days for a new card, else interval × ease × 1.3; ease + 0.15.

Ease never goes below 1.3. Times are UTC ISO 8601 strings, as stored in the
database; the caller passes "now", so the schedule is reproducible and tested.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone

AGAIN, HARD, GOOD, EASY = 0, 1, 2, 3
GRADES = (AGAIN, HARD, GOOD, EASY)
MIN_EASE = 1.3
START_EASE = 2.5
RELEARN_MINUTES = 10
MAX_INTERVAL_DAYS = 3650


@dataclass(frozen=True)
class CardState:
    due_at: str
    interval_days: float = 0.0
    ease: float = START_EASE
    reps: int = 0
    lapses: int = 0
    last_review_at: str | None = None

    @classmethod
    def from_dict(cls, data: dict) -> CardState:
        return cls(
            due_at=str(data["due_at"]),
            interval_days=float(data.get("interval_days", 0.0)),
            ease=float(data.get("ease", START_EASE)),
            reps=int(data.get("reps", 0)),
            lapses=int(data.get("lapses", 0)),
            last_review_at=data.get("last_review_at"),
        )

    def to_dict(self) -> dict:
        return {"due_at": self.due_at, "interval_days": self.interval_days, "ease": self.ease, "reps": self.reps,
                "lapses": self.lapses, "last_review_at": self.last_review_at}


def parse_time(text: str) -> datetime:
    value = datetime.fromisoformat(text.replace("Z", "+00:00"))
    if value.tzinfo is None:
        raise ValueError(f"time without a time zone: {text!r}")
    return value.astimezone(timezone.utc)


def format_time(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def new_card(now: str) -> CardState:
    """A card is due as soon as it is made."""
    return CardState(due_at=format_time(parse_time(now)))


def review(card: CardState, grade: int, now: str) -> CardState:
    if grade not in GRADES:
        raise ValueError(f"grade must be one of {GRADES}")
    at = parse_time(now)
    ease = card.ease
    if grade == AGAIN:
        ease = max(MIN_EASE, ease - 0.20)
        return replace(card, due_at=format_time(at + timedelta(minutes=RELEARN_MINUTES)), interval_days=0.0,
                       ease=round(ease, 2), reps=0, lapses=card.lapses + (1 if card.reps > 0 else 0),
                       last_review_at=format_time(at))
    if grade == HARD:
        ease = max(MIN_EASE, ease - 0.15)
        interval = max(1.0, card.interval_days * 1.2)
    elif grade == GOOD:
        interval = 1.0 if card.reps == 0 else 3.0 if card.reps == 1 else card.interval_days * ease
    else:
        ease = ease + 0.15
        interval = 4.0 if card.reps == 0 else max(card.interval_days * ease * 1.3, 4.0)
    interval = round(min(interval, MAX_INTERVAL_DAYS), 2)
    return replace(card, due_at=format_time(at + timedelta(days=interval)), interval_days=interval,
                   ease=round(ease, 2), reps=card.reps + 1, last_review_at=format_time(at))


def preview(card: CardState, now: str) -> dict[int, float]:
    """For each grade, how long until the card comes back, in days (10 minutes for "again")."""
    out = {}
    for grade in GRADES:
        after = review(card, grade, now)
        out[grade] = round((parse_time(after.due_at) - parse_time(now)).total_seconds() / 86400, 4)
    return out


def is_new(card: CardState) -> bool:
    return card.last_review_at is None


def queue(cards: list[tuple[str, CardState]], now: str, *, new_limit: int, new_seen_today: int) -> list[str]:
    """Ids of the cards to study now: due reviews first (most overdue first), then new cards up to
    what is left of today's limit, oldest first (the caller passes them in creation order)."""
    at = parse_time(now)
    due = sorted(((parse_time(c.due_at), cid) for cid, c in cards if not is_new(c) and parse_time(c.due_at) <= at))
    fresh = [cid for cid, c in cards if is_new(c)][:max(0, new_limit - new_seen_today)]
    return [cid for _, cid in due] + fresh
