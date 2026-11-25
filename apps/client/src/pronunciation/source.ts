// Recorded pronunciations: Wikimedia Commons files listed in data/pronunciations.json (made by
// tools/pronunciation/build.py). The app plays them through the Zabon API (/v1/audio/...),
// which fetches them from upload.wikimedia.org.
import { normaliseBaseUrl } from "../api/http";

export interface Recording {
  /** Commons file name, e.g. "LL-Q7737 (rus)-Tatiana Kerbush-книга.wav". */
  file: string;
  /** Path under upload.wikimedia.org/wikipedia/commons/ of the file the app plays. */
  path: string;
  author: string;
  license: string;
}

export interface Manifest {
  words: Record<string, Recording>;
  homographs: string[];
}

export function audioUrl(apiBase: string, path: string): string {
  return `${normaliseBaseUrl(apiBase)}/v1/audio/${path.split("/").map(encodeURIComponent).join("/")}`;
}

/** The dictionary key of a word: lower case, no stress mark (ё stays ё). */
export function wordKey(lemma: string): string {
  return lemma.replace(/[̀́]/g, "").trim().toLowerCase();
}

let manifest: Promise<Manifest> | null = null;

/** The list is ~300 KB, so it is loaded only when a word is opened. */
export function loadManifest(): Promise<Manifest> {
  manifest ??= import("../data/pronunciations.json").then((mod) => {
    const data = (mod.default ?? mod) as unknown as Manifest;
    return { words: data.words ?? {}, homographs: data.homographs ?? [] };
  }).catch((error) => {
    manifest = null;
    throw error;
  });
  return manifest;
}

export type Lookup = { kind: "recording"; recording: Recording } | { kind: "homograph" } | { kind: "none" };

export function lookup(data: Manifest, lemma: string): Lookup {
  const key = wordKey(lemma);
  if (data.homographs.includes(key)) return { kind: "homograph" };
  const recording = data.words[key];
  return recording ? { kind: "recording", recording } : { kind: "none" };
}
