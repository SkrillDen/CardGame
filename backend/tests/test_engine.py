"""Engine scenario tests: turns, beats, bito, layers, buffer lifecycle."""

import random

import pytest

from game.engine import (
    contribute_buffer,
    deal_cards,
    join_room,
    create_room,
    start_game,
    play_card,
    take_bottom,
    trigger_buffer_distribution,
    check_bito,
    check_layer_transition,
)
from game.models import Card, GameRoom, Player
from tests.conftest import event_types, events_of, make_player, room_with

C = Card.from_str


# ===========================================================================
# deal_cards / lobby
# ===========================================================================

def test_deal_cards_initial_state(rng):
    room, events = deal_cards(3, rng=rng)
    assert room.started
    assert len(room.players) == 3
    # Opener on the table, first to act is seat 1.
    assert len(room.table_stack) == 1
    assert room.current_idx == 1
    assert room.trump in ("H", "D", "C")
    types = event_types(events)
    assert "game_started" in types
    assert "card_played" in types
    assert "game_state" in types


def test_deal_cards_private_hand_events(rng):
    room, events = deal_cards(2, rng=rng)
    hand_updates = [e for e in events if e["type"] == "hand_update"]
    assert len(hand_updates) == 2
    targets = {e["payload"]["_to"] for e in hand_updates}
    assert targets == {"p0", "p1"}


def test_lobby_create_join_start():
    room, _ = create_room("Alice", room_id="r1")
    assert len(room.players) == 1
    room, _ = join_room(room, "Bob")
    assert len(room.players) == 2
    room, events = start_game(room, rng=random.Random(1))
    assert room.started
    assert "game_started" in event_types(events)


# ===========================================================================
# play_card: basic beats and errors
# ===========================================================================

def test_play_card_valid_beat_advances_turn(rng):
    # 3 players so a 2-card stack doesn't trigger bito. Top is 7H; p1 beats it.
    players = [
        make_player("p0", [C("AS")]),
        make_player("p1", [C("9H")]),
        make_player("p2", [C("6C")]),
    ]
    room = room_with(players, trump="D", stack=[C("7H")], current_idx=1)
    room, events = play_card(room, "p1", C("9H"))
    assert "card_played" in event_types(events)
    assert room.current_player.id == "p2"
    assert room.table_stack[-1].code == "9H"
    # p1 still has the played card removed.
    assert all(c.code != "9H" for c in room.players[1].main_hand)


def test_play_card_illegal_beat_emits_error_no_state_change(rng):
    players = [
        make_player("p0", [C("AS")]),
        make_player("p1", [C("6H")]),
    ]
    room = room_with(players, trump="D", stack=[C("7H")], current_idx=1)
    before_stack = list(room.table_stack)
    before_current = room.current_idx
    room, events = play_card(room, "p1", C("6H"))
    assert any(e["type"] == "error" for e in events)
    assert room.table_stack == before_stack
    assert room.current_idx == before_current


def test_play_card_not_your_turn_error():
    players = [make_player("p0", [C("9H")]), make_player("p1", [C("9H")])]
    room = room_with(players, trump="D", stack=[C("7H")], current_idx=1)
    room, events = play_card(room, "p0", C("9H"))
    assert any(e["type"] == "error" for e in events)


def test_play_card_card_not_in_hand_error():
    players = [make_player("p0", [C("AS")]), make_player("p1", [C("9H")])]
    room = room_with(players, trump="D", stack=[C("7H")], current_idx=1)
    room, events = play_card(room, "p1", C("AH"))
    assert any(e["type"] == "error" for e in events)


# ===========================================================================
# take_bottom
# ===========================================================================

