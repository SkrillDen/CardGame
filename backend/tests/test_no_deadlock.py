"""Regression tests for the turn/layer deadlocks reported in 2-3 player games.

These guard the invariant that the game never stalls on a player who has no
card to play and no stack to take from ("a move is expected but there are no
cards"), across the buffer / hidden-card lifecycle.
"""
import random

import pytest

from game.engine import (
    deal_cards, play_card, take_bottom, contribute_buffer, validate_beat,
)
from game.models import Card, GameRoom, Player
from tests.conftest import make_player, room_with

C = Card.from_str


# ---------------------------------------------------------------------------
# Targeted regressions
# ---------------------------------------------------------------------------

def test_waiting_trigger_opening_empty_stack_gets_share_not_deadlock():
    """2p: the deferred trigger's turn comes up on an EMPTY stack (they must
    open) but they have no main cards. They must collect their deferred share
    instead of stalling."""
    players = [make_player("p0", []), make_player("p1", [C("6C")])]
    room = room_with(players, trump="D", stack=[C("9H")], current_idx=1)
    room.players[0].waiting_for_share = True
    room.players[0].pending_share = [C("9C"), C("6S")]
    room.buffer_distributed = True
    # p1 takes the only stack card -> stack empties -> turn moves to p0.
    room, _ = take_bottom(room, "p1")
    p0 = room.players[0]
    if room.current_player.id == "p0":
        assert p0.active_cards, "current player p0 must have cards to play"
        assert p0.layer == "buffer"
        assert p0.waiting_for_share is False


def test_contribution_emptying_main_triggers_distribution():
    """A contribution that empties a player's main hand must trigger buffer
    distribution (same as playing the last card), so the player isn't stranded
    on an empty main layer with the buffer never distributed."""
    players = [make_player("p0", [C("9H")]),  # one card -> contributing empties main
               make_player("p1", [C("JH"), C("JC")])]
    room = room_with(players, trump="D", stack=[])
    room.buffer_pile = [C("7D"), C("8D")]
    room.contribution_phase = True
    room.contribution_due = {"p0", "p1"}
    room, events = contribute_buffer(room, "p0", C("9H"))
    assert room.buffer_distributed is True
    assert room.players[0].main_hand == []
    assert "buffer_triggered" in [e["type"] for e in events]
    # Contribution phase must have ended (distribution supersedes it).
    assert room.contribution_phase is False


def test_forced_take_cards_not_orphaned_when_share_resolves():
    """A waiting trigger that took bottom cards back into their (reopened) main
    hand must carry those cards over to the buffer layer when the share
    resolves — they must not be stranded."""
    players = [make_player("p0", [C("8D"), C("10D")]),  # 'reopened' main via forced takes
               make_player("p1", [C("JH")])]
    room = room_with(players, trump="D", stack=[C("7H")], current_idx=1)
    room.players[0].waiting_for_share = True
    room.players[0].pending_share = [C("9C")]
    room.buffer_distributed = True
    # p1 plays JH -> stack [7H, JH] len 2 == active -> bito -> p0 resolves share.
    room, _ = play_card(room, "p1", C("JH"))
    p0 = room.players[0]
    assert p0.waiting_for_share is False
    assert p0.layer == "buffer"
    # The two leftover main cards + the share card all land in the buffer layer.
    codes = {c.code for c in p0.buffer_share}
    assert codes == {"8D", "10D", "9C"}
    assert p0.main_hand == []


def test_eliminated_closer_after_bito_passes_turn():
    """If the player who closes a bito eliminated themselves on that same play,
    the turn must move to a player who can act rather than resting on the
    eliminated closer."""
    players = [
        make_player("p0", [], hidden=[C("9H")], layer="hidden"),
        make_player("p1", [C("JH")]),
        make_player("p2", [C("QH")]),
    ]
    room = room_with(players, trump="D", stack=[C("7H"), C("8H")], current_idx=0)
    room.players[0].hidden_taken = True
    # p0 plays their last hidden card -> stack reaches 3 == active -> bito, and
    # p0 is eliminated. In 3p this also starts a contribution phase.
    room, _ = play_card(room, "p0", C("9H"))
    # Drive any contribution phase to completion.
    for _ in range(5):
        if not room.contribution_phase:
            break
        for pid in list(room.contribution_due):
            pl = room.get_player(pid)
            if pl.main_hand:
                room, _ = contribute_buffer(room, pid, pl.main_hand[0])
            else:
                room.contribution_due.discard(pid)
    # Once play resumes, the turn must not rest on the eliminated closer.
    if room.loser_id is None:
        assert not room.current_player.eliminated
        assert room.current_player.active_cards or room.table_stack


# ---------------------------------------------------------------------------
# Property test: auto-play many random games, assert no hard deadlock
# ---------------------------------------------------------------------------

def _legal_play(room, player):
    top = room.table_stack[-1] if room.table_stack else None
    for c in list(player.active_cards):
        if top is None or validate_beat(top, c, room.trump):
            return c
    return None


def _auto_play(seed, n, max_steps=4000):
    rng = random.Random(seed)
    room, _ = deal_cards(n, rng=rng)
    for _ in range(max_steps):
        if room.loser_id is not None:
            return  # finished cleanly
        if room.contribution_phase:
            for pid in list(room.contribution_due):
                pl = room.get_player(pid)
                if pl.main_hand:
                    room, _ = contribute_buffer(room, pid, pl.main_hand[0])
                else:
                    room.contribution_due.discard(pid)
            if not room.contribution_due:
                room.contribution_phase = False
            continue
        p = room.current_player
        can_take = len(room.table_stack) > 0
        card = _legal_play(room, p)
        # The invariant under test: the current player always has SOMETHING to
        # do — a card to play or a stack to take.
        assert card is not None or can_take, (
            f"DEADLOCK seed={seed} n={n} player={p.id} layer={p.layer} "
            f"main={p.main_hand} buffer={p.buffer_share} hidden={p.hidden_cards} "
            f"waiting={p.waiting_for_share} stack={room.table_stack}"
        )
        if card is not None and rng.random() < 0.7:
            room, _ = play_card(room, p.id, card)
        elif can_take:
            room, _ = take_bottom(room, p.id)
        else:
            room, _ = play_card(room, p.id, card)


@pytest.mark.parametrize("n", [2, 3])
def test_auto_play_never_deadlocks(n):
    for seed in range(400):
        _auto_play(seed, n)
