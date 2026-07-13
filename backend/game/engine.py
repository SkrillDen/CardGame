"""Pure game-logic engine for the Durak-variant card game.

Every public function takes a ``GameRoom`` (plus action arguments) and returns
``(GameRoom, list[Event])``. No I/O, no FastAPI, no WebSocket — the same
functions are exercised by the unit tests and by the server's dispatch loop.

Events are plain dicts: ``{"type": <str>, "payload": {...}}``.
Private events (destined for a single player) carry ``payload["_to"] =
<player_id>``; the server routes those privately, everything else is broadcast.

Turn-flow summary (see plan for the full state machine):

  * ``play_card``  -> beat the top card (or open a fresh stack); then resolve
                      layer transitions, then ``check_bito``; if no bito,
                      ``advance_turn``.
  * ``take_bottom``-> give up: take stack[0] into the main hand; advance turn.
  * ``contribute_buffer`` -> add a card to the shared buffer pile during the
                      post-bito contribution phase.

Last-main-card / trump lifecycle (2-3p only):
  playing the card that empties the main hand picks a new trump weighted by
  the buffer pile's suit counts, splits the buffer into reserved shares, and
  DEFERS the triggering player's share until the current stack clears. If the
  turn cycles back to them first, they are forced into ``take_bottom`` (the
  taken card reopens the main hand). On bito they take the share with no skip.
"""

from __future__ import annotations

import random
from typing import List, Optional, Tuple

from .deck import (
    choose_initial_trump,
    choose_weighted_trump,
    deal_hands,
)
from .models import Card, GameRoom, Player, make_event

# Event is just a typed alias for clarity.
Event = dict


# ===========================================================================
# (a) Beating rules
# ===========================================================================

def validate_beat(card_to_beat: Card, card_played: Card, trump: str) -> bool:
    """Return True iff ``card_played`` legally beats ``card_to_beat``.

    Spades are a closed domain — a spade can only ever be beaten by a higher
    spade, and a spade can only ever beat a lower spade. This holds in every
    trump context (including trump == Spades, where all spades are trump and
    only a higher trump-spade beats a lower one).
    """
    a, b = card_to_beat, card_played

    # Spade being beaten: only a higher spade works (trump is irrelevant).
    if a.suit == "S":
        return b.suit == "S" and b.rank > a.rank
    # Spade doing the beating against a non-spade: never allowed.
    if b.suit == "S":
        return False
    # Both non-spade, same suit: higher rank wins.
    if a.suit == b.suit:
        return b.rank > a.rank
    # ``a`` is a non-spade trump: a non-trump ``b`` cannot beat it.
    if a.suit == trump:
        return False
    # ``b`` is a non-spade trump: it beats the non-trump ``a``.
    if b.suit == trump:
        return True
    # Different non-trump, non-spade suits: no beat.
    return False


def can_beat_any(hand: List[Card], top: Optional[Card], trump: str) -> bool:
    """True if any card in ``hand`` can beat ``top`` (None => fresh stack)."""
    if top is None:
        return len(hand) > 0
    return any(validate_beat(top, c, trump) for c in hand)


# ===========================================================================
# (b) Initial deal
# ===========================================================================

def deal_cards(
    num_players: int,
    rng: Optional[random.Random] = None,
    room_id: str = "room",
    player_names: Optional[List[str]] = None,
) -> Tuple[GameRoom, List[Event]]:
    """Create a freshly dealt ``GameRoom`` and the opening events.

    The opening table card is the last card dealt; per the resolved rules it
    counts as the first player's (index 0) automatic first move, so the player
    who must act next is index 1 (beating the opener).
    """
    if rng is None:
        rng = random.Random()
    if not (2 <= num_players <= 5):
        raise ValueError(f"num_players must be 2..5, got {num_players}")
    if player_names is None:
        player_names = [f"Player{i+1}" for i in range(num_players)]

    hidden, main, opening_card = deal_hands(num_players, rng)
    trump = choose_initial_trump(rng)

    players = [
        Player(
            id=f"p{i}",
            name=player_names[i],
            main_hand=main[i],
            hidden_cards=hidden[i],
        )
        for i in range(num_players)
    ]

    # Dealer sits at the last seat; first player (index 0) auto-plays the
    # opener, so index 1 is first to act.
    dealer_idx = num_players - 1
    current_idx = 1 % num_players

    room = GameRoom(
        room_id=room_id,
        players=players,
        dealer_idx=dealer_idx,
        current_idx=current_idx,
        trump=trump,
        table_stack=[opening_card],
        started=True,
        rng=rng,
    )

    events: List[Event] = [
        make_event("game_started", trump=trump, opening_card=str(opening_card)),
        make_event("card_played", player_id=players[0].id, card=str(opening_card), automatic=True),
    ]
    events.extend(_public_state(room))
    # Each player privately learns their own main hand.
    for p in players:
        events.append(make_event("hand_update", _to=p.id, cards=[str(c) for c in p.main_hand]))
    return room, events


