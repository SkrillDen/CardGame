import type { MouseEvent } from "react";

export function RulesModal({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  if (!open) return null;

  return (
    <div className="overlay" onClick={onClose}>
      <div
        className="modal rules-modal"
        onClick={(event: MouseEvent<HTMLDivElement>) => event.stopPropagation()}
      >
        <div className="rules-header">
          <h2>Rules</h2>
          <button
            type="button"
            className="rules-close"
            aria-label="Close rules"
            onClick={onClose}
          >
            ×
          </button>
        </div>

        <div className="rules-body">
          <p>
            Goal: avoid being the last player who still has cards. The last remaining
            player loses.
          </p>
          <ul>
            <li>The game supports 2 to 5 players.</li>
            <li>The first card is placed automatically when the game starts.</li>
            <li>On your turn, play one card that beats the current top card on the table.</li>
            <li>A higher card of the same suit beats a lower one.</li>
            <li>A trump card beats any non-trump card.</li>
            <li>Spades are special: only a higher spade can beat a spade.</li>
            <li>If you cannot or do not want to beat, press <strong>Take bottom</strong>.</li>
            <li>That takes the bottom table card into your main hand and passes the turn.</li>
            <li>When the table stack reaches the number of active players, it is cleared as bito.</li>
            <li>In 2 to 3 player games, bito can trigger a shared buffer mechanic.</li>
            <li>During contribution, each active player sends one main-hand card into the buffer.</li>
            <li>After buffer distribution, players may move from main cards to buffer cards.</li>
            <li>When a player finishes buffer cards, their hidden cards are revealed.</li>
            <li>When a player runs out of hidden cards, they are out of the game.</li>
          </ul>
        </div>
      </div>
    </div>
  );
}
