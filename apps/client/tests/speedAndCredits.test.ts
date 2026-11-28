import { describe, expect, it } from "vitest";
import manifestData from "../src/data/pronunciations.json";
import { authorCredits, commonsPage, licenseUrl, licensesUsed } from "../src/pronunciation/credits";
import { nextSpeed, SLOWER_WITHIN_MS } from "../src/pronunciation/player";
import type { Manifest } from "../src/pronunciation/source";

describe("listen pressed again", () => {
  it("goes 1x, 0.75x, 0.5x and back to 1x", () => {
    const a = nextSpeed(null, 0);
    const b = nextSpeed({ speed: a, at: 0 }, 1000);
    const c = nextSpeed({ speed: b, at: 1000 }, 2000);
    const d = nextSpeed({ speed: c, at: 2000 }, 3000);
    expect([a, b, c, d]).toEqual([1, 0.75, 0.5, 1]);
  });

  it("starts at normal speed again after a pause longer than 5 seconds", () => {
    expect(nextSpeed({ speed: 0.75, at: 0 }, SLOWER_WITHIN_MS)).toBe(0.5);
    expect(nextSpeed({ speed: 0.75, at: 0 }, SLOWER_WITHIN_MS + 1)).toBe(1);
    expect(nextSpeed({ speed: 0.5, at: 10_000 }, 9_000)).toBe(1);
  });
});

describe("pronunciation credits", () => {
  const manifest: Manifest = {
    homographs: [],
    words: {
      а: { file: "a.wav", path: "x", author: "B", license: "CC BY-SA 4.0" },
      б: { file: "b.wav", path: "x", author: "A", license: "CC BY-SA 4.0" },
      в: { file: "c.wav", path: "x", author: "B", license: "CC BY-SA 4.0" },
      г: { file: "d.ogg", path: "x", author: "B", license: "CC BY 2.0 FR" },
    },
  };

  it("groups words by author and licence, most words first", () => {
    expect(authorCredits(manifest)).toEqual([
      { author: "B", license: "CC BY-SA 4.0", words: 2 },
      { author: "A", license: "CC BY-SA 4.0", words: 1 },
      { author: "B", license: "CC BY 2.0 FR", words: 1 },
    ]);
    expect(licensesUsed(authorCredits(manifest))).toEqual(["CC BY 2.0 FR", "CC BY-SA 4.0"]);
  });

  it("links each licence to its text", () => {
    expect(licenseUrl("CC BY-SA 4.0")).toBe("https://creativecommons.org/licenses/by-sa/4.0/");
    expect(licenseUrl("CC BY 2.0 FR")).toBe("https://creativecommons.org/licenses/by/2.0/fr/");
    expect(licenseUrl("CC0")).toBe("https://creativecommons.org/publicdomain/zero/1.0/");
    expect(licenseUrl("Public domain")).toBe("");
    expect(commonsPage("Ru-кот.ogg")).toBe("https://commons.wikimedia.org/wiki/File:Ru-%D0%BA%D0%BE%D1%82.ogg");
  });

  it("credits every recording the app ships with a real author and a known licence", () => {
    const data = manifestData as unknown as Manifest;
    const credits = authorCredits(data);
    expect(credits.reduce((n, c) => n + c.words, 0)).toBe(Object.keys(data.words).length);
    for (const c of credits) {
      expect(c.author).toMatch(/\p{L}/u);
      expect(c.author).not.toMatch(/^\[\d+\]$/);
      expect(c.license === "Public domain" || licenseUrl(c.license) !== "").toBe(true);
    }
  });
});