def test_take_bottom_moves_bottom_card_to_main_hand():
    players = [make_player("p0", [C("AS")]), make_player("p1", [])]
    room = room_with(players, trump="D", stack=[C("7H"), C("9H")], current_idx=1)
    room, events = take_bottom(room, "p1")
    assert "card_taken" in event_types(events)
    hand_updates = [e for e in events if e["type"] == "hand_update"]
    assert len(hand_updates) == 1
    assert hand_updates[0]["payload"]["_to"] == "p1"
    assert hand_updates[0]["payload"]["cards"] == ["7H"]
    assert room.table_stack == [C("9H")]
    assert room.players[1].main_hand[-1].code == "7H"
    # Turn advanced.
    assert room.current_player.id == "p0"


def test_take_bottom_empty_stack_error():
    players = [make_player("p0", [C("AS")]), make_player("p1", [])]
    room = room_with(players, trump="D", stack=[], current_idx=1)
    room, events = take_bottom(room, "p1")
    assert any(e["type"] == "error" for e in events)


def test_take_bottom_on_hidden_layer_stays_hidden_and_adds_card():
    players = [
        make_player("p0", [C("AS")]),
        make_player("p1", [], hidden=[C("9C"), C("6S")], layer="hidden"),
    ]
    room = room_with(players, trump="D", stack=[C("7H"), C("9H")], current_idx=1)
    room.players[1].hidden_taken = True
    room, events = take_bottom(room, "p1")
    assert room.players[1].layer == "hidden"
    assert [c.code for c in room.players[1].hidden_cards] == ["9C", "6S", "7H"]
    hand_updates = [e for e in events if e["type"] == "hand_update"]
    assert len(hand_updates) == 1
    assert hand_updates[0]["payload"]["cards"] == ["9C", "6S", "7H"]


def test_take_bottom_on_buffer_layer_stays_buffer_and_adds_card():
    players = [
        make_player("p0", [C("AS")]),
        make_player("p1", [], layer="buffer"),
    ]
    players[1].buffer_share = [C("9C"), C("6S")]
    room = room_with(players, trump="D", stack=[C("7H"), C("9H")], current_idx=1)
    room, events = take_bottom(room, "p1")
    assert room.players[1].layer == "buffer"
    assert [c.code for c in room.players[1].buffer_share] == ["9C", "6S", "7H"]
    hand_updates = [e for e in events if e["type"] == "hand_update"]
    assert len(hand_updates) == 1
    assert hand_updates[0]["payload"]["cards"] == ["9C", "6S", "7H"]


# ===========================================================================
# bito
# ===========================================================================

def test_bito_clears_stack_and_closer_reopens():
    # 2 players, both active; stack already at 2 => bito on next beat.
    # Give each player a spare card so the closer still holds a card to reopen
    # with (an emptied hand would instead trigger buffer distribution and pass
    # the turn — covered separately).
    players = [make_player("p0", [C("9H"), C("9C")]),
               make_player("p1", [C("JH"), C("JC")])]
    room = room_with(players, trump="D", stack=[C("7H")], current_idx=1)
    # p1 plays JH -> stack [7H, JH] length 2 == active => bito.
    room, events = play_card(room, "p1", C("JH"))
    assert "bito" in event_types(events)
    assert room.table_stack == []
    assert room.bito_count == 1
    # Closer (p1) still holds JC, so they reopen the next stack: stays current.
    assert room.current_player.id == "p1"


def test_bito_contribution_phase_2p_only_every_second():
    # 2p: after first bito, no contribution; after second, yes.
    # Use check_bito directly so no buffer-distribution side effects kick in.
    players = [make_player("p0", [C("9H"), C("9C")]),
               make_player("p1", [C("JH"), C("JC")])]
    room = room_with(players, trump="D")
    # First bito: stack of 2 in a 2p game.
    room.table_stack = [C("7H"), C("9H")]
    room, events = check_bito(room)
    assert "bito" in event_types(events)
    assert room.bito_count == 1
    assert room.contribution_phase is False  # 2p: only every 2nd
    # Second bito.
    room.table_stack = [C("7C"), C("9C")]
    room, events = check_bito(room)
    assert room.bito_count == 2
    assert room.contribution_phase is True
    assert room.contribution_due == {"p0", "p1"}


