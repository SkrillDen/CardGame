// Game-over modal. Names the loser (last player holding cards).

import { useGameStore } from "../store/gameStore";
import { useT } from "../i18n";

export function GameOver() {
  const t = useT();
  const loserId = useGameStore((s) => s.loserId);
  const players = useGameStore((s) => s.players);
  if (!loserId) return null;
  const loser = players.find((p) => p.id === loserId);

  return (
    <div className="overlay">
      <div className="modal">
        <h2>{t.gameOverHeading}</h2>
        <p>{t.gameOverBody}</p>
        <div className="loser">{loser?.name ?? "—"}</div>
        <button className="primary" onClick={() => location.reload()}>
          {t.btnBackToLobby}
        </button>
      </div>
    </div>
  );
}
