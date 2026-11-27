// Who made the pronunciation recordings, for the About page: every Commons recording the app
// plays is credited there (author, licence, file) instead of in each word window.
import type { Manifest } from "./source";

export interface AuthorCredit {
  author: string;
  license: string;
  words: number;
}

/** Authors with their licence and how many words they recorded, most words first. */
export function authorCredits(manifest: Manifest): AuthorCredit[] {
  const byKey = new Map<string, AuthorCredit>();
  for (const recording of Object.values(manifest.words)) {
    const key = `${recording.author}\u0000${recording.license}`;
    const entry = byKey.get(key) ?? { author: recording.author, license: recording.license, words: 0 };
    entry.words += 1;
    byKey.set(key, entry);
  }
  return [...byKey.values()].sort((a, b) => b.words - a.words || a.author.localeCompare(b.author) || a.license.localeCompare(b.license));
}

/** "CC BY-SA 4.0" -> its deed on creativecommons.org; "" for the public domain. */
export function licenseUrl(license: string): string {
  if (license === "CC0") return "https://creativecommons.org/publicdomain/zero/1.0/";
  const match = /^CC (BY(?:-SA)?) (\d\.\d)(?: ([A-Z]{2}))?$/.exec(license);
  if (!match) return "";
  const [, kind = "", version = "", port] = match;
  return `https://creativecommons.org/licenses/${kind.toLowerCase()}/${version}/${port ? `${port.toLowerCase()}/` : ""}`;
}

/** The licences in use, each once, in a stable order. */
export function licensesUsed(credits: AuthorCredit[]): string[] {
  return [...new Set(credits.map((c) => c.license))].sort();
}

export function commonsPage(file: string): string {
  return `https://commons.wikimedia.org/wiki/File:${encodeURIComponent(file.replace(/ /g, "_"))}`;
}
