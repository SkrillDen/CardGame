// Card code parsing and presentation helpers. Mirrors backend's Card.code.

import type { CardCode, Suit } from "../types";

export const SUITS: readonly Suit[] = ["S", "H", "D", "C"] as const;

export const SUIT_SYMBOL: Record<Suit, string> = {
  S: "♠",
  H: "♥",
  D: "♦",
  C: "♣",
};

/** Hearts/Diamonds red, Spades/Clubs black. */
export function suitColor(suit: Suit): "red" | "black" {
  return suit === "H" || suit === "D" ? "red" : "black";
}

const RANK_NAMES: Record<number, string> = {
  11: "J",
  12: "Q",
  13: "K",
  14: "A",
};

export interface ParsedCard {
  suit: Suit;
  rank: number;
  rankLabel: string; // "7","10","J"...
  code: CardCode;
}

/** Parse a card code like "7H", "10D", "AS" into structured form. */
export function parseCard(code: CardCode): ParsedCard {
  const c = code.trim().toUpperCase();
  if (c.length < 2 || c.length > 3) {
    throw new Error(`Invalid card code: ${code}`);
  }
  const suit = c.slice(-1) as Suit;
  if (!SUITS.includes(suit)) {
    throw new Error(`Invalid suit in card code: ${code}`);
  }
  const rankStr = c.slice(0, -1);
  const inv: Record<string, number> = { J: 11, Q: 12, K: 13, A: 14 };
  let rank: number;
  if (rankStr in inv) {
    rank = inv[rankStr];
  } else {
    rank = parseInt(rankStr, 10);
    if (Number.isNaN(rank) || rank < 6 || rank > 10) {
      throw new Error(`Invalid rank in card code: ${code}`);
    }
  }
  return { suit, rank, rankLabel: RANK_NAMES[rank] ?? String(rank), code: c };
}

/** Human label like "7♥", "10♦", "A♠". */
export function cardLabel(code: CardCode): string {
  const { rankLabel, suit } = parseCard(code);
  return `${rankLabel}${SUIT_SYMBOL[suit]}`;
}