# ===========================================================================
# Internal helpers
# ===========================================================================

def _public_state(room: GameRoom) -> List[Event]:
    """Build a broadcastable snapshot of the public game state."""
    return [
        make_event(
            "game_state",
            trump=room.trump,
            table_stack=[str(c) for c in room.table_stack],
            table_stack_size=len(room.table_stack),
            current_player_id=room.current_player.id,
            active_players=[
                {
                    "id": p.id,
                    "name": p.name,
                    "card_count": p.total_cards,
                    "layer": p.layer,
                    "eliminated": p.eliminated,
                    "waiting_for_share": p.waiting_for_share,
                }
                for p in room.players
            ],
            bito_count=room.bito_count,
            buffer_size=len(room.buffer_pile),
            buffer_distributed=room.buffer_distributed,
            contribution_phase=room.contribution_phase,
            contribution_due=list(room.contribution_due),
        )
    ]


def _err(code: str, message: str) -> List[Event]:
    return [make_event("error", code=code, message=message)]


def _set_layer(room: GameRoom, player: Player, layer: str, events: List[Event]) -> None:
    if player.layer != layer:
        player.layer = layer
        events.append(make_event("layer_changed", player_id=player.id, layer=layer))


def _num_main_players(room: GameRoom) -> int:
    return room.num_players


# ===========================================================================
# (f) Layer transition resolution
# ===========================================================================

def check_layer_transition(room: GameRoom, player_id: str) -> Tuple[GameRoom, List[Event]]:
    """Advance ``player`` through layers based on what's now empty.

    This is the single place that decides main->buffer->hidden->out movement.

    * main empty:
        - 2-3p with buffer distributed AND player is NOT the deferred trigger:
          take pending_share, layer -> buffer.
        - otherwise: stay (waiting for distribution / waiting for stack clear).
    * buffer empty: take hidden cards (if not yet taken), layer -> hidden.
    * hidden empty: eliminate the player.
    """
    events: List[Event] = []
    player = room.get_player(player_id)
    if player is None or player.eliminated:
        return room, events

    # --- main -> next layer ---
    #   * 4-5p: no buffer mechanic, go straight to hidden.
    #   * 2-3p: go to buffer if a share is available now; otherwise stay
    #     (waiting for distribution or for the current stack to clear).
    if player.layer == "main" and not player.main_hand:
        if not room.is_two_three_player:
            _take_hidden(room, player, events)
        elif room.buffer_distributed and not player.waiting_for_share:
            share = player.pending_share
            player.pending_share = []
            player.buffer_share = list(share)
            _set_layer(room, player, "buffer", events)
            if share:
                events.append(
                    make_event(
                        "buffer_share",
                        _to=player.id,
                        cards=[str(c) for c in share],
                    )
                )
        # else: stay on main, waiting.

    # --- buffer -> hidden ---
    if player.layer == "buffer" and not player.buffer_share:
        _take_hidden(room, player, events)

    # --- hidden -> eliminated ---
    if player.layer == "hidden" and not player.hidden_cards and not player.eliminated:
        player.eliminated = True
        events.append(make_event("player_out", player_id=player.id))
        if room.num_active <= 1:
            _end_game(room, events)

    return room, events


