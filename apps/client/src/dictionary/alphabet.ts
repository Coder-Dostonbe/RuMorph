// Alphabetical order and letter sections for the dictionary in both directions.
// Russian: the Cyrillic alphabet (Ё goes with Е, as in printed dictionaries).
// Uzbek: the Latin alphabet in its official order, with O', G', Sh and Ch as letters of their own.

export const RU_LETTERS = "АБВГДЕЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ".split("");

export const UZ_LETTERS = [
  "A", "B", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O", "P", "Q", "R", "S", "T", "U",
  "V", "X", "Y", "Z", "O'", "G'", "Sh", "Ch",
] as const;

const UZ_INDEX = new Map<string, number>(UZ_LETTERS.map((l, i) => [l.toLowerCase(), i]));

/** One spelling for the Uzbek apostrophe (ʻ ’ ` and ' are all typed for it). */
export function normalizeUz(text: string): string {
  return text.toLocaleLowerCase("uz").replace(/[ʻʼ’‘`´]/g, "'");
}

/** The Uzbek letters of a text, as alphabet positions (spaces and signs are left out). */
export function uzLetters(text: string): number[] {
  const s = normalizeUz(text);
  const out: number[] = [];
  for (let i = 0; i < s.length; i++) {
    const two = s.slice(i, i + 2);
    if (two === "o'" || two === "g'" || two === "sh" || two === "ch") {
      out.push(UZ_INDEX.get(two)!);
      i++;
      continue;
    }
    const one = UZ_INDEX.get(s[i]!);
    if (one !== undefined) out.push(one);
  }
  return out;
}

export function compareUz(a: string, b: string): number {
  const x = uzLetters(a);
  const y = uzLetters(b);
  for (let i = 0; i < Math.min(x.length, y.length); i++) if (x[i] !== y[i]) return x[i]! - y[i]!;
  return x.length - y.length || a.localeCompare(b);
}

/** The section letter of an Uzbek word ("" if it starts with no Uzbek letter). */
export function uzInitial(text: string): string {
  const first = uzLetters(text)[0];
  return first === undefined ? "" : UZ_LETTERS[first]!;
}

export function compareRu(a: string, b: string): number {
  return a.localeCompare(b, "ru");
}

/** The section letter of a Russian word ("" if it starts with no Cyrillic letter). */
export function ruInitial(text: string): string {
  const c = text.trim().charAt(0).toLocaleUpperCase("ru");
  if (c === "Ё") return "Е";
  return RU_LETTERS.includes(c) ? c : "";
}

/**
 * The Uzbek headword of a translation: its first meaning that is a word rather than a suffix
 * ("-da, -ga, ichida" gives "ichida"), without notes in brackets.
 */
export function uzHead(translation: string): string {
  const parts = translation
    .split(/[,;]/)
    .map((p) => p.replace(/\([^)]*\)/g, "").trim())
    .filter(Boolean);
  const word = parts.find((p) => !p.startsWith("-")) ?? parts[0] ?? "";
  return word.replace(/^-+/, "").trim();
}

/** The meanings of a translation, each as it is searched (normalized, without bracket notes). */
export function uzMeanings(translation: string): string[] {
  return translation
    .split(/[,;]/)
    .map((p) => normalizeUz(p.replace(/\([^)]*\)/g, "").replace(/^\s*-+/, "").trim()))
    .filter(Boolean);
}

/**
 * How well an Uzbek query matches a translation: 0 a meaning is the query, 1 a meaning starts
 * with it, 2 the translation contains it, -1 no match. Lower is better.
 */
export function uzMatch(query: string, translation: string): number {
  const q = normalizeUz(query).trim();
  if (!q) return -1;
  const meanings = uzMeanings(translation);
  if (meanings.includes(q)) return 0;
  if (meanings.some((m) => m.startsWith(q) || m.split(/\s+/).some((w) => w.startsWith(q)))) return 1;
  return normalizeUz(translation).includes(q) ? 2 : -1;
}

export interface Section<T> {
  letter: string;
  items: T[];
}

/** Sorted items cut into letter sections, in alphabet order; words with no letter go last under "#". */
export function sections<T>(items: T[], initial: (item: T) => string, letters: readonly string[]): Section<T>[] {
  const by = new Map<string, T[]>();
  for (const item of items) {
    const letter = initial(item) || "#";
    by.set(letter, [...(by.get(letter) ?? []), item]);
  }
  return [...letters, "#"].filter((l) => by.has(l)).map((letter) => ({ letter, items: by.get(letter)! }));
}
