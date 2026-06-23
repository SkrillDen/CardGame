// TypeScript types mirroring the backend WebSocket contract exactly.
// Backend source of truth: backend/game/engine.py (make_event) and manager.py.

// ---- Card primitives -------------------------------------------------------

export type Suit = "S" | "H" | "D" | "C"; // Spades, Hearts, Diamonds, Clubs
export type Layer = "main" | "buffer" | "hidden";

/** Card code, e.g. "7H", "10D", "AS". 10 is the only three-char code. */
export type CardCode = string;

// ---- Public game state (from game_state event) ----------------------------

export interface PlayerView {
  id: string;
  name: string;
  card_count: number;
  layer: Layer;
  eliminated?: boolean;
}

// ---- Server -> Client message types ---------------------------------------

export interface RoomUpdatePayload {
  room_id: string;
  started?: boolean;
  players: { id: string; name: string }[];
}

export interface GameStatePayload {
  trump: Suit;
  table_stack: CardCode[];
  table_stack_size: number;
  current_player_id: string;
  active_players: PlayerView[];
  bito_count: number;
  buffer_size: number;
  buffer_distributed: boolean;
  contribution_phase: boolean;
  contribution_due: string[];
}

export interface CardPlayedPayload {
  player_id: string;
  card: CardCode;
  automatic?: boolean;
}

export interface CardTakenPayload {
  player_id: string;
  card: CardCode;
  reason?: "take" | "forced";
}

export interface BitоPayload {
  bito_count: number;
  closer_id: string;
}

export interface BufferRequestPayload {
  due: string[];
}

export interface BufferTriggeredPayload {
  new_trump: Suit;
  trigger_id: string;
  shares: Record<string, number>;
}

export interface BufferContributedPayload {
  player_id: string;
  buffer_size: number;
}

export interface LayerChangedPayload {
  player_id: string;
  layer: Layer;
}

export interface TurnSkippedPayload {
  player_id: string;
}

export interface PlayerOutPayload {
  player_id: string;
}

export interface GameOverPayload {
  loser_id: string | null;
}

export interface GameStartedPayload {
  trump: Suit;
  opening_card: CardCode;
}

// Private (player-specific) payloads
export interface HandUpdatePayload {
  cards: CardCode[];
}
export interface BufferSharePayload {
  cards: CardCode[];
  deferred?: boolean;
}
export interface HiddenRevealedPayload {
  cards: CardCode[];
}

export interface ErrorPayload {
  code: string;
  message: string;
}

export type ServerMessage =
  | { type: "room_update"; payload: RoomUpdatePayload }
  | { type: "game_started"; payload: GameStartedPayload }
  | { type: "game_state"; payload: GameStatePayload }
  | { type: "card_played"; payload: CardPlayedPayload }
  | { type: "card_taken"; payload: CardTakenPayload }
  | { type: "bito"; payload: BitоPayload }
  | { type: "buffer_request"; payload: BufferRequestPayload }
  | { type: "buffer_triggered"; payload: BufferTriggeredPayload }
  | { type: "buffer_contributed"; payload: BufferContributedPayload }
  | { type: "layer_changed"; payload: LayerChangedPayload }
  | { type: "turn_skipped"; payload: TurnSkippedPayload }
  | { type: "player_out"; payload: PlayerOutPayload }
  | { type: "game_over"; payload: GameOverPayload }
  | { type: "hand_update"; payload: HandUpdatePayload }
  | { type: "buffer_share"; payload: BufferSharePayload }
  | { type: "hidden_revealed"; payload: HiddenRevealedPayload }
  | { type: "error"; payload: ErrorPayload };

// ---- Client -> Server message types ---------------------------------------

export type ClientMessage =
  | { type: "create_room"; payload: { name: string } }
  | { type: "join_room"; payload: { room_id: string; name: string } }
  | { type: "start_game"; payload: Record<string, never> }
  | { type: "play_card"; payload: { card: CardCode } }
  | { type: "take_bottom"; payload: Record<string, never> }
  | { type: "contribute_buffer"; payload: { card: CardCode } };