def test_bito_contribution_phase_3p_every_time():
    players = [
        make_player("p0", [C("9H")]),
        make_player("p1", [C("JH")]),
        make_player("p2", [C("QH")]),
    ]
    room = room_with(players, trump="D")
    # Stack of 3 in a 3p game => bito, and 3p => contribution every time.
    room.table_stack = [C("7H"), C("9H"), C("JH")]
    room, events = check_bito(room)
    assert "bito" in event_types(events)
    assert room.contribution_phase is True
    assert room.contribution_due == {"p0", "p1", "p2"}


# ===========================================================================
# Contribution
# ===========================================================================

def test_contribute_buffer_collects_and_clears_phase():
    # Two main cards each so contributing one doesn't empty the hand (an empty
    # main during contribution triggers buffer distribution — tested elsewhere).
    players = [make_player("p0", [C("9H"), C("9C")]),
               make_player("p1", [C("JH"), C("JC")])]
    room = room_with(players, trump="D", stack=[])
    room.contribution_phase = True
    room.contribution_due = {"p0", "p1"}
    room, events = contribute_buffer(room, "p0", C("9H"))
    assert "buffer_contributed" in event_types(events)
    hand_updates = [e for e in events if e["type"] == "hand_update"]
    assert len(hand_updates) == 1
    assert hand_updates[0]["payload"]["_to"] == "p0"
    assert hand_updates[0]["payload"]["cards"] == ["9C"]
    game_states = [e for e in events if e["type"] == "game_state"]
    assert len(game_states) == 1
    assert game_states[0]["payload"]["buffer_size"] == 1
    assert game_states[0]["payload"]["contribution_phase"] is True
    assert "p0" not in room.contribution_due
    assert room.contribution_phase is True
    assert len(room.buffer_pile) == 1
    room, events = contribute_buffer(room, "p1", C("JH"))
    assert room.contribution_phase is False
    assert room.contribution_due == set()
    assert len(room.buffer_pile) == 2


def test_contribute_buffer_when_not_due_errors():
    players = [make_player("p0", [C("9H")]), make_player("p1", [C("JH")])]
    room = room_with(players, trump="D", stack=[])
    room.contribution_phase = True
    room.contribution_due = {"p0"}
    room, events = contribute_buffer(room, "p1", C("JH"))
    assert any(e["type"] == "error" for e in events)


# ===========================================================================
# Buffer distribution + deferred trigger (2-3p)
# ===========================================================================

def test_trigger_buffer_distribution_sets_trump_and_shares():
    players = [make_player("p0", []), make_player("p1", [])]
    room = room_with(players, trump="H", stack=[C("7H")])
    room.buffer_pile = [C("9D"), C("JC"), C("6H"), C("7S")]
    rng = random.Random(0)
    room.rng = rng
    room, events = trigger_buffer_distribution(room, "p0")
    assert "buffer_triggered" in event_types(events)
    assert room.buffer_distributed is True
    assert room.buffer_pile == []
    # All 4 cards split between 2 players.
    total = sum(len(p.pending_share) for p in room.players)
    assert total == 4
    # Trigger is deferred.
    assert room.players[0].waiting_for_share is True
    assert room.players[1].waiting_for_share is False


def test_deferred_trigger_takes_share_on_bito_no_skip():
    # p0 emptied main hand -> triggered distribution; on bito, takes share.
    players = [
        make_player("p0", []),  # waiting for share
        make_player("p1", [C("JH")]),
    ]
    room = room_with(players, trump="D", stack=[C("7H")], current_idx=1)
    room.players[0].waiting_for_share = True
    room.players[0].pending_share = [C("9C"), C("6S")]
    room.buffer_distributed = True
    # p1 plays JH -> stack reaches 2 (== active) -> bito.
    room, events = play_card(room, "p1", C("JH"))
    assert "bito" in event_types(events)
    # p0 took the share, now on buffer layer, no skip flag.
    p0 = room.players[0]
    assert p0.waiting_for_share is False
    assert p0.layer == "buffer"
    assert len(p0.buffer_share) == 2
    assert p0.skip_next_turn is False
    buffer_shares = [e for e in events if e["type"] == "buffer_share"]
    assert len(buffer_shares) == 1
    assert buffer_shares[0]["payload"]["_to"] == "p0"
    assert buffer_shares[0]["payload"]["cards"] == ["9C", "6S"]


