// The player's own hand: renders the active-layer cards. Only cards that can
// legally beat the current top are clickable (a cosmetic hint — the server is
// still the source of truth). Disabled entirely when it isn't the player's
// turn or during the contribution phase.

import { useGameStore } from "../store/gameStore";
import { canBeat } from "../game/rules";
import { CardView } from "./CardView";
import { ActionBar } from "./ActionBar";

export function Hand() {
  const hand = useGameStore((s) => s.myHand);
  const hidden = useGameStore((s) => s.myHidden);
  const myLayer = useGameStore((s) => s.myLayer);
  const stack = useGameStore((s) => s.tableStack);
  const trump = useGameStore((s) => s.trump);
  const currentId = useGameStore((s) => s.currentId);
  const myId = useGameStore((s) => s.myPlayerId);
  const contribution = useGameStore((s) => s.contributionPhase);
  const selected = useGameStore((s) => s.selectedCard);
  const select = useGameStore((s) => s.selectCard);

  const isMyTurn = currentId === myId;
  const top = stack.length ? stack[stack.length - 1] : null;
  // Playable = it's my turn, no contribution phase, and the card beats the top
  // (any card is legal when opening a fresh stack).
  const playable = (code: string) =>
    isMyTurn && !contribution && (top === null || (trump ? canBeat(top, code, trump) : false));

  const active = myLayer === "hidden" ? hidden : hand;

  return (
    <div className="board-bottom">
      <div className="hand-wrap">
        {active.length === 0 ? (
          <span className="hint">No cards in this layer</span>
        ) : (
          active.map((code) => (
            <CardView
              key={code}
              code={code}
              selectable={playable(code)}
              selected={selected === code}
              disabled={!playable(code)}
              onClick={() => select(selected === code ? null : code)}
            />
          ))
        )}
      </div>
      <ActionBar />
    </div>
  );
}
