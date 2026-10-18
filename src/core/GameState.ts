// Game flow state machine (docs/DECISIONS.md, « Machine à états »). Pure: no DOM, no three.js.
import type { ChainId } from "./chain";
import type { EventBus } from "./EventBus";

export type GameStateId =
  | "INTRO"
  | "STORE"
  | "SCANNING"
  | "OPENING"
  | "TERRACE"
  | "REVEAL"
  | "CHAIN"
  | "RECAP"
  | "RETURN"
  | "EXIT"
  | "END_MENU"
  | "ERROR"
  | "SAFE_RETURN";

export type GameEvent =
  | { type: "START" }
  | { type: "SCAN_CONFIRMED"; chainId: ChainId }
  | { type: "MODULE_READY" }
  | { type: "DOORS_OPEN" }
  | { type: "VIEWPOINT_REACHED" }
  | { type: "ROOF_REVEALED" }
  | { type: "TIMELINE_DONE" }
  | { type: "REPLAY" }
  | { type: "RETURN_REQUESTED" }
  | { type: "DOORS_CLOSED" }
  | { type: "EXIT_REQUESTED" }
  | { type: "PARVIS_REACHED" }
  | { type: "RESUME_STORE" }
  | { type: "FAILURE"; reason: string }
  | { type: "ERROR_ACKNOWLEDGED" }
  | { type: "SAFE_RESTORED" };

export interface GameSnapshot {
  state: GameStateId;
  /** The single shelf being explored; null in the store. */
  activeChain: ChainId | null;
  error?: string;
}

export interface StateChange {
  from: GameStateId;
  to: GameStateId;
  event: GameEvent;
  snapshot: GameSnapshot;
}

export interface GameEvents {
  stateChanged: StateChange;
}

export const INITIAL_SNAPSHOT: GameSnapshot = { state: "INTRO", activeChain: null };

const IN_CHAIN_MODULE: readonly GameStateId[] = ["TERRACE", "REVEAL", "CHAIN", "RECAP"];
const NO_WALKING: readonly GameStateId[] = ["INTRO", "END_MENU", "ERROR", "SAFE_RETURN"];

/** Next snapshot, or null when the event does not apply to the current state. */
export function transition(current: GameSnapshot, event: GameEvent): GameSnapshot | null {
  const { state, activeChain } = current;
  const to = (next: GameStateId): GameSnapshot => ({ state: next, activeChain });
  const inStore = (next: GameStateId): GameSnapshot => ({ state: next, activeChain: null });

  switch (event.type) {
    case "START":
      return state === "INTRO" ? inStore("STORE") : null;
    case "SCAN_CONFIRMED":
      return state === "STORE" ? { state: "SCANNING", activeChain: event.chainId } : null;
    case "MODULE_READY":
      return state === "SCANNING" ? to("OPENING") : null;
    case "DOORS_OPEN":
      return state === "OPENING" ? to("TERRACE") : null;
    case "VIEWPOINT_REACHED":
      return state === "TERRACE" ? to("REVEAL") : null;
    case "ROOF_REVEALED":
      return state === "REVEAL" ? to("CHAIN") : null;
    case "TIMELINE_DONE":
      return state === "CHAIN" ? to("RECAP") : null;
    case "REPLAY":
      return state === "RECAP" ? to("CHAIN") : null;
    case "RETURN_REQUESTED":
      return IN_CHAIN_MODULE.includes(state) ? to("RETURN") : null;
    case "DOORS_CLOSED":
      return state === "RETURN" ? inStore("STORE") : null;
    case "EXIT_REQUESTED":
      return state === "STORE" ? inStore("EXIT") : null;
    case "PARVIS_REACHED":
      return state === "EXIT" ? inStore("END_MENU") : null;
    case "RESUME_STORE":
      return state === "END_MENU" ? inStore("STORE") : null;
    case "FAILURE":
      return state === "ERROR" ? null : { state: "ERROR", activeChain, error: event.reason };
    case "ERROR_ACKNOWLEDGED":
      return state === "ERROR" ? to("SAFE_RETURN") : null;
    case "SAFE_RESTORED":
      return state === "SAFE_RETURN" ? inStore("STORE") : null;
  }
}

export function canWalk(state: GameStateId): boolean {
  return !NO_WALKING.includes(state);
}

/** Holds the current snapshot and announces every accepted transition on the bus. */
export class GameState {
  private current: GameSnapshot = INITIAL_SNAPSHOT;

  constructor(private readonly bus: EventBus<GameEvents>) {}

  get snapshot(): GameSnapshot {
    return this.current;
  }

  /** Returns false when the event was rejected (state unchanged, nothing emitted). */
  send(event: GameEvent): boolean {
    const next = transition(this.current, event);
    if (!next) return false;
    const from = this.current.state;
    this.current = next;
    this.bus.emit("stateChanged", { from, to: next.state, event, snapshot: next });
    return true;
  }
}