def test_waiting_trigger_turn_lands_and_can_take_not_force_fed():
    # 2 players. p0 is waiting for share with a non-empty stack. When the turn
    # reaches p0 they are NOT force-fed a card; the turn simply rests on them so
    # they may act (here: take the bottom, since they hold no cards to play).
    players = [
        make_player("p0", []),  # waiting, empty main
        make_player("p1", [C("6C")]),
    ]
    room = room_with(players, trump="D", stack=[C("7H"), C("9H")], current_idx=1)
    room.players[0].waiting_for_share = True
    room.players[0].pending_share = [C("9C"), C("6S")]
    room.buffer_distributed = True
    # p1 takes bottom -> stack becomes [9H], turn advances to p0.
    room, events = take_bottom(room, "p1")
    # p0 is current, still waiting, with the stack available to take from.
    assert room.current_player.id == "p0"
    assert room.players[0].main_hand == []  # NOT force-fed
    assert room.table_stack == [C("9H")]
    # p0 chooses to take the bottom -> reopens their main hand with 9H and can
    # play it on a later turn.
    room, events = take_bottom(room, "p0")
    assert any(c.code == "9H" for c in room.players[0].main_hand)
    assert room.players[0].layer == "main"


def test_player_never_beats_their_own_card_in_2p():
    # 2p: p1 is on the hidden layer with skip_next_turn set (just revealed).
    # p0 opens a stack; honouring p1's skip would loop the turn back to p0 and
    # force them to beat their own card. Instead the turn must go to p1.
    p0 = make_player("p0", [], layer="buffer")
    p0.buffer_share = [C("9D"), C("KD")]
    p1 = make_player("p1", [], hidden=[C("7C")], layer="hidden")
    p1.hidden_taken = True
    p1.skip_next_turn = True
    room = room_with([p0, p1], trump="D", stack=[], current_idx=0)
    room, events = play_card(room, "p0", C("9D"))
    assert room.table_stack[-1].code == "9D"
    # The turn must NOT rest on p0 (who owns the top card).
    assert room.current_player.id == "p1"


def test_waiting_trigger_may_play_a_card_it_holds():
    # A waiting-for-share player who holds a (reopened) main card may play it,
    # rather than being blocked until their share is distributed.
    # 3 players so a 2-card stack doesn't trigger bito and clear the table.
    players = [
        make_player("p0", [C("KD")]),  # waiting but holding a card
        make_player("p1", [C("6C")]),
        make_player("p2", [C("6H")]),
    ]
    room = room_with(players, trump="D", stack=[C("7H")], current_idx=0)
    room.players[0].waiting_for_share = True
    room.players[0].pending_share = [C("9C")]
    room.buffer_distributed = True
    # KD is a trump (D) and beats 7H; the play must be accepted, not rejected.
    room, events = play_card(room, "p0", C("KD"))
    assert "error" not in event_types(events)
    assert room.table_stack[-1].code == "KD"
    assert all(c.code != "KD" for c in room.players[0].main_hand)


# ===========================================================================
# Regression: both players empty main hands - non-trigger gets share immediately
# ===========================================================================

