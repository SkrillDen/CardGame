// Table panel: trump indicator, the bottom->top stack (top card emphasized),
// and chips for bito count, buffer size, and distribution status.

import { useGameStore } from "../store/gameStore";
import { useT } from "../i18n";
import { SUIT_SYMBOL, suitColor } from "../game/cards";
import { CardView } from "./CardView";

export function Table() {
  const t = useT();
  const trump = useGameStore((s) => s.trump);
  const stack = useGameStore((s) => s.tableStack);
  const bitoCount = useGameStore((s) => s.bitoCount);
  const bufferSize = useGameStore((s) => s.bufferSize);
  const bufferDistributed = useGameStore((s) => s.bufferDistributed);

  return (
    <div className="table-panel">
      <div className="trump-indicator" title={t.trumpTitle}>
        <span className="label">{t.trumpLabel}</span>
        <span className={`suit ${trump ? suitColor(trump) : ""}`}>
          {trump ? SUIT_SYMBOL[trump] : "?"}
        </span>
      </div>

      <div className="stack">
        {stack.length === 0 ? (
          <span className="stack-empty">{t.stackEmpty}</span>
        ) : (
          stack.map((c, i) => (
            <CardView key={`${c}-${i}`} code={c} selected={i === stack.length - 1} />
          ))
        )}
      </div>

      <div className="chip-row">
        <span className="chip">{t.chipBito(bitoCount)}</span>
        <span className="chip">{t.chipBuffer(bufferSize)}</span>
        {bufferDistributed && <span className="chip">{t.chipBufferDealt}</span>}
      </div>
    </div>
  );
}
