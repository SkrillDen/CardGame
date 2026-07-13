// Central client state. Zustand store holding the public game snapshot, the
// player's private hand/hidden info, and connection status. The WebSocket
// hook feeds every inbound message to `dispatch`; outbound messages go via
// `send`.

import { create } from "zustand";
import { getT } from "../i18n";
import type {
  CardCode,
  ClientMessage,
  Layer,
  PlayerView,
  ServerMessage,
  Suit,
} from "../types";

export type Phase = "lobby" | "waiting" | "playing" | "over";

export interface Toast {
  id: number;
  kind: "info" | "success" | "error";
  text: string;
}

export interface GameState {
  // Identity / connection
  phase: Phase;
  ws: WebSocket | null;
  connected: boolean;
  connectionLost: boolean; // true after all reconnect retries exhausted
  roomId: string | null;
  myName: string;
  myPlayerId: string | null;
  isHost: boolean;
  // Public snapshot (from latest game_state)
  players: PlayerView[];
  trump: Suit | null;
  tableStack: CardCode[];
  currentId: string | null;
  bitoCount: number;
  bufferSize: number;
  bufferDistributed: boolean;
  contributionPhase: boolean;
  contributionDue: string[];
  // Private
  myHand: CardCode[];
  myHidden: CardCode[]; // revealed faces; empty until hidden_revealed
  myHiddenCount: number; // badge counter; 2 at start, drained as played
  myLayer: Layer;
  // UI
  selectedCard: CardCode | null;
  loserId: string | null;
  toasts: Toast[];
  lastPlayed: CardCode | null; // last card played to the table (any player)
  bitoFlash: CardCode | null;  // winning card kept visible briefly after bito
}

interface Actions {
  setWs: (ws: WebSocket | null) => void;
  setConnected: (v: boolean) => void;
  setConnectionLost: (v: boolean) => void;
  setIdentity: (room: string, name: string, host: boolean) => void;
  send: (msg: ClientMessage) => void;
  dispatch: (msg: ServerMessage) => void;
  selectCard: (code: CardCode | null) => void;
  resetForLobby: () => void;
  pushToast: (kind: Toast["kind"], text: string) => void;
  dismissToast: (id: number) => void;
}

let toastSeq = 0;

const initial: GameState = {
  phase: "lobby",
  ws: null,
  connected: false,
  connectionLost: false,
  roomId: null,
  myName: "",
  myPlayerId: null,
  isHost: false,
  players: [],
  trump: null,
  tableStack: [],
  currentId: null,
  bitoCount: 0,
  bufferSize: 0,
  bufferDistributed: false,
  contributionPhase: false,
  contributionDue: [],
  myHand: [],
  myHidden: [],
  myHiddenCount: 0,
  myLayer: "main",
  selectedCard: null,
  loserId: null,
  toasts: [],
  lastPlayed: null,
  bitoFlash: null,
};

