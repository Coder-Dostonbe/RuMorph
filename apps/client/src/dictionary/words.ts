// Every word of the lexicon, for the dictionary list. The core hands out at most 200 words a
// call, so the list is read page by page once and kept for the session (per language and part of speech).
import { grammar, type PosFilter, type SearchResult } from "../core/grammar";
import type { Locale } from "../i18n";

export type ListedWord = SearchResult["items"][number];

const PAGE = 200;
const cache = new Map<string, Promise<ListedWord[]>>();

/** All words matching the query (all words when it is empty), every page. */
export async function searchAll(query: string, lang: Locale, pos: PosFilter | null): Promise<ListedWord[]> {
  const items: ListedWord[] = [];
  for (;;) {
    const page = await grammar.search(query, lang, { pos, limit: PAGE, offset: items.length });
    items.push(...page.items);
    if (page.items.length === 0 || items.length >= page.total) return items;
  }
}

/** The whole lexicon (or one part of speech), read once per session. A failed read is not kept. */
export function allWords(lang: Locale, pos: PosFilter | null): Promise<ListedWord[]> {
  const key = `${lang}|${pos ?? ""}`;
  let words = cache.get(key);
  if (!words) {
    words = searchAll("", lang, pos);
    cache.set(key, words);
    words.catch(() => cache.delete(key));
  }
  return words;
}
