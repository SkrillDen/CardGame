// Root component. Phase from the store decides Lobby vs. game board.

import { useState } from "react";
import { useWebSocket } from "./hooks/useWebSocket";
import { useGameStore } from "./store/gameStore";
import { useT, useLocaleStore } from "./i18n";
import { Lobby } from "./components/Lobby";
import { Table } from "./components/Table";
import { PlayerList } from "./components/PlayerList";
import { Hand } from "./components/Hand";
import { GameOver } from "./components/GameOver";
import { RulesModal } from "./components/RulesModal";
import { Toasts } from "./components/Toast";

export default function App() {
  const t = useT();
  const locale = useLocaleStore((s) => s.locale);
  const setLocale = useLocaleStore((s) => s.setLocale);
  const ws = useWebSocket();
  const phase = useGameStore((s) => s.phase);
  const connected = useGameStore((s) => s.connected);
  const connectionLost = useGameStore((s) => s.connectionLost);
  const roomId = useGameStore((s) => s.roomId);
  const resetForLobby = useGameStore((s) => s.resetForLobby);
  const [rulesOpen, setRulesOpen] = useState(false);

  function handleBackToLobby() {
    ws.disconnect();
    resetForLobby();
  }

  return (
    <div className="app">
      <header className="app-header">
        <h1>{t.appTitle}</h1>
        <div className="header-tools">
          <button
            type="button"
            className="locale-button"
            onClick={() => setLocale(locale === "en" ? "ru" : "en")}
            title={locale === "en" ? "Переключить на русский" : "Switch to English"}
          >
            {locale === "en" ? "RU" : "EN"}
          </button>
          <button
            type="button"
            className="info-button"
            aria-label={t.openRules}
            title={t.gameRulesTitle}
            onClick={() => setRulesOpen(true)}
          >
            i
          </button>
          <div className={`conn ${connected ? "" : "off"}`}>
            <span className="dot" />
            {connected ? t.connected : t.disconnected}
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

      {connectionLost && phase !== "lobby" && (
        <div className="connection-lost-banner">
          <span>{t.connectionLost}</span>
          <button type="button" onClick={handleBackToLobby}>
            {t.backToMenu}
          </button>
        </div>
      )}

      <RulesModal open={rulesOpen} onClose={() => setRulesOpen(false)} />
      <Toasts />
    </div>
  );
}
