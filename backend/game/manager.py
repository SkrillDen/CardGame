"""Room registry, WebSocket connection pool, and broadcast logic.

The ``ConnectionManager`` is the only stateful, I/O-aware layer. It holds the
mapping of room_id -> GameRoom and room_id -> {player_id -> WebSocket}, and it
routes engine events to the right recipients:

  * events whose payload carries ``_to`` are sent only to that player;
  * every other event is broadcast to the whole room.

The engine itself stays pure; the manager is what glues it to the network.
"""

from __future__ import annotations

import json
import logging
from typing import Dict, List, Optional

from fastapi import WebSocket

from .engine import (
    contribute_buffer,
    create_room,
    join_room,
    play_card,
    start_game,
    take_bottom,
)
from .models import Card, GameRoom, Player, make_event

logger = logging.getLogger("durak.manager")


class ConnectionManager:
    """In-memory registry of rooms and their open WebSocket connections."""

    def __init__(self) -> None:
        # room_id -> GameRoom
        self.rooms: Dict[str, GameRoom] = {}
        # room_id -> {player_id -> WebSocket}
        self.connections: Dict[str, Dict[str, WebSocket]] = {}
        # websocket -> (room_id, player_id) for clean disconnect bookkeeping
        self.sock_index: Dict[WebSocket, tuple] = {}

    # ------------------------------------------------------------------
    # Room lifecycle
    # ------------------------------------------------------------------

    def create_room(self, room_id: str, name: str) -> tuple:
        """Create a new room and return ``(GameRoom, player_id)``."""
        if room_id in self.rooms:
            raise ValueError(f"Room {room_id!r} already exists")
        room, _ = create_room(name=name, room_id=room_id)
        self.rooms[room_id] = room
        self.connections[room_id] = {}
        return room, room.players[0].id

    def join_room(self, room_id: str, name: str) -> tuple:
        """Join an existing room. Returns ``(GameRoom, player_id)``."""
        room = self.rooms.get(room_id)
        if room is None:
            raise KeyError(f"Room {room_id!r} not found")
        player_id = f"p{len(room.players)}"
        room, _ = join_room(room, name=name)
        return room, player_id

    def get_room(self, room_id: str) -> Optional[GameRoom]:
        return self.rooms.get(room_id)

    def player_id_for_name(self, room_id: str, name: str) -> Optional[str]:
        room = self.rooms.get(room_id)
        if room is None:
            return None
        for p in room.players:
            if p.name == name:
                return p.id
        return None

    # ------------------------------------------------------------------
    # Connection bookkeeping
    # ------------------------------------------------------------------

    def connect(self, room_id: str, player_id: str, ws: WebSocket) -> None:
        """Register a WebSocket for ``(room_id, player_id)``."""
        self.connections.setdefault(room_id, {})[player_id] = ws
        self.sock_index[ws] = (room_id, player_id)

    def disconnect(self, ws: WebSocket) -> None:
        """Remove a WebSocket from its room (no-op if unknown)."""
        meta = self.sock_index.pop(ws, None)
        if meta is None:
            return
        room_id, player_id = meta
        conns = self.connections.get(room_id, {})
        # Only remove if it's still this socket (reconnects replace it).
        if conns.get(player_id) is ws:
            conns.pop(player_id, None)

    # ------------------------------------------------------------------
    # Broadcasting
    # ------------------------------------------------------------------

    async def send(self, ws: WebSocket, event: dict) -> None:
        await ws.send_text(json.dumps(event))

    async def send_to_player(self, room_id: str, player_id: str, event: dict) -> None:
        ws = self.connections.get(room_id, {}).get(player_id)
        if ws is not None:
            try:
                await self.send(ws, event)
            except Exception:
                logger.exception("Failed to send to player %s", player_id)

    async def broadcast(self, room_id: str, events: List[dict]) -> None:
        """Route a list of engine events to the right recipients.

        Events with ``payload["_to"]`` go privately to that player only;
        all others are broadcast to every connection in the room.
        """
        conns = self.connections.get(room_id, {})
        for event in events:
            to = event.get("payload", {}).pop("_to", None)
            if to is not None:
                await self.send_to_player(room_id, to, event)
            else:
                text = json.dumps(event)
                dead: List[str] = []
                for pid, ws in list(conns.items()):
                    try:
                        await ws.send_text(text)
                    except Exception:
                        logger.exception("Broadcast to %s failed; dropping", pid)
                        dead.append(pid)
                for pid in dead:
                    conns.pop(pid, None)

    # ------------------------------------------------------------------
    # Engine dispatch
    # ------------------------------------------------------------------

    def dispatch(self, room_id: str, player_id: str, msg: dict) -> List[dict]:
        """Apply one client message via the engine and return the events.

        Validates the message envelope, parses card codes into ``Card`` where
        needed, and forwards to the matching engine function. Errors from the
        engine (e.g. ``not_your_turn``) come back as ``error`` events.
        """
        room = self.rooms.get(room_id)
        if room is None:
            return [make_event("error", code="no_room", message="Room does not exist")]

        msg_type = msg.get("type")
        payload = msg.get("payload") or {}

        try:
            if msg_type == "start_game":
                room, events = start_game(room)
                self.rooms[room_id] = room
                return events
            if msg_type == "play_card":
                room, events = play_card(room, player_id, Card.from_str(payload["card"]))
                self.rooms[room_id] = room
                return events
            if msg_type == "take_bottom":
                room, events = take_bottom(room, player_id)
                self.rooms[room_id] = room
                return events
            if msg_type == "contribute_buffer":
                room, events = contribute_buffer(room, player_id, Card.from_str(payload["card"]))
                self.rooms[room_id] = room
                return events
            return [make_event("error", code="unknown_type", message=f"Unknown type {msg_type!r}")]
        except KeyError as e:
            return [make_event("error", code="missing_field", message=f"Missing field {e}")]
        except ValueError as e:
            return [make_event("error", code="bad_value", message=str(e))]