def _take_hidden(room: GameRoom, player: Player, events: List[Event]) -> None:
    """Move a player from main/buffer into the hidden-card layer.

    Reveals the 2 dealt hidden cards (private event) if not yet done.
    """
    if not player.hidden_taken:
        player.hidden_taken = True
        player.hidden_cards = list(player.hidden_cards)
        events.append(
            make_event(
                "hidden_revealed",
                _to=player.id,
                cards=[str(c) for c in player.hidden_cards],
            )
        )
    _set_layer(room, player, "hidden", events)


def _end_game(room: GameRoom, events: List[Event]) -> None:
    """Set the loser (last player holding cards) and emit game_over."""
    remaining = room.active_players
    if len(remaining) <= 1:
        loser = remaining[0] if remaining else None
        room.loser_id = loser.id if loser else None
        events.append(make_event("game_over", loser_id=room.loser_id))


# ===========================================================================
# (h) Buffer distribution (2-3p only)
# ===========================================================================

def trigger_buffer_distribution(room: GameRoom, trigger_pid: str) -> Tuple[GameRoom, List[Event]]:
    """Distribute the shared buffer pile: pick a new trump, split into shares.

    The triggering player's share is deferred (``waiting_for_share = True``);
    they take it when the current stack clears. Other players take their share
    when their own main hand empties (handled in ``check_layer_transition``).
    """
    events: List[Event] = []
    if room.buffer_distributed:
        return room, events
    if not room.is_two_three_player:
        return room, events

    new_trump = choose_weighted_trump(room.buffer_pile, room.rng)
    room.trump = new_trump

    # Shuffle the pile and split evenly; remainder goes to earliest seats.
    pile = list(room.buffer_pile)
    room.rng.shuffle(pile)
    n = room.num_players
    base = len(pile) // n
    rem = len(pile) % n

    active = list(room.players)  # all seats; eliminated players keep none
    shares: dict = {}
    idx = 0
    for i, p in enumerate(active):
        size = base + (1 if i < rem else 0)
        share = pile[idx : idx + size]
        idx += size
        p.pending_share = share
        shares[p.id] = len(share)
        if p.id == trigger_pid:
            p.waiting_for_share = True

    room.buffer_pile = []
    room.buffer_distributed = True

    events.append(
        make_event(
            "buffer_triggered",
            new_trump=new_trump,
            trigger_id=trigger_pid,
            shares=shares,
        )
    )
    return room, events


# ===========================================================================
# (g) Contribution phase
# ===========================================================================

def contribute_buffer(
    room: GameRoom, player_id: str, card: Card
) -> Tuple[GameRoom, List[Event]]:
    """Contribute one main-hand card to the shared buffer pile."""
    events: List[Event] = []

    if not room.contribution_phase:
        return room, _err("not_contribution_phase", "No contribution requested right now")
    player = room.get_player(player_id)
    if player is None:
        return room, _err("unknown_player", "Unknown player")
    if player_id not in room.contribution_due:
        return room, _err("not_due", "You have already contributed or are not eligible")
    # Match by code so callers may pass Card.from_str(...) or equivalent.
    target = next((c for c in player.main_hand if c.code == card.code), None)
    if target is None:
        return room, _err("card_not_in_main", "You must contribute from your main hand")

    player.main_hand.remove(target)
    room.buffer_pile.append(target)
    room.contribution_due.discard(player_id)
    events.append(
        make_event("buffer_contributed", player_id=player_id, buffer_size=len(room.buffer_pile))
    )
    events.append(
        make_event("hand_update", _to=player_id, cards=[str(c) for c in player.main_hand])
    )

    # Contributing the last main card empties the hand — the same "ran out of
    # main cards" condition that a final play would create. Trigger the buffer
    # distribution now (deferring this player's share) so they are not left
    # stranded on an empty main layer with no way to draw into the buffer.
    if (
        room.is_two_three_player
        and not room.buffer_distributed
        and not player.main_hand
    ):
        room.contribution_phase = False
        room.contribution_due = set()
        _, ev = trigger_buffer_distribution(room, player_id)
        events.extend(ev)
        # Other players whose main is already empty pick up their share now.
        for p in room.players:
            if p.id != player_id:
                _, ev = check_layer_transition(room, p.id)
                events.extend(ev)
        # The current player (the bito closer, due to open the next stack) may
        # now be unable to act — e.g. they are the deferred trigger with an
        # empty main. Pass the turn on so play can continue.
        cur = room.current_player
        if cur.eliminated or cur.waiting_for_share or not cur.active_cards:
            _advance_turn(room, events)
    elif not room.contribution_due:
        room.contribution_phase = False
        # The contribution phase is over; the bito closer is due to open the
        # next stack. If they can no longer act (e.g. they eliminated
        # themselves on the closing play), pass the turn on.
        cur = room.current_player
        if cur.eliminated or cur.waiting_for_share or not cur.active_cards:
            _advance_turn(room, events)
    events.extend(_public_state(room))
    return room, events


