import { describe, expect, it } from "vitest";
import data from "../src/data/pronunciations.json";
import { audioUrl, lookup, wordKey, type Manifest } from "../src/pronunciation/source";

const manifest: Manifest = {
  words: {
    книга: { file: "LL-Q7737 (rus)-X-книга.wav", path: "transcoded/a/ab/LL-Q7737_(rus)-X-книга.wav/LL-Q7737_(rus)-X-книга.wav.mp3", author: "X", license: "CC BY-SA 4.0" },
  },
  homographs: ["замок"],
};

describe("pronunciations", () => {
  it("builds the API address of a recording", () => {
    expect(audioUrl("https://api.test/", "a/ab/Ru-дом.ogg")).toBe("https://api.test/v1/audio/a/ab/Ru-%D0%B4%D0%BE%D0%BC.ogg");
    expect(audioUrl("https://api.test", manifest.words["книга"]!.path)).toContain("/v1/audio/transcoded/a/ab/LL-Q7737_(rus)-X-");
  });

  it("finds a word by its lemma", () => {
    expect(wordKey("Кни́га")).toBe("книга");
    expect(lookup(manifest, "книга").kind).toBe("recording");
    expect(lookup(manifest, "замок").kind).toBe("homograph");
    expect(lookup(manifest, "стол").kind).toBe("none");
  });

  it("ships a list with credit for every recording", () => {
    const words = Object.entries((data as unknown as Manifest).words);
    expect(words.length).toBeGreaterThan(500);
    for (const [word, r] of words) {
      expect(word).toBe(wordKey(word));
      expect(r.author.trim()).not.toBe("");
      expect(r.license).toMatch(/^(CC BY(-SA)? \d\.\d( [A-Z]{2})?|CC0|Public domain)$/);
      expect(r.path).toMatch(/^(transcoded\/)?[0-9a-f]\/[0-9a-f]{2}\//);
    }
  });
});
