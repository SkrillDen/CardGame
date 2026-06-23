// A single card. Renders face-up (with suit color) or face-down (back).
// When `selectable`, lifts on hover and applies selection styling.

import { memo } from "react";
import { cardLabel, parseCard, suitColor, SUIT_SYMBOL } from "../game/cards";

interface Props {
  code?: string; // when omitted, renders face-down
  faceDown?: boolean;
  selected?: boolean;
  selectable?: boolean;
  disabled?: boolean;
  onClick?: () => void;
}

function CardViewImpl({ code, faceDown, selected, selectable, disabled, onClick }: Props) {
  if (faceDown || !code) {
    return (
      <div className="card face-down" aria-hidden>
        <div className="center">◆</div>
      </div>
    );
  }
  const { rankLabel, suit } = parseCard(code);
  const color = suitColor(suit);
  const cls = [
    "card",
    color,
    selectable ? "selectable" : "",
    selected ? "selected" : "",
    disabled ? "disabled" : "",
  ].join(" ");
  return (
    <div
      className={cls}
      onClick={selectable && !disabled ? onClick : undefined}
      title={cardLabel(code)}
    >
      <div className="corner tl">
        {rankLabel}
        {SUIT_SYMBOL[suit]}
      </div>
      <div className="center">{SUIT_SYMBOL[suit]}</div>
      <div className="corner br">
        {rankLabel}
        {SUIT_SYMBOL[suit]}
      </div>
    </div>
  );
}

export const CardView = memo(CardViewImpl);