# ===========================================================================
# (e) Bito (stack full -> discard)
# ===========================================================================

def check_bito(room: GameRoom) -> Tuple[GameRoom, List[Event]]:
    """If the stack has reached the active-player count, discard it to bito.

    Effects:
      * move all stack cards to ``bito``, increment ``bito_count``.
      * clear deferred buffer waits: waiting players take their pending share
        into the buffer layer with NO turn skip.
      * the closer (who placed the last card) opens the next stack, i.e. stays
        the current player.
      * start a contribution phase for 2-3p (3p every bito, 2p every 2nd),
        but only while the buffer is still undistributed.
    """
    events: List[Event] = []
    if not room.table_stack:
        return room, events
    if len(room.table_stack) < room.num_active:
        return room, events

    closer_id = room.current_player.id
    room.bito.extend(room.table_stack)
    room.table_stack = []
    room.bito_count += 1
    events.append(make_event("bito", bito_count=room.bito_count, closer_id=closer_id))

    # Clear deferred waits: waiting players take their share now (no skip).
    for p in room.players:
        if p.waiting_for_share:
            _resolve_share(room, p, events)

    # Closer opens the next stack (current player unchanged).
    # Contribution phase (2-3p, undistributed only).
    if room.is_two_three_player and not room.buffer_distributed:
        need_contribution = room.num_players == 3 or room.bito_count % 2 == 0
        if need_contribution:
            room.contribution_phase = True
            room.contribution_due = {p.id for p in room.active_players}
            events.append(
                make_event("buffer_request", due=list(room.contribution_due))
            )

    events.extend(_public_state(room))
    return room, events


# ===========================================================================
# (i) Turn advancement
# ===========================================================================

def _resolve_share(room: GameRoom, player: Player, events: List[Event]) -> None:
    """Give a deferred player their pending buffer share now (no turn penalty).

    Used both on bito (all waiting players collect their share) and when the
    turn genuinely lands on a waiting player who must OPEN a fresh stack but has
    no main cards to do it with — otherwise the game would stall on a player
    with nothing to play and no stack to take from.
    """
    player.waiting_for_share = False
    share = player.pending_share
    player.pending_share = []
    # A deferred trigger may have been forced to take bottom cards back into
    # their (reopened) main hand while waiting. Carry those over so they are
    # not stranded when the player moves onto the buffer layer.
    leftover_main = list(player.main_hand)
    player.main_hand = []
    player.buffer_share = leftover_main + list(share)
    _set_layer(room, player, "buffer", events)
    if player.buffer_share:
        events.append(
            make_event(
                "buffer_share",
                _to=player.id,
                cards=[str(c) for c in player.buffer_share],
                deferred=True,
            )
        )


