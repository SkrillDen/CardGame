// Contextual action bar. In normal play: Play / Take-bottom. During the
// contribution phase: a card picker to contribute to the shared buffer.

import { useState } from "react";
import { useGameStore } from "../store/gameStore";
import { useT } from "../i18n";

export function ActionBar() {
  const contribution = useGameStore((s) => s.contributionPhase);
  const contributionDue = useGameStore((s) => s.contributionDue);
  const myId = useGameStore((s) => s.myPlayerId);
  const myHand = useGameStore((s) => s.myHand);
  const send = useGameStore((s) => s.send);

  if (contribution) {
    return <ContributeBar due={contributionDue.includes(myId ?? "")} myHand={myHand} send={send} />;
  }
  return <PlayBar />;
}

function PlayBar() {
  const t = useT();
  const selected = useGameStore((s) => s.selectedCard);
  const stack = useGameStore((s) => s.tableStack);
  const currentId = useGameStore((s) => s.currentId);
  const myId = useGameStore((s) => s.myPlayerId);
  const send = useGameStore((s) => s.send);
  const select = useGameStore((s) => s.selectCard);

  const isMyTurn = currentId === myId;
  const canPlay = isMyTurn && selected !== null;
  const canTake = isMyTurn && stack.length > 0;

  return (
    <div className="action-bar">
      <button
        className="primary"
        disabled={!canPlay}
        onClick={() => {
          if (selected) {
            send({ type: "play_card", payload: { card: selected } });
            select(null);
          }
        }}
      >
        {t.btnPlayCard}
      </button>
      <button
        className="secondary"
        disabled={!canTake}
        onClick={() => send({ type: "take_bottom", payload: {} })}
      >
        {t.btnTakeBottom}
      </button>
      {!isMyTurn && <span className="hint">{t.waitingForTurn}</span>}
    </div>
  );
}

function ContributeBar({
  due,
  myHand,
  send,
}: {
  due: boolean;
  myHand: string[];
  send: (m: Parameters<ReturnType<typeof useGameStore.getState>["send"]>[0]) => void;
}) {
  const t = useT();
  const [picked, setPicked] = useState<string | null>(null);
  if (!due) {
    return (
      <div className="action-bar">
        <span className="hint">{t.waitingContribute}</span>
      </div>
    );
  }
  return (
    <div className="action-bar" style={{ flexDirection: "column", alignItems: "stretch" }}>
      <span className="hint">{t.pickContribute}</span>
      <div className="hand-wrap">
        {myHand.map((c) => (
          <button
            key={c}
            className={picked === c ? "primary" : "secondary"}
            onClick={() => setPicked(c)}
          >
            {c}
          </button>
        ))}
      </div>
      <button
        className="primary"
        disabled={!picked}
        onClick={() => {
          if (picked) {
            send({ type: "contribute_buffer", payload: { card: picked } });
            setPicked(null);
          }
        }}
      >
        {t.btnContribute}
      </button>
    </div>
  );
}
