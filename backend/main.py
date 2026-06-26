"""FastAPI app exposing the Durak-variant engine over WebSocket.

Run locally:
    uvicorn main:app --reload --port 8000

Connect a client to ``ws://localhost:8000/ws/{room_id}`` with a ``?name=...``
query string. The first client into a room creates it; subsequent clients join.

Protocol (JSON over the socket):
  client -> server: {"type": <type>, "payload": {...}}
      pre-game:  start_game {}
      in-game:   play_card { card }, take_bottom {}, contribute_buffer { card }
  server -> client: {"type": <type>, "payload": {...}}
      see game/engine.py for the full event vocabulary.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from game.engine import _public_state  # noqa: F401  (re-exported for convenience)
from game.manager import ConnectionManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("durak.main")

app = FastAPI(title="Durak-variant server")

# CORS for any future HTTP/preview surface; WebSockets are not constrained by
# CORS but the middleware is harmless and keeps options open.
cors_origins = os.environ.get("CORS_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

manager = ConnectionManager()


def _room_overview(room_id: str) -> Optional[dict]:
    """Compact pre-game room snapshot sent on join."""
    room = manager.get_room(room_id)
    if room is None:
        return None
    return {
        "type": "room_update",
        "payload": {
            "room_id": room_id,
            "started": room.started,
            "players": [{"id": p.id, "name": p.name} for p in room.players],
        },
    }


@app.websocket("/ws/{room_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    room_id: str,
    name: str = Query(...),
) -> None:
    """Main game socket: create-or-join on connect, then dispatch loop."""
    await websocket.accept()

    # --- Create or join the room on connect ---
    try:
        if manager.get_room(room_id) is None:
            _, player_id = manager.create_room(room_id, name)
            logger.info("Created room %s for %s", room_id, name)
        else:
            # Reconnect if the name is already seated; otherwise join.
            existing = manager.player_id_for_name(room_id, name)
            if existing is not None:
                player_id = existing
            else:
                _, player_id = manager.join_room(room_id, name)
                logger.info("%s joined room %s", name, room_id)
    except (ValueError, KeyError) as e:
        await websocket.send_text(
            json.dumps({"type": "error", "payload": {"code": "join_failed", "message": str(e)}})
        )
        await websocket.close()
        return

    manager.connect(room_id, player_id, websocket)

    # Send the current room/game state to the newly connected client.
    overview = _room_overview(room_id)
    if overview is not None:
        await websocket.send_text(json.dumps(overview))
    room = manager.get_room(room_id)
    if room is not None and room.started:
        from game.engine import _public_state as pub  # local to avoid import cycle

        for ev in pub(room):
            await websocket.send_text(json.dumps(ev))

    # --- Main dispatch loop ---
    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_text(
                    json.dumps(
                        {"type": "error", "payload": {"code": "bad_json", "message": "Invalid JSON"}}
                    )
                )
                continue

            events = manager.dispatch(room_id, player_id, msg)
            if events:
                await manager.broadcast(room_id, events)
    except WebSocketDisconnect:
        logger.info("%s disconnected from room %s", name, room_id)
    finally:
        manager.disconnect(websocket)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "rooms": len(manager.rooms)}


_STATIC_DIR = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if _STATIC_DIR.is_dir():
    app.mount("/", StaticFiles(directory=_STATIC_DIR, html=True), name="static")
else:
    logger.warning("Frontend dist not found at %s — static files will not be served", _STATIC_DIR)


if __name__ == "__main__":
    import uvicorn

    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run("main:app", host=host, port=port, reload=True)