def _advance_turn(room: GameRoom, events: List[Event]) -> None:
    """Move to the next eligible player, applying skips and forced takes.

    * skip eliminated players;
    * honour ``skip_next_turn`` (clear it, emit turn_skipped, keep going);
    * a waiting-for-share player with a non-empty stack is forced to take the
      bottom card (failed beat) into their main hand, then we move on;
    * a waiting-for-share player who must OPEN an empty stack instead collects
      their deferred share immediately (they have no main card to open with);
    * a player whose current active layer is empty is transitioned down
      (main->buffer->hidden->out) so the turn never stops on someone who has
      no card to play and no stack to take from.
    """
    n = room.num_players
    # Allow several transitions/skips per lap; the bound guards against hangs.
    for _ in range(n * 4 + 2):
        room.current_idx = (room.current_idx + 1) % n
        p = room.current_player
        if p.eliminated:
            continue
        if p.skip_next_turn:
            p.skip_next_turn = False
            events.append(make_event("turn_skipped", player_id=p.id))
            continue
        if p.waiting_for_share:
            if room.table_stack:
                # Forced failed beat: take the bottom card into the main hand
                # (penalty) and lose this turn.
                bottom = room.table_stack.pop(0)
                p.main_hand.append(bottom)
                events.append(
                    make_event(
                        "card_taken",
                        player_id=p.id,
                        card=str(bottom),
                        reason="forced",
                    )
                )
                events.append(make_event("hand_update", _to=p.id, cards=[str(c) for c in p.main_hand]))
                continue
            # Empty stack: they'd have to open but hold no main cards. Give them
            # their deferred share now so they can act.
            _resolve_share(room, p, events)

        # Ensure the player actually has something to play; if their active
        # layer is empty, move them down a layer (may reveal hidden / eliminate).
        if not p.active_cards and not p.eliminated:
            _, ev = check_layer_transition(room, p.id)
            events.extend(ev)
        if p.eliminated:
            continue

        # The player can act if they have a card to play or a stack to take.
        if p.active_cards or room.table_stack:
            break
        # Otherwise keep scanning (the transitions above should prevent this
        # from persisting; the loop bound is the final safety net).


# ===========================================================================
# (c) Play a card
# ===========================================================================

def play_card(
    room: GameRoom, player_id: str, card: Card
) -> Tuple[GameRoom, List[Event]]:
    """Play ``card`` to beat the current top (or open a fresh stack)."""
    events: List[Event] = []

    if not room.started:
        return room, _err("not_started", "Game has not started")
    if room.contribution_phase:
        return room, _err("contribution_phase", "Contribute a buffer card first")
    if room.loser_id is not None:
        return room, _err("game_over", "Game is over")

    player = room.get_player(player_id)
    if player is None:
        return room, _err("unknown_player", "Unknown player")
    if room.current_player.id != player_id:
        return room, _err("not_your_turn", "It is not your turn")
    if player.waiting_for_share:
        return room, _err("waiting_for_share", "You are waiting for your buffer share")

    target = next((c for c in player.active_cards if c.code == card.code), None)
    if target is None:
        return room, _err("card_not_in_hand", "You do not have that card in your active layer")

    # Beating check (no check needed when opening a fresh stack).
    if room.table_stack:
        top = room.table_stack[-1]
        if not validate_beat(top, target, room.trump):
            return room, _err("illegal_beat", f"{target.code} cannot beat {top.code}")

    # Apply the play.
    player.active_cards.remove(target)
    room.table_stack.append(target)
    events.append(make_event("card_played", player_id=player_id, card=str(target)))

    # ---- Post-play resolution for the acting player ----
    was_main = player.layer == "main"
    was_buffer = player.layer == "buffer"
    emptied_main = was_main and not player.main_hand
    emptied_buffer = was_buffer and not player.buffer_share

    if emptied_main:
        if room.is_two_three_player:
            # Trump change + buffer distribution; trigger defers their share.
            if not room.buffer_distributed:
                _, ev = trigger_buffer_distribution(room, player_id)
                events.extend(ev)
            # Player remains on main layer, waiting for share (or already
            # distributed -> they will pick up on the next transition check).
            # Also check transitions for other players whose main may already
            # be empty — they should receive their buffer share immediately.
            for p in room.players:
                if p.id != player_id:
                    _, ev = check_layer_transition(room, p.id)
                    events.extend(ev)
        # 4-5p falls through: check_layer_transition moves them to hidden.

    # Run layer transitions (handles main->hidden for 4-5p, buffer->hidden,
    # hidden->eliminated). If the player advanced onto hidden because of THIS
    # play (their own turn), they skip their next turn.
    advanced_to_hidden = emptied_main or emptied_buffer
    _, ev = check_layer_transition(room, player_id)
    events.extend(ev)
    if advanced_to_hidden and player.layer == "hidden":
        player.skip_next_turn = True

    # ---- Bito check ----
    _, ev = check_bito(room)
    events.extend(ev)

    # ---- Advance turn (unless contribution phase now active or game over) ----
    if not room.contribution_phase and room.loser_id is None:
        # Normally: if bito cleared the stack, the closer stays current to open
        # the next stack. But if the closer just eliminated themselves (played
        # their last card) or otherwise has nothing to open with, pass the turn
        # on to the next player who can act.
        closer = room.current_player
        if room.table_stack:
            _advance_turn(room, events)
        elif closer.eliminated or not closer.active_cards:
            _advance_turn(room, events)
        events.extend(_public_state(room))

    return room, events


