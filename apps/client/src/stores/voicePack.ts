// Downloadable voice packs (Settings): every word's pronunciation in one voice, kept on the
// device so it plays without internet. Packs are built by tools/pronunciation/pack.py and
// listed in data/voicePacks.json; the app downloads one through the API
// (/v1/voice-packs/<file>), checks its size and SHA-256, and stores each word in the webview's
// Cache Storage. One pack is installed at a time: installing another replaces it.
import { defineStore } from "pinia";
import { computed, ref } from "vue";
import { normaliseBaseUrl } from "../api/http";
import { keyValue } from "../data/keyValue";
import packList from "../data/voicePacks.json";
import { PackError, parsePack, sha256Hex } from "../pronunciation/packFormat";
import { wordKey } from "../pronunciation/source";
import { useSettings } from "./settings";

export interface VoicePackInfo {
  id: string;
  file: string;
  bytes: number;
  words: number;
  sha256: string;
}

export const voicePacks: VoicePackInfo[] = (packList as { packs: VoicePackInfo[] }).packs;

const KEY = "voice.pack";
const CACHE_PREFIX = "zabon-voice-";
const BASE = "https://voice.zabon.invalid/";
const wordUrl = (id: string, word: string) => `${BASE}${id}/${encodeURIComponent(word)}`;
const indexUrl = (id: string) => `${BASE}${id}/_index`;

type Credits = Record<string, [author: string, license: string]>;

export function sampleUrl(apiUrl: string, pack: VoicePackInfo): string {
  return `${normaliseBaseUrl(apiUrl)}/v1/voice-packs/${pack.file.replace(/\.bin$/, ".sample.ogg")}`;
}

async function readWithProgress(response: Response, expected: number, onProgress: (done: number) => void): Promise<Uint8Array> {
  if (!response.body) return new Uint8Array(await response.arrayBuffer());
  const out = new Uint8Array(expected);
  const reader = response.body.getReader();
  let done = 0;
  for (;;) {
    const chunk = await reader.read();
    if (chunk.done) break;
    if (done + chunk.value.length > expected) throw new PackError("size");
    out.set(chunk.value, done);
    done += chunk.value.length;
    onProgress(done);
  }
  if (done !== expected) throw new PackError("size");
  return out;
}

const offline = (): boolean => typeof navigator !== "undefined" && navigator.onLine === false;

export const useVoicePack = defineStore("voicePack", () => {
  const installed = ref<string | null>(null);
  const credits = ref<Credits | null>(null);
  const loaded = ref(false);
  /** The pack being downloaded, its progress (0-1) and the last failure code. */
  const busy = ref<string | null>(null);
  const progress = ref(0);
  const failure = ref<{ id: string; code: string } | null>(null);
  const supported = typeof caches !== "undefined";

  const current = computed(() => voicePacks.find((p) => p.id === installed.value) ?? null);

  async function load(): Promise<void> {
    if (loaded.value) return;
    loaded.value = true;
    const id = await keyValue.get(KEY).catch(() => null);
    if (!id || !supported || !voicePacks.some((p) => p.id === id)) return;
    try {
      const cache = await caches.open(CACHE_PREFIX + id);
      const index = await cache.match(indexUrl(id));
      if (!index) return;
      credits.value = (await index.json()) as Credits;
      installed.value = id;
    } catch {
      installed.value = null;
    }
  }

  async function install(pack: VoicePackInfo): Promise<void> {
    if (busy.value) return;
    failure.value = null;
    if (!supported) {
      failure.value = { id: pack.id, code: "unsupported" };
      return;
    }
    if (offline()) {
      failure.value = { id: pack.id, code: "offline" };
      return;
    }
    busy.value = pack.id;
    progress.value = 0;
    try {
      let response: Response;
      try {
        response = await fetch(`${normaliseBaseUrl(useSettings().apiUrl)}/v1/voice-packs/${pack.file}`);
      } catch {
        throw new PackError(offline() ? "offline" : "unreachable");
      }
      if (!response.ok) throw new PackError(`HTTP ${response.status}`);
      const bytes = await readWithProgress(response, pack.bytes, (done) => (progress.value = (0.9 * done) / pack.bytes));
      if ((await sha256Hex(bytes)) !== pack.sha256) throw new PackError("checksum");
      const { header, audio } = parsePack(bytes);

      const cache = await caches.open(CACHE_PREFIX + pack.id);
      const entries = Object.entries(header.words);
      const index: Credits = {};
      for (let i = 0; i < entries.length; i += 64) {
        await Promise.all(entries.slice(i, i + 64).map(([word, [offset, length, author, license]]) => {
          index[word] = [author, license];
          const body = new Blob([audio.slice(offset, offset + length)], { type: header.mime });
          return cache.put(wordUrl(pack.id, word), new Response(body, { headers: { "content-type": header.mime } }));
        }));
        progress.value = 0.9 + (0.1 * Math.min(i + 64, entries.length)) / entries.length;
      }
      await cache.put(indexUrl(pack.id), new Response(JSON.stringify(index), { headers: { "content-type": "application/json" } }));
      await keyValue.set(KEY, pack.id);
      installed.value = pack.id;
      credits.value = index;
      await removeOthers(pack.id);
      void navigator.storage?.persist?.().catch(() => false);
    } catch (e) {
      await caches.delete(CACHE_PREFIX + pack.id).catch(() => false);
      failure.value = { id: pack.id, code: e instanceof Error ? e.message : String(e) };
    } finally {
      busy.value = null;
    }
  }

  async function removeOthers(keep: string | null): Promise<void> {
    for (const name of await caches.keys()) {
      if (name.startsWith(CACHE_PREFIX) && name !== CACHE_PREFIX + keep) await caches.delete(name);
    }
  }

  async function remove(): Promise<void> {
    await keyValue.set(KEY, "");
    installed.value = null;
    credits.value = null;
    if (supported) await removeOthers(null);
  }

  function has(lemma: string): boolean {
    return credits.value !== null && wordKey(lemma) in credits.value;
  }

  async function audio(lemma: string): Promise<Blob | null> {
    const id = installed.value;
    if (!id || !has(lemma)) return null;
    const hit = await (await caches.open(CACHE_PREFIX + id)).match(wordUrl(id, wordKey(lemma)));
    return hit ? hit.blob() : null;
  }

  return { installed, current, loaded, busy, progress, failure, supported, load, install, remove, has, audio };
});
