import { describe, expect, it } from "vitest";
import {
  compareRu, compareUz, ruInitial, sections, uzHead, uzInitial, uzLetters, uzMatch, RU_LETTERS, UZ_LETTERS,
} from "../src/dictionary/alphabet";

describe("Uzbek order", () => {
  it("puts O', G', Sh, Ch after Z, as the Uzbek alphabet does", () => {
    const words = ["choy", "olma", "o'rik", "shahar", "zamon", "g'isht", "gul", "sabzi", "xona"];
    expect([...words].sort(compareUz)).toEqual(["gul", "olma", "sabzi", "xona", "zamon", "o'rik", "g'isht", "shahar", "choy"]);
  });

  it("reads every spelling of the apostrophe the same", () => {
    expect(uzInitial("oʻrik")).toBe("O'");
    expect(uzInitial("g’isht")).toBe("G'");
    expect(uzLetters("o'rik")).toEqual(uzLetters("oʻrik"));
  });

  it("gives the section letter", () => {
    expect(uzInitial("Shahar")).toBe("Sh");
    expect(uzInitial("chiroyli")).toBe("Ch");
    expect(uzInitial("-")).toBe("");
  });
});

describe("Uzbek headword and search", () => {
  it("takes the first meaning that is a word", () => {
    expect(uzHead("-da, -ga, ichida, ichiga")).toBe("ichida");
    expect(uzHead("u (erkak)")).toBe("u");
    expect(uzHead("-dan")).toBe("dan");
    expect(uzHead("kitob")).toBe("kitob");
  });

  it("ranks exact meanings first, then beginnings, then anything containing the query", () => {
    expect(uzMatch("kitob", "kitob")).toBe(0);
    expect(uzMatch("kit", "kitob, daftar")).toBe(1);
    expect(uzMatch("yaxshi", "juda yaxshi")).toBe(1);
    expect(uzMatch("tob", "kitob")).toBe(2);
    expect(uzMatch("uy", "kitob")).toBe(-1);
    expect(uzMatch("o‘rmon", "o'rmon")).toBe(0);
  });
});

describe("Russian order", () => {
  it("sorts and puts Ё with Е", () => {
    expect(["яблоко", "ёж", "арбуз", "еда"].sort(compareRu)).toEqual(["арбуз", "еда", "ёж", "яблоко"]);
    expect(ruInitial("ёж")).toBe("Е");
    expect(ruInitial("книга")).toBe("К");
  });
});

describe("sections", () => {
  it("cuts a list into letters in alphabet order", () => {
    const s = sections(["вода", "арбуз", "вино", "1"], ruInitial, RU_LETTERS);
    expect(s.map((x) => [x.letter, x.items])).toEqual([["А", ["арбуз"]], ["В", ["вода", "вино"]], ["#", ["1"]]]);
    expect(sections(["shahar", "olma"], uzInitial, UZ_LETTERS).map((x) => x.letter)).toEqual(["O", "Sh"]);
  });
});
