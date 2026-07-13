// Roster of all players: avatar, name, host/current tags, card count, layer
// chip, eliminated styling. The local player's row also surfaces hidden-card
// state via PlayerBadge.

import { useGameStore } from "../store/gameStore";
import { useT } from "../i18n";
import { PlayerBadge } from "./PlayerBadge";

export function PlayerList() {
  const t = useT();
  const players = useGameStore((s) => s.players);
  const currentId = useGameStore((s) => s.currentId);
  const myId = useGameStore((s) => s.myPlayerId);
  const myHidden = useGameStore((s) => s.myHidden);
  const contributionPhase = useGameStore((s) => s.contributionPhase);
  const contributionDue = useGameStore((s) => s.contributionDue);

  return (
    <div className="player-list">
      {players.map((p, i) => {
        const isCurrent = p.id === currentId;
        const isMe = p.id === myId;
        // During the buffer/contribution phases, make it clear whom everyone is
        // waiting on: players who still owe a contribution, or a deferred player
        // waiting for their buffer share.
        const isDue = contributionPhase && contributionDue.includes(p.id);
        const isWaitingShare = !!p.waiting_for_share;
        return (
          <div
            key={p.id}
            className={`player-row ${isCurrent ? "current" : ""} ${
              isDue || isWaitingShare ? "waiting" : ""
            } ${p.eliminated ? "eliminated" : ""}`}
          >
            <div className="avatar">{initials(p.name)}</div>
            <div className="meta">
              <span className="name">
                {p.name}
                {i === 0 && <span className="tag host">{t.tagHost}</span>}
                {isCurrent && !p.eliminated && !contributionPhase && (
                  <span className="tag current">{t.tagTurn}</span>
                )}
                {isDue && <span className="tag waiting">{t.tagContributing}</span>}
                {isWaitingShare && !isDue && (
                  <span className="tag waiting">{t.tagWaitingShare}</span>
                )}
              </span>
              <span className="sub">
                <span>{t.cardCount(p.card_count)}</span>
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