# ===========================================================================
# (d) Take the bottom card (give up)
# ===========================================================================

def take_bottom(room: GameRoom, player_id: str) -> Tuple[GameRoom, List[Event]]:
    """Give up beating: take the bottom card of the stack into the main hand."""
    events: List[Event] = []

    if not room.started:
        return room, _err("not_started", "Game has not started")
    if room.contribution_phase:
        return room, _err("contribution_phase", "Contribute a buffer card first")
    if room.loser_id is not None:
        return room, _err("game_over", "Game is over")

    player = room.get_player(player_id)
    if player is None:
        return room, _err("unknown_player", "Unknown player")
    if room.current_player.id != player_id:
        return room, _err("not_your_turn", "It is not your turn")
    if not room.table_stack:
        return room, _err("empty_stack", "There is no stack to take from")

    bottom = room.table_stack.pop(0)
    if player.layer == "main":
        player.main_hand.append(bottom)
    elif player.layer == "buffer":
        player.buffer_share.append(bottom)
    else:
        player.hidden_cards.append(bottom)
    events.append(make_event("card_taken", player_id=player_id, card=str(bottom), reason="take"))
    events.append(
        make_event("hand_update", _to=player_id, cards=[str(c) for c in player.active_cards])
    )

    # Taking a card can never grow the stack, so no bito is possible here.
    if not room.contribution_phase and room.loser_id is None:
        _advance_turn(room, events)
        events.extend(_public_state(room))

    return room, events


# ===========================================================================
# (lobby) Room creation / join / start
# ===========================================================================

def create_room(name: str, room_id: str = "room") -> Tuple[GameRoom, List[Event]]:
    """Create an empty (un-started) room with one player seated."""
    room = GameRoom(room_id=room_id, players=[], started=False)
    room.players.append(Player(id="p0", name=name, main_hand=[], hidden_cards=[]))
    events = [make_event("room_update", room_id=room_id, players=[{"id": "p0", "name": name}])]
    return room, events


def join_room(room: GameRoom, name: str) -> Tuple[GameRoom, List[Event]]:
    """Seat a new player in an existing un-started room."""
    if room.started:
        return room, _err("already_started", "Game already started")
    if len(room.players) >= 5:
        return room, _err("room_full", "Room is full")
    pid = f"p{len(room.players)}"
    room.players.append(Player(id=pid, name=name, main_hand=[], hidden_cards=[]))
    events = [
        make_event(
            "room_update",
            room_id=room.room_id,
            players=[{"id": p.id, "name": p.name} for p in room.players],
        )
    ]
    return room, events


def start_game(
    room: GameRoom, rng: Optional[random.Random] = None
) -> Tuple[GameRoom, List[Event]]:
    """Deal cards and begin play for an already-populated room."""
    if room.started:
        return room, _err("already_started", "Game already started")
    if not (2 <= len(room.players) <= 5):
        return room, _err("bad_player_count", "Need 2-5 players to start")

    if rng is None:
        rng = room.rng
    names = [p.name for p in room.players]
    # Reuse the existing player ids/names but reset their state via deal_cards.
    new_room, events = deal_cards(
        num_players=len(room.players),
        rng=rng,
        room_id=room.room_id,
        player_names=names,
    )
    # Preserve original ids (deal_cards created p0..p{N-1} which matches).
    return new_room, events
