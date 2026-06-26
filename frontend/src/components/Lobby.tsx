// Lobby: name + room-id entry, create/join, roster, host-only Start button.

import { useState } from "react";
import { useGameStore } from "../store/gameStore";
import { useT } from "../i18n";
import type { useWebSocket } from "../hooks/useWebSocket";

interface Props {
  ws: ReturnType<typeof useWebSocket>;
}

export function Lobby({ ws }: Props) {
  const t = useT();
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
        <h2>{t.lobbyHeading}</h2>
        <div className="field">
          <label htmlFor="name">{t.labelName}</label>
          <input
            id="name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder={t.placeholderName}
            disabled={seated}
          />
        </div>
        <div className="field">
          <label htmlFor="room">{t.labelRoom}</label>
          <input
            id="room"
            value={roomId}
            onChange={(e) => setRoomId(e.target.value)}
            placeholder={t.placeholderRoom}
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
              {roomId.trim() ? t.btnJoin : t.btnCreateJoin}
            </button>
          </div>
        ) : (
          <>
            <div className="roster">
              <h3>{t.rosterHeading(players.length)}</h3>
              <ul>
                {players.map((p, i) => (
                  <li key={p.id}>
                    <span className="tag host" hidden={i !== 0}>
                      {t.tagHost}
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
                  title={players.length < 2 ? t.startDisabledHint : undefined}
                >
                  {t.btnStart}
                </button>
              ) : (
                <span className="hint">{t.waitingForHost}</span>
              )}
            </div>
          </>
        )}
        {!connected && seated && (
          <p className="hint" style={{ marginTop: 12 }}>
            {t.connecting}
          </p>
        )}
      </div>
    </div>
  );
}

function generateRoomId(): string {
  return Math.random().toString(36).slice(2, 8).toUpperCase();
}
