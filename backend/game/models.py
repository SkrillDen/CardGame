"""Core data models for the Durak-variant card game.

All game state lives in these dataclasses. The engine module operates on
`GameRoom` instances as pure data (no I/O), which keeps the rules fully
testable without a server or WebSocket connection.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import List, Optional, Set

# Suits: Spades, Hearts, Diamonds, Clubs.
SUITS = ("S", "H", "D", "C")

# Rank encoding: 6..10 numeric, 11=J, 12=Q, 13=K, 14=A.
RANK_NAMES = {11: "J", 12: "Q", 13: "K", 14: "A"}
SUIT_SYMBOLS = {"S": "♠", "H": "♥", "D": "♦", "C": "♣"}


@dataclass(frozen=True)
class Card:
    """An immutable card identified by suit and rank.

    String form is two characters for most ranks ("7H", "AS") and three for
    the 10 ("10D"). `Card.from_str` reverses this.
    """

    suit: str
    rank: int

    def __post_init__(self) -> None:
        if self.suit not in SUITS:
            raise ValueError(f"Invalid suit: {self.suit!r}")
        if not (6 <= self.rank <= 14):
            raise ValueError(f"Invalid rank: {self.rank!r}")

    @property
    def code(self) -> str:
        rank = RANK_NAMES.get(self.rank, str(self.rank))
        return f"{rank}{self.suit}"

    def __str__(self) -> str:  # e.g. "7H", "10D", "AS"
        return self.code

    def __repr__(self) -> str:  # keep repr compact for logs/debug
        return self.code

    @classmethod
    def from_str(cls, code: str) -> "Card":
        code = code.strip().upper()
        if len(code) < 2:
            raise ValueError(f"Invalid card code: {code!r}")
        suit = code[-1]
        rank_str = code[:-1]
        # reverse-lookup face names
        inv = {v: k for k, v in RANK_NAMES.items()}
        if rank_str in inv:
            rank = inv[rank_str]
        else:
            rank = int(rank_str)
        return cls(suit=suit, rank=rank)


# Player layers, consumed in this order: main -> buffer -> hidden.
LAYERS = ("main", "buffer", "hidden")


@dataclass
class Player:
    """A single player's full state across all three card layers."""

    id: str
    name: str
    main_hand: List[Card] = field(default_factory=list)
    buffer_share: List[Card] = field(default_factory=list)  # active buffer layer
    hidden_cards: List[Card] = field(default_factory=list)  # 2 face-down dealt cards
    layer: str = "main"  # which layer the player currently plays from
    hidden_taken: bool = False  # hidden cards moved into active play
    pending_share: List[Card] = field(default_factory=list)  # reserved buffer, not yet taken
    waiting_for_share: bool = False  # deferred trigger waiting for stack clear
    skip_next_turn: bool = False  # forfeit the next turn (hidden-card reveal)
    contributing: bool = False  # mid contribution phase
    eliminated: bool = False

    @property
    def total_cards(self) -> int:
        return len(self.main_hand) + len(self.buffer_share) + len(self.hidden_cards)

    @property
    def active_cards(self) -> List[Card]:
        """Cards the player can legally play right now (current layer only)."""
        if self.layer == "main":
            return self.main_hand
        if self.layer == "buffer":
            return self.buffer_share
        return self.hidden_cards

    def set_active(self, cards: List[Card]) -> None:
        """Replace the contents of the current active layer."""
        if self.layer == "main":
            self.main_hand = cards
        elif self.layer == "buffer":
            self.buffer_share = cards
        else:
            self.hidden_cards = cards


@dataclass
class GameRoom:
    """Complete mutable state of one game room.

    The engine functions in `game.engine` take this object, mutate it in place
    for convenience, and return it together with a list of events to broadcast.
    """

    room_id: str
    players: List[Player]  # turn order; index = seat
    dealer_idx: int = 0
    current_idx: int = 0  # whose turn it is
    trump: str = "H"
    table_stack: List[Card] = field(default_factory=list)  # [0]=bottom, [-1]=top
    bito: List[Card] = field(default_factory=list)  # discarded, out of play
    bito_count: int = 0
    buffer_pile: List[Card] = field(default_factory=list)  # shared buffer (2-3p only)
    buffer_distributed: bool = False
    contribution_phase: bool = False
    contribution_due: Set[str] = field(default_factory=set)  # player ids owing a contribution
    started: bool = False
    loser_id: Optional[str] = None  # set when game ends; the last player holding cards
    # Injected RNG so all randomness (trump picks, shuffles) is reproducible in tests.
    rng: random.Random = field(default_factory=random.Random)

    # ---- Derived helpers -------------------------------------------------

    @property
    def current_player(self) -> Player:
        return self.players[self.current_idx]

    @property
    def num_players(self) -> int:
        return len(self.players)

    @property
    def active_players(self) -> List[Player]:
        """Players still in the game (not eliminated)."""
        return [p for p in self.players if not p.eliminated]

    @property
    def num_active(self) -> int:
        return len(self.active_players)

    @property
    def is_two_three_player(self) -> bool:
        """Whether the buffer/balance mechanic applies (2 or 3 players)."""
        return self.num_players in (2, 3)

    def get_player(self, player_id: str) -> Optional[Player]:
        for p in self.players:
            if p.id == player_id:
                return p
        return None

    def player_index(self, player_id: str) -> int:
        for i, p in enumerate(self.players):
            if p.id == player_id:
                return i
        raise KeyError(player_id)


# ---------------------------------------------------------------------------
# Event helpers
# ---------------------------------------------------------------------------

def make_event(event_type: str, **payload) -> dict:
    """Build a broadcast event: {"type": <type>, "payload": {...}}."""
    return {"type": event_type, "payload": payload}