def test_2p_both_empty_main_non_trigger_gets_share_immediately():
    """Regression: when A empties their last main card (triggering buffer
    distribution), B's main hand is already empty.  B must immediately
    receive their pending share and move to the buffer layer so they can
    still play.  Previously check_layer_transition was never called for B,
    leaving both players unable to act."""
    buffer_cards = [C("9D"), C("JC"), C("6H"), C("7C")]
    players = [
        make_player("p0", [C("9H")]),  # will trigger distribution
        make_player("p1", []),          # already empty - the problematic case
    ]
    room = room_with(players, trump="D", stack=[], current_idx=0)
    room.buffer_pile = buffer_cards
    rng = random.Random(42)
    room.rng = rng

    # p0 plays their last main card; stack had 0 cards, so no bito yet.
    room, events = play_card(room, "p0", C("9H"))

    # Buffer distribution must have fired.
    assert room.buffer_distributed is True
    # p0 is deferred (waiting for share).
    assert room.players[0].waiting_for_share is True
    # p1 must NOT be stuck on the main layer with an empty hand.
    p1 = room.players[1]
    assert p1.layer == "buffer", f"p1.layer={p1.layer!r}; p1 should have moved to buffer"
    assert len(p1.buffer_share) > 0, "p1 should have received their buffer share"
    # A buffer_share event must have been emitted for p1.
    share_events = [e for e in events if e["type"] == "buffer_share" and e["payload"]["_to"] == "p1"]
    assert len(share_events) == 1


# ===========================================================================
# Layer transitions: buffer->hidden skip, 4-5p direct main->hidden
# ===========================================================================

def test_buffer_to_hidden_sets_skip_next_turn():
    # p on buffer layer empties it -> takes hidden, skip next turn.
    players = [
        make_player("p0", [], hidden=[C("9C"), C("6S")], layer="buffer"),
        make_player("p1", [C("JH")]),
    ]
    room = room_with(players, trump="D", stack=[C("7H")], current_idx=0)
    # p0 plays their last buffer card... but they have none. Set up so that
    # buffer empties via a play: give p0 a buffer card instead.
    players = [
        make_player("p0", [], hidden=[C("9C"), C("6S")], layer="buffer"),
        make_player("p1", [C("JH")]),
    ]
    players[0].buffer_share = [C("9H")]
    room = room_with(players, trump="D", stack=[C("7H")], current_idx=0)
    room, events = play_card(room, "p0", C("9H"))
    assert room.players[0].layer == "hidden"
    assert room.players[0].skip_next_turn is True
    assert "hidden_revealed" in event_types(events)


def test_4_player_no_buffer_no_trump_change_on_empty_main():
    players = [
        make_player("p0", [C("9H")]),
        make_player("p1", [C("JH")]),
        make_player("p2", [C("QH")]),
        make_player("p3", [C("KH")]),
    ]
    room = room_with(players, trump="D", stack=[C("7H")], current_idx=0)
    # p0 has only 9H; playing it empties main. 4p -> direct to hidden.
    room.players[0].hidden_cards = [C("6C"), C("7S")]
    room, events = play_card(room, "p0", C("9H"))
    # No buffer triggered event in 4p.
    assert "buffer_triggered" not in event_types(events)
    assert room.players[0].layer == "hidden"
    assert room.players[0].skip_next_turn is True


# ===========================================================================
# Elimination & game over
# ===========================================================================

def test_elimination_emits_player_out():
    # p0 on hidden with one card; playing it eliminates them.
    players = [
        make_player("p0", [], hidden=[C("9H")], layer="hidden"),
        make_player("p1", [C("JH")]),
    ]
    room = room_with(players, trump="D", stack=[C("7H")], current_idx=0)
    room, events = play_card(room, "p0", C("9H"))
    assert room.players[0].eliminated is True
    assert "player_out" in event_types(events)


def test_game_over_when_one_remains():
    players = [
        make_player("p0", [], hidden=[C("9H")], layer="hidden"),
        make_player("p1", [C("JH")]),
    ]
    room = room_with(players, trump="D", stack=[C("7H")], current_idx=0)
    room, events = play_card(room, "p0", C("9H"))
    # p0 eliminated -> only p1 remains -> game over, p1 is loser.
    assert "game_over" in event_types(events)
    assert room.loser_id == "p1"
