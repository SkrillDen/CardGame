import { describe, it, expect } from "vitest";
import { canBeat, canBeatAny } from "../game/rules";

describe("canBeat — same suit (non-spade)", () => {
  it("higher rank beats lower in same suit", () => {
    expect(canBeat("7H", "9H", "D")).toBe(true);
  });
  it("equal rank does not beat", () => {
    expect(canBeat("7H", "7H", "D")).toBe(false);
  });
  it("lower rank does not beat", () => {
    expect(canBeat("9H", "7H", "D")).toBe(false);
  });
});

describe("canBeat — trump (non-spade)", () => {
  it("trump beats a non-trump", () => {
    expect(canBeat("7H", "6D", "D")).toBe(true);
  });
  it("non-trump cannot beat a trump", () => {
    expect(canBeat("7D", "AH", "D")).toBe(false);
  });
  it("trump vs trump needs higher rank", () => {
    expect(canBeat("7D", "9D", "D")).toBe(true);
    expect(canBeat("9D", "7D", "D")).toBe(false);
  });
  it("different non-trump suits do not beat", () => {
    expect(canBeat("7H", "9C", "D")).toBe(false);
  });
});

describe("canBeat — spade immunity (being beaten)", () => {
  it("spade beaten only by higher spade, never by trump", () => {
    expect(canBeat("7S", "9S", "H")).toBe(true);
    expect(canBeat("7S", "AH", "H")).toBe(false); // trump heart
    expect(canBeat("7S", "AC", "H")).toBe(false); // higher non-spade
    expect(canBeat("7S", "AD", "D")).toBe(false); // trump diamond
    expect(canBeat("7S", "AC", "C")).toBe(false); // trump club
  });
  it("when spades are trump, only higher spade wins", () => {
    expect(canBeat("7S", "9S", "S")).toBe(true);
    expect(canBeat("9S", "7S", "S")).toBe(false);
    expect(canBeat("7S", "AH", "S")).toBe(false);
  });
});

describe("canBeat — spade immunity (doing the beating)", () => {
  it("spade cannot beat a non-spade", () => {
    expect(canBeat("7H", "AS", "H")).toBe(false);
  });
  it("spade cannot beat a non-spade even if spades are trump", () => {
    expect(canBeat("7H", "AS", "S")).toBe(false);
  });
  it("spade cannot beat a trump card", () => {
    expect(canBeat("7D", "AS", "D")).toBe(false);
  });
});

describe("canBeatAny", () => {
  it("null top just needs any card", () => {
    expect(canBeatAny(["7H"], null, "D")).toBe(true);
    expect(canBeatAny([], null, "D")).toBe(false);
  });
  it("finds a winning card", () => {
    expect(canBeatAny(["6H", "9H"], "7H", "D")).toBe(true);
    expect(canBeatAny(["6H"], "7H", "D")).toBe(false);
  });
  it("spade top needs a spade", () => {
    expect(canBeatAny(["AH", "9S"], "7S", "H")).toBe(true);
    expect(canBeatAny(["AH"], "7S", "H")).toBe(false);
  });
});
