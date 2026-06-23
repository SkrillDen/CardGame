// Root component. Phase from the store decides Lobby vs. game board.

import { useState } from "react";
import { useWebSocket } from "./hooks/useWebSocket";
import { useGameStore } from "./store/gameStore";
import { Lobby } from "./components/Lobby";
import { Table } from "./components/Table";
import { PlayerList } from "./components/PlayerList";
import { Hand } from "./components/Hand";
import { GameOver } from "./components/GameOver";
import { RulesModal } from "./components/RulesModal";
import { Toasts } from "./components/Toast";

export default function App() {
  const ws = useWebSocket();
  const phase = useGameStore((s) => s.phase);
  const connected = useGameStore((s) => s.connected);
  const roomId = useGameStore((s) => s.roomId);
  const [rulesOpen, setRulesOpen] = useState(false);

  return (
    <div className="app">
      <header className="app-header">
        <h1>♠ Durak</h1>
        <div className="header-tools">
          <button
            type="button"
            className="info-button"
            aria-label="Open game rules"
            title="Game rules"
            onClick={() => setRulesOpen(true)}
          >
            i
          </button>
          <div className={`conn ${connected ? "" : "off"}`}>
            <span className="dot" />
            {connected ? "Connected" : "Disconnected"}
            {roomId ? ` · ${roomId}` : ""}
          </div>
        </div>
      </header>

      {phase === "lobby" ? (
        <Lobby ws={ws} />
      ) : (
        <main className="board">
          <div className="board-top">
            <PlayerList />
            <Table />
          </div>
          <div className="board-center" />
          <Hand />
        </main>
      )}

      {phase === "over" && <GameOver />}
      <RulesModal open={rulesOpen} onClose={() => setRulesOpen(false)} />
      <Toasts />
    </div>
  );
}
