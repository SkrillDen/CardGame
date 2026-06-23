"""Shared pytest fixtures and helpers."""

from __future__ import annotations

import random
from typing import List, Tuple

import pytest

from game.deck import build_deck, shuffle_deck
from game.engine import deal_cards
from game.models import Card, GameRoom, Player


@pytest.fixture
def rng() -> random.Random:
    """A fresh seeded RNG so deals are reproducible."""
    return random.Random(1234)


def event_types(events) -> List[str]:
    return [e["type"] for e in events]


def events_of(room_events, *types: str):
    want = set(types)
    return [e for e in room_events if e["type"] in want]


def make_player(pid: str, main: List[Card], hidden: List[Card] | None = None,
                layer: str = "main") -> Player:
    return Player(
        id=pid,
        name=f"Name{pid}",
        main_hand=list(main),
        hidden_cards=list(hidden or []),
        layer=layer,
    )


def room_with(players: List[Player], trump: str = "H", stack: List[Card] | None = None,
              current_idx: int = 0, rng: random.Random | None = None) -> GameRoom:
    room = GameRoom(
        room_id="test",
        players=players,
        trump=trump,
        table_stack=list(stack or []),
        current_idx=current_idx,
        started=True,
        rng=rng or random.Random(0),
    )
    return room


def deal_for(num_players: int, rng: random.Random) -> Tuple[GameRoom, list]:
    """Deal a fresh room, convenient for engine scenario tests."""
    return deal_cards(num_players, rng=rng)
