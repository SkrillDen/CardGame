// Lobby: name + room-id entry, create/join, roster, host-only Start button.

import { useState } from "react";
import { useGameStore } from "../store/gameStore";
import type { useWebSocket } from "../hooks/useWebSocket";

interface Props {
  ws: ReturnType<typeof useWebSocket>;
}

export function Lobby({ ws }: Props) {
  const [name, setName] = useState("");
  const [roomId, setRoomId] = useState("");
  const players = useGameStore((s) => s.players);
  const isHost = useGameStore((s) => s.isHost);
  const phase = useGameStore((s) => s.phase);
  const connected = useGameStore((s) => s.connected);

  const seated = phase !== "lobby" || players.length > 0;

  const handleCreate = () => {
    if (!name.trim()) return;
    const rid = roomId.trim() || generateRoomId();
    ws.connect(rid, name.trim());
  };

  const handleStart = () => {
    useGameStore.getState().send({ type: "start_game", payload: {} });
  };

  return (
    <div className="lobby">
      <div className="lobby-card">
        <h2>Durak — Join a game</h2>
        <div className="field">
          <label htmlFor="name">Your name</label>
          <input
            id="name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g. Alice"
            disabled={seated}
          />
        </div>
        <div className="field">
          <label htmlFor="room">Room code (leave blank to create)</label>
          <input
            id="room"
            value={roomId}
            onChange={(e) => setRoomId(e.target.value)}
            placeholder="e.g. ABC123"
            disabled={seated}
          />
        </div>

        {!seated ? (
          <div className="actions">
            <button
              className="primary"
              onClick={handleCreate}
              disabled={!name.trim()}
            >
              {roomId.trim() ? "Join" : "Create & Join"}
            </button>
          </div>
        ) : (
          <>
            <div className="roster">
              <h3>Players ({players.length})</h3>
              <ul>
                {players.map((p, i) => (
                  <li key={p.id}>
                    <span className="tag host" hidden={i !== 0}>
                      Host
                    </span>
                    {p.name}
                  </li>
                ))}
              </ul>
            </div>
            <div className="actions" style={{ marginTop: 16 }}>
              {isHost ? (
                <button
                  className="primary"
                  onClick={handleStart}
                  disabled={players.length < 2}
                  title={players.length < 2 ? "Need at least 2 players" : undefined}
                >
                  Start game
                </button>
              ) : (
                <span className="hint">Waiting for host to start…</span>
              )}
            </div>
          </>
        )}
        {!connected && seated && (
          <p className="hint" style={{ marginTop: 12 }}>
            Connecting…
          </p>
        )}
      </div>
    </div>
  );
}

function generateRoomId(): string {
  return Math.random().toString(36).slice(2, 8).toUpperCase();
}
