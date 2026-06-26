// WebSocket connection hook with auto-reconnect.
//
// Opens `<VITE_WS_URL>/ws/<roomId>?name=<myName>`. On connect, the backend
// re-sends the current room/game state, so reconnect requires no client-side
// replay. Inbound messages are dispatched to the Zustand store.

import { useCallback, useEffect } from "react";
import { useGameStore } from "../store/gameStore";
import type { ServerMessage } from "../types";

const proto = location.protocol === "https:" ? "wss:" : "ws:";
const WS_BASE = `${proto}//${location.host}`;

const MAX_RETRIES = 5;
const BASE_DELAY = 1000;
const MAX_DELAY = 10000;

// Module-scoped connection state so the standalone `open` helper can access it.
let retries = 0;
let manualClose = false;
let pendingTimer: ReturnType<typeof setTimeout> | null = null;

/**
 * Connect to the game room. Returns a disconnect function. Stable across
 * renders; callers usually invoke once.
 */
export function useWebSocket() {
  const connect = useCallback((roomId: string, name: string) => {
    manualClose = false;
    retries = 0;
    const url = `${WS_BASE}/ws/${encodeURIComponent(roomId)}?name=${encodeURIComponent(name)}`;
    useGameStore.getState().setIdentity(roomId, name, true);
    open(url);
  }, []);

  const disconnect = useCallback(() => {
    manualClose = true;
    if (pendingTimer) {
      clearTimeout(pendingTimer);
      pendingTimer = null;
    }
    const ws = useGameStore.getState().ws;
    if (ws) ws.close();
  }, []);

  useEffect(() => () => disconnect(), [disconnect]);

  return { connect, disconnect };
}

function open(url: string) {
  const ws = new WebSocket(url);

  ws.onopen = () => {
    retries = 0;
    useGameStore.getState().setWs(ws);
    useGameStore.getState().setConnected(true);
    useGameStore.getState().pushToast("info", "Connected");
  };

  ws.onmessage = (ev) => {
    let msg: ServerMessage;
    try {
      msg = JSON.parse(ev.data as string) as ServerMessage;
    } catch {
      useGameStore.getState().pushToast("error", "Received malformed message");
      return;
    }
    useGameStore.getState().dispatch(msg);
  };

  ws.onerror = () => {
    // Errors are usually followed by onclose; handled there.
  };

  ws.onclose = () => {
    useGameStore.getState().setConnected(false);
    useGameStore.getState().setWs(null);
    if (manualClose) return;
    if (retries >= MAX_RETRIES) {
      useGameStore
        .getState()
        .pushToast("error", "Connection lost — gave up reconnecting");
      return;
    }
    const delay = Math.min(BASE_DELAY * 2 ** retries, MAX_DELAY);
    retries += 1;
    useGameStore.getState().pushToast("info", `Reconnecting in ${delay / 1000}s…`);
    pendingTimer = setTimeout(() => open(url), delay);
  };
}
