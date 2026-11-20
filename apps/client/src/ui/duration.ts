import { format, type Messages } from "../i18n";

/** "10 daq", "3 kun", "2 oy" from a number of days. */
export function formatDays(days: number, m: Messages): string {
  if (days < 1) return format(m.cards.minutes, { n: Math.max(1, Math.round(days * 1440)) });
  if (days < 45) return format(m.cards.days, { n: Math.round(days * 10) / 10 });
  return format(m.cards.months, { n: Math.round((days / 30) * 10) / 10 });
}

/** When an ISO time comes, relative to now: "hozir", "10 daq", "3 kun". */
export function formatUntil(iso: string, m: Messages): string {
  const days = (new Date(iso).getTime() - Date.now()) / 86_400_000;
  return days <= 0 ? m.cards.now : formatDays(days, m);
}
