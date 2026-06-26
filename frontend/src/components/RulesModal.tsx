import type { MouseEvent } from "react";
import { useT } from "../i18n";

export function RulesModal({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  const t = useT();
  if (!open) return null;

  return (
    <div className="overlay" onClick={onClose}>
      <div
        className="modal rules-modal"
        onClick={(event: MouseEvent<HTMLDivElement>) => event.stopPropagation()}
      >
        <div className="rules-header">
          <h2>{t.rulesHeading}</h2>
          <button
            type="button"
            className="rules-close"
            aria-label={t.closeRules}
            onClick={onClose}
          >
            ×
          </button>
        </div>

        <div className="rules-body">
          <ul>
            {t.rulesLines.map((line, i) => (
              <li key={i}>{line}</li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}
