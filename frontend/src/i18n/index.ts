// Locale store + hook.
//
// Usage in React components:
//   const t = useT();
//   <span>{t.connected}</span>
//   <span>{t.cardCount(5)}</span>
//
// Usage outside React (gameStore, useWebSocket):
//   import { getT } from "../i18n";
//   getT().toastConnected

import { create } from "zustand";
import { locales, type Locale, type Strings } from "./locales";

const STORAGE_KEY = "durak_locale";

function loadLocale(): Locale {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved === "en" || saved === "ru") return saved;
  } catch {}
  // Auto-detect browser language: use Russian if the browser is set to it.
  const lang = navigator.language.toLowerCase();
  return lang.startsWith("ru") ? "ru" : "en";
}

interface LocaleState {
  locale: Locale;
  setLocale: (l: Locale) => void;
}

export const useLocaleStore = create<LocaleState>((set) => ({
  locale: loadLocale(),
  setLocale: (locale) => {
    try {
      localStorage.setItem(STORAGE_KEY, locale);
    } catch {}
    set({ locale });
  },
}));

/** Hook: returns the current translations object. Re-renders on locale change. */
export function useT(): Strings {
  const locale = useLocaleStore((s) => s.locale);
  return locales[locale] as Strings;
}

/** Non-hook accessor for use in Zustand stores and plain functions. */
export function getT(): Strings {
  return locales[useLocaleStore.getState().locale] as Strings;
}
