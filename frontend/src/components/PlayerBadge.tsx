// A per-player "hidden: N" badge. Until the local player's hidden cards are
// revealed, shows a count badge; once revealed, shows the faces inline.

import { CardView } from "./CardView";
import { useT } from "../i18n";

interface Props {
  hiddenCount: number;
  revealedCards: string[];
  isMe: boolean;
}

export function PlayerBadge({ hiddenCount, revealedCards, isMe }: Props) {
  const t = useT();
  if (revealedCards.length > 0) {
    return (
      <div className="hand-wrap" style={{ minHeight: "auto" }}>
        {revealedCards.map((c, i) => (
          <CardView key={`${c}-${i}`} code={c} />
        ))}
      </div>
    );
  }
  if (hiddenCount > 0 && isMe) {
    return <span className="badge-hidden">{t.hiddenCount(hiddenCount)}</span>;
  }
  return null;
}
