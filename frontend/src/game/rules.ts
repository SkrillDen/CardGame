// Client-side beating-rule mirror. Used only for UI hints (which cards are
// playable). The server remains the source of truth; the server may still
// reject a play the client thinks is legal.

// Mirrors backend `validate_beat` in game/engine.py exactly:
//   * When spades are NOT trump they are a closed domain — beaten only by a
//     higher spade, and a spade never beats a non-spade.
//   * When spades ARE trump they act as a normal trump: any spade beats any
//     non-spade, higher spade beats lower spade.
//   * Same suit: higher rank wins.
//   * Trump beats a non-trump; trump beats trump only by higher rank.

import type { CardCode, Suit } from "../types";
import { parseCard } from "./cards";

export function canBeat(toBeat: CardCode, played: CardCode, trump: Suit): boolean {
  const a = parseCard(toBeat);
  const b = parseCard(played);

  // Closed spade domain only applies while spades are not the trump.
  if (trump !== "S") {
    if (a.suit === "S") {
      return b.suit === "S" && b.rank > a.rank;
    }
    if (b.suit === "S") {
      return false;
    }
  }
  if (a.suit === b.suit) {
    return b.rank > a.rank;
  }
  if (a.suit === trump) {
    return false;
  }
  if (b.suit === trump) {
    return true;
  }
  return false;
}

/** True if any card in `hand` can beat `top`. top==null means fresh stack. */
export function canBeatAny(hand: CardCode[], top: CardCode | null, trump: Suit): boolean {
  if (top === null) return hand.length > 0;
  return hand.some((c) => canBeat(top, c, trump));
}
