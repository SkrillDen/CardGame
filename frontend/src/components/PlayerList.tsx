// Roster of all players: avatar, name, host/current tags, card count, layer
// chip, eliminated styling. The local player's row also surfaces hidden-card
// state via PlayerBadge.

import { useGameStore } from "../store/gameStore";
import { PlayerBadge } from "./PlayerBadge";

export function PlayerList() {
  const players = useGameStore((s) => s.players);
  const currentId = useGameStore((s) => s.currentId);
  const myId = useGameStore((s) => s.myPlayerId);
  const myHidden = useGameStore((s) => s.myHidden);

  return (
    <div className="player-list">
      {players.map((p, i) => {
        const isCurrent = p.id === currentId;
        const isMe = p.id === myId;
        return (
          <div
            key={p.id}
            className={`player-row ${isCurrent ? "current" : ""} ${p.eliminated ? "eliminated" : ""}`}
          >
            <div className="avatar">{initials(p.name)}</div>
            <div className="meta">
              <span className="name">
                {p.name}
                {i === 0 && <span className="tag host">Host</span>}
                {isCurrent && !p.eliminated && <span className="tag current">Turn</span>}
              </span>
              <span className="sub">
                <span>{p.card_count} cards</span>
                <span className="chip" style={{ padding: "1px 6px" }}>
                  {p.layer}
                </span>
                {isMe && (
                  <PlayerBadge
                    hiddenCount={2 - myHidden.length}
                    revealedCards={p.layer === "hidden" ? myHidden : []}
                    isMe
                  />
                )}
              </span>
            </div>
          </div>
        );
      })}
    </div>
  );
}

function initials(name: string): string {
  return name.trim().slice(0, 2).toUpperCase() || "??";
}
