import { describe, it, expect } from "vitest";
import { parseCard, cardLabel, suitColor, SUIT_SYMBOL } from "../game/cards";

describe("parseCard", () => {
  it("parses a plain numeric card", () => {
    const c = parseCard("7H");
    expect(c.suit).toBe("H");
    expect(c.rank).toBe(7);
    expect(c.rankLabel).toBe("7");
    expect(c.code).toBe("7H");
  });

  it("parses the three-char 10 code", () => {
    const c = parseCard("10D");
    expect(c.suit).toBe("D");
    expect(c.rank).toBe(10);
    expect(c.rankLabel).toBe("10");
  });

  it("parses face cards (J,Q,K,A)", () => {
    expect(parseCard("JS").rank).toBe(11);
    expect(parseCard("QC").rank).toBe(12);
    expect(parseCard("KH").rank).toBe(13);
    expect(parseCard("AS").rank).toBe(14);
    expect(parseCard("JS").rankLabel).toBe("J");
  });

  it("lowercases input is normalized to uppercase", () => {
    expect(parseCard("as").code).toBe("AS");
    expect(parseCard("10d").code).toBe("10D");
  });

  it("rejects invalid codes", () => {
    expect(() => parseCard("X")).toThrow();
    expect(() => parseCard("7X")).toThrow();
    expect(() => parseCard("5H")).toThrow(); // rank below 6
    expect(() => parseCard("15H")).toThrow(); // rank above 14
  });
});

describe("cardLabel", () => {
  it("combines rank label and suit symbol", () => {
    expect(cardLabel("7H")).toBe("7♥");
    expect(cardLabel("10D")).toBe("10♦");
    expect(cardLabel("AS")).toBe("A♠");
  });
});

describe("suitColor / symbol", () => {
  it("red hearts and diamonds", () => {
    expect(suitColor("H")).toBe("red");
    expect(suitColor("D")).toBe("red");
  });
  it("black spades and clubs", () => {
    expect(suitColor("S")).toBe("black");
    expect(suitColor("C")).toBe("black");
  });
  it("symbols for all suits", () => {
    expect(SUIT_SYMBOL.S).toBe("♠");
    expect(SUIT_SYMBOL.H).toBe("♥");
    expect(SUIT_SYMBOL.D).toBe("♦");
    expect(SUIT_SYMBOL.C).toBe("♣");
  });
});
