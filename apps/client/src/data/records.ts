// Everything the statistics need, read from the learner's tables and trimmed to the fields
// tilsim_core/stats.py uses.
import { flashcards, readings, reviews, testResults, vocabulary } from "./userData";

export interface Records {
  reviews: { reviewed_at: string; grade: number }[];
  readings: { read_at: string; duration_ms: number }[];
  tests: { taken_at: string; total: number; correct: number }[];
  words: { created_at: string; status: string }[];
  cards: { due_at: string; interval_days: number; last_review_at: string | null }[];
}

export async function loadRecords(): Promise<Records> {
  const [r, rd, t, w, c] = await Promise.all([reviews.list(), readings.list(), testResults.list(), vocabulary.list(), flashcards.list()]);
  return {
    reviews: r.map((x) => ({ reviewed_at: x.reviewed_at, grade: x.grade })),
    readings: rd.map((x) => ({ read_at: x.read_at, duration_ms: x.duration_ms })),
    tests: t.filter((x) => x.total > 0).map((x) => ({ taken_at: x.taken_at, total: x.total, correct: x.correct })),
    words: w.map((x) => ({ created_at: x.created_at, status: x.status })),
    cards: c.map((x) => ({ due_at: x.due_at, interval_days: x.interval_days, last_review_at: x.last_review_at })),
  };
}

/** The device's offset from UTC in minutes (Tashkent: +300). */
export function utcOffsetMinutes(at = new Date()): number {
  return -at.getTimezoneOffset();
}