export const useGameStore = create<GameState & Actions>((set, get) => ({
  ...initial,

  setWs: (ws) => set({ ws }),
  setConnected: (v) => set({ connected: v }),
  setConnectionLost: (v) => set({ connectionLost: v }),
  setIdentity: (room, name, host) =>
    set({ roomId: room, myName: name, isHost: host }),

  send: (msg) => {
    const ws = get().ws;
    if (!ws || ws.readyState !== WebSocket.OPEN) {
      get().pushToast("error", getT().toastNotConnected);
      return;
    }
    ws.send(JSON.stringify(msg));
  },

  selectCard: (code) => set({ selectedCard: code }),

  resetForLobby: () => set({ ...initial, myName: get().myName, ws: get().ws, connected: get().connected }),

  pushToast: (kind, text) => {
    const id = ++toastSeq;
    set((s) => ({ toasts: [...s.toasts, { id, kind, text }] }));
    // auto-dismiss
    setTimeout(() => get().dismissToast(id), 3500);
  },
  dismissToast: (id) =>
    set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) })),

  dispatch: (msg) => {
    const { type, payload } = msg;
    switch (type) {
      // ---- Lobby ----
      case "room_update": {
        // The first player listed is the host (creator). My id is whichever
        // entry matches my name.
        const me = payload.players.find((p) => p.name === get().myName);
        set({
          myPlayerId: me?.id ?? get().myPlayerId,
          players: payload.players.map((p) => ({
            id: p.id,
            name: p.name,
            card_count: 0,
            layer: "main" as Layer,
          })),
          phase: payload.started ? "playing" : get().phase === "lobby" ? "lobby" : get().phase,
        });
        break;
      }

      // ---- Game start ----
      case "game_started":
        set({ phase: "playing", trump: payload.trump });
        get().pushToast("info", getT().toastGameStarted(payload.trump));
        break;

      // ---- Public snapshot (re-applied after every action) ----
      case "game_state": {
        const me = payload.active_players.find(
          (p) => p.id === get().myPlayerId
        );
        set({
          players: payload.active_players,
          trump: payload.trump,
          tableStack: payload.table_stack,
          currentId: payload.current_player_id,
          bitoCount: payload.bito_count,
          bufferSize: payload.buffer_size,
          bufferDistributed: payload.buffer_distributed,
          contributionPhase: payload.contribution_phase,
          contributionDue: payload.contribution_due,
          myLayer: me?.layer ?? get().myLayer,
        });
        // Clear selection if the card is no longer in hand.
        const hand = get().myHand;
        if (get().selectedCard && !hand.includes(get().selectedCard!)) {
          set({ selectedCard: null });
        }
        break;
      }

      // ---- Narrative events (mostly toasts; state comes via game_state) ----
      case "card_played":
        // Remember the last card on the table so we can keep the winning card
        // visible for a moment when the stack is cleared to bito.
        set({ lastPlayed: payload.card });
        // If I played, drop it from my hand optimistically (server corrects).
        if (payload.player_id === get().myPlayerId) {
          set((s) => ({
            myHand: s.myHand.filter((c) => c !== payload.card),
            myHidden: s.myHidden.filter((c) => c !== payload.card),
            selectedCard:
              s.selectedCard === payload.card ? null : s.selectedCard,
          }));
        }
        break;

      case "card_taken":
        // If I took, the card enters my main hand (server's hand_update will
        // confirm). No optimistic change needed here.
        if (payload.reason === "forced" && payload.player_id === get().myPlayerId) {
          get().pushToast("error", getT().toastForcedTake);
        }
        break;

      case "bito": {
        get().pushToast("success", getT().toastBito(payload.bito_count));
        // Keep the last (winning) card visible briefly instead of letting the
        // whole stack vanish instantly when the next game_state empties it.
        const winning = get().lastPlayed;
        if (winning) {
          set({ bitoFlash: winning });
          setTimeout(() => {
            if (get().bitoFlash === winning) set({ bitoFlash: null });
          }, 1500);
        }
        break;
      }

      case "buffer_request":
        get().pushToast("info", getT().toastContributeRequest);
        break;

      case "buffer_triggered":
        // Apply the new trump immediately so the indicator and hand-legality
        // hints update on this turn, not one move later.
        set({ trump: payload.new_trump });
        get().pushToast("info", getT().toastBufferTriggered(payload.new_trump));
        break;

      case "buffer_contributed":
        if (payload.player_id === get().myPlayerId) {
          set((s) => ({
            contributionDue: s.contributionDue.filter((id) => id !== payload.player_id),
          }));
        }
        // Private hand state is reconciled by the accompanying hand_update.
        break;

      case "layer_changed":
        if (payload.player_id === get().myPlayerId) {
          set({ myLayer: payload.layer });
        }
        break;

      case "turn_skipped":
        if (payload.player_id === get().myPlayerId) {
          get().pushToast("info", getT().toastTurnSkipped);
        }
        break;

      case "player_out": {
        const out = get().players.find((p) => p.id === payload.player_id);
        get().pushToast("info", getT().toastPlayerOut(out?.name ?? "?"));
        break;
      }

      case "game_over":
        set({ phase: "over", loserId: payload.loser_id });
        break;

      // ---- Private messages (only to me) ----
      case "hand_update":
        set({ myHand: payload.cards });
        // Active-layer hand replaces selection if invalid.
        if (get().selectedCard && !payload.cards.includes(get().selectedCard!)) {
          set({ selectedCard: null });
        }
        break;

      case "buffer_share":
        set({ myHand: payload.cards, myLayer: "buffer" });
        get().pushToast("success", getT().toastBufferShare);
        break;

      case "hidden_revealed":
        set({ myHidden: payload.cards, myLayer: "hidden" });
        get().pushToast("info", getT().toastHiddenRevealed);
        break;

      case "error":
        get().pushToast("error", payload.message);
        break;

      default:
        // Unknown message types are ignored defensively.
        break;
    }
  },
}));
