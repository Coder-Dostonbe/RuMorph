import { describe, expect, it } from "vitest";
import packs from "../src/data/voicePacks.json";
import { PackError, parsePack, sha256Hex } from "../src/pronunciation/packFormat";

function makePack(words: Record<string, Uint8Array>): Uint8Array {
  const index: Record<string, [number, number, string, string]> = {};
  let offset = 0;
  for (const [word, data] of Object.entries(words)) {
    index[word] = [offset, data.length, "Vosk TTS", "Apache-2.0"];
    offset += data.length;
  }
  const header = new TextEncoder().encode(JSON.stringify({ format: "zabon-voice-pack", version: 1, mime: "audio/ogg", voice: { id: "t" }, words: index }));
  const out = new Uint8Array(8 + header.length + offset);
  out.set([0x5a, 0x56, 0x50, 0x31]);
  new DataView(out.buffer).setUint32(4, header.length, false);
  out.set(header, 8);
  let at = 8 + header.length;
  for (const data of Object.values(words)) {
    out.set(data, at);
    at += data.length;
  }
  return out;
}

describe("voice packs", () => {
  it("reads every word's audio from a pack", () => {
    const { header, audio } = parsePack(makePack({ дом: new Uint8Array([1, 2]), книга: new Uint8Array([3, 4, 5]) }));
    const [offset, length, author] = header.words["книга"]!;
    expect(Array.from(audio.subarray(offset, offset + length))).toEqual([3, 4, 5]);
    expect(author).toBe("Vosk TTS");
  });

  it("refuses broken files", () => {
    expect(() => parsePack(new Uint8Array([1, 2, 3, 4, 5, 6, 7, 8]))).toThrow(PackError);
    const pack = makePack({ дом: new Uint8Array([1, 2]) });
    expect(() => parsePack(pack.subarray(0, pack.length - 1))).toThrow(PackError);
  });

  it("checks SHA-256", async () => {
    expect(await sha256Hex(new TextEncoder().encode("abc"))).toBe("ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad");
  });

  it("lists packs the API can serve", () => {
    for (const p of packs.packs as { id: string; file: string; bytes: number; sha256: string }[]) {
      expect(p.file).toMatch(/^zabon-voice-[a-z0-9-]+-\d+\.bin$/);
      expect(p.file.startsWith(`zabon-voice-${p.id}-`)).toBe(true);
      expect(p.bytes).toBeGreaterThan(0);
      expect(p.sha256).toMatch(/^[0-9a-f]{64}$/);
    }
  });
});
