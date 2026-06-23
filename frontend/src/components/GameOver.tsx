// Game-over modal. Names the loser (last player holding cards).

import { useGameStore } from "../store/gameStore";

export function GameOver() {
  const loserId = useGameStore((s) => s.loserId);
  const players = useGameStore((s) => s.players);
  if (!loserId) return null;
  const loser = players.find((p) => p.id === loserId);

  return (
    <div className="overlay">
      <div className="modal">
        <h2>Game over</h2>
        <p>The last player holding cards loses:</p>
        <div className="loser">{loser?.name ?? "—"}</div>
        <button className="primary" onClick={() => location.reload()}>
          Back to lobby
        </button>
      </div>
    </div>
  );
}
