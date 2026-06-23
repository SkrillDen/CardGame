"""Deck generation, shuffle, and initial deal.

The deal is pure and takes an injectable ``random.Random`` so tests can be
fully deterministic.

Deal structure (for ``num_players`` = N):
  * 2 hidden cards per player  -> 2*N cards face-down
  * 1 opening card placed face-up on the table (the first player's automatic
    first move) -> 1 card
  * remaining cards dealt round-robin into main hands.
    For 2-3p this divides evenly; for 4-5p the remainder falls to the
    earliest seats (documented, deterministic).
"""

from __future__ import annotations

import random
from typing import List, Tuple

from .models import Card, SUITS

# Initial trump is chosen from these suits only (Spades excluded at game start).
INITIAL_TRUMP_CANDIDATES = ("H", "D", "C")


def build_deck() -> List[Card]:
    """Return a fresh ordered 36-card deck (6-A across all four suits)."""
    return [Card(suit=s, rank=r) for s in SUITS for r in range(6, 15)]


def shuffle_deck(deck: List[Card], rng: random.Random) -> List[Card]:
    """Return a shuffled copy of ``deck`` (original is left untouched)."""
    shuffled = list(deck)
    rng.shuffle(shuffled)
    return shuffled


def deal_hands(num_players: int, rng: random.Random) -> Tuple[List[List[Card]], List[List[Card]], Card]:
    """Deal hidden hands, main hands, and the opening table card.

    Returns ``(hidden_per_player, main_per_player, opening_card)``.

    The opening card is the *last* card dealt overall; it goes to the table,
    not into any player's hand. Per the resolved rules, this counts as the
    first player's (left of dealer) automatic first move, but the card itself
    is not taken from their hand.
    """
    if not (2 <= num_players <= 5):
        raise ValueError(f"num_players must be 2..5, got {num_players}")

    deck = shuffle_deck(build_deck(), rng)

    hidden: List[List[Card]] = [[] for _ in range(num_players)]
    # Reserve the opening table card first (last card of the deck).
    opening_card = deck.pop()
    remaining = deck

    # Deal 2 hidden cards per player.
    for _ in range(2):
        for i in range(num_players):
            hidden[i].append(remaining.pop())

    # Everything left is main-hand pool; deal round-robin.
    main: List[List[Card]] = [[] for _ in range(num_players)]
    idx = 0
    while remaining:
        main[idx % num_players].append(remaining.pop())
        idx += 1

    return hidden, main, opening_card


def choose_initial_trump(rng: random.Random) -> str:
    """Pick the initial trump uniformly from H/D/C (never Spades)."""
    return rng.choice(INITIAL_TRUMP_CANDIDATES)


def choose_weighted_trump(buffer_pile: List[Card], rng: random.Random) -> str:
    """Pick a new trump weighted by suit counts in the buffer pile.

    Equivalent to drawing one card uniformly at random from the pile and
    taking its suit. The drawn card is conceptually shuffled back, so the
    buffer pile itself is not mutated here.
    """
    if not buffer_pile:
        # No buffer to draw from; fall back to an initial-style pick.
        return rng.choice(INITIAL_TRUMP_CANDIDATES)
    drawn = rng.choice(buffer_pile)
    return drawn.suit
