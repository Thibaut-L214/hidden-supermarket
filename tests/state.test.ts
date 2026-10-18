import { describe, expect, it } from "vitest";
import { EventBus } from "../src/core/EventBus";
import {
  GameState,
  INITIAL_SNAPSHOT,
  canWalk,
  transition,
  type GameEvent,
  type GameEvents,
  type GameSnapshot,
  type GameStateId,
} from "../src/core/GameState";

function run(events: GameEvent[], from: GameSnapshot = INITIAL_SNAPSHOT): GameSnapshot {
  return events.reduce((snapshot, event) => transition(snapshot, event) ?? snapshot, from);
}

const toTerrace: GameEvent[] = [
  { type: "START" },
  { type: "SCAN_CONFIRMED", chainId: "eggs" },
  { type: "MODULE_READY" },
  { type: "DOORS_OPEN" },
];
const toRecap: GameEvent[] = [
  ...toTerrace,
  { type: "VIEWPOINT_REACHED" },
  { type: "ROOF_REVEALED" },
  { type: "TIMELINE_DONE" },
];

describe("transition", () => {
  it("plays the eggs shelf from intro to recap", () => {
    expect(run(toRecap)).toEqual({ state: "RECAP", activeChain: "eggs" });
  });

  it("replays the chain from the recap", () => {
    expect(run([...toRecap, { type: "REPLAY" }]).state).toBe("CHAIN");
  });

  it.each<[string, GameEvent[]]>([
    ["TERRACE", toTerrace],
    ["REVEAL", [...toTerrace, { type: "VIEWPOINT_REACHED" }]],
    ["CHAIN", [...toTerrace, { type: "VIEWPOINT_REACHED" }, { type: "ROOF_REVEALED" }]],
    ["RECAP", toRecap],
  ])("returns to the store from %s", (_, path) => {
    const back = run([...path, { type: "RETURN_REQUESTED" }, { type: "DOORS_CLOSED" }]);
    expect(back).toEqual({ state: "STORE", activeChain: null });
  });

  it("goes back to the terrace when the player turns around during the return", () => {
    const back = run([...toRecap, { type: "RETURN_REQUESTED" }, { type: "TERRACE_ENTERED" }]);
    expect(back).toEqual({ state: "TERRACE", activeChain: "eggs" });
    expect(transition(run(toTerrace), { type: "TERRACE_ENTERED" })).toBeNull();
  });

  it("refuses a second scan while a shelf is opening", () => {
    const opening = run(toTerrace.slice(0, 3));
    expect(opening.state).toBe("OPENING");
    expect(transition(opening, { type: "SCAN_CONFIRMED", chainId: "pork" })).toBeNull();
  });

  it("ignores events that do not apply to the current state", () => {
    expect(transition(INITIAL_SNAPSHOT, { type: "DOORS_OPEN" })).toBeNull();
    expect(transition(run(toRecap), { type: "START" })).toBeNull();
  });

  it("recovers from a failure through the safe return", () => {
    const failed = run([...toTerrace.slice(0, 2), { type: "FAILURE", reason: "GLB" }]);
    expect(failed).toEqual({ state: "ERROR", activeChain: "eggs", error: "GLB" });
    const safe = run([{ type: "ERROR_ACKNOWLEDGED" }, { type: "SAFE_RESTORED" }], failed);
    expect(safe).toEqual({ state: "STORE", activeChain: null });
  });

  it("leaves through the exit and can come back into the store", () => {
    const menu = run([{ type: "START" }, { type: "EXIT_REQUESTED" }, { type: "PARVIS_REACHED" }]);
    expect(menu.state).toBe("END_MENU");
    expect(run([{ type: "RESUME_STORE" }], menu).state).toBe("STORE");
  });
});

describe("canWalk", () => {
  it.each<[GameStateId, boolean]>([
    ["INTRO", false],
    ["STORE", true],
    ["OPENING", true],
    ["CHAIN", true],
    ["END_MENU", false],
    ["ERROR", false],
  ])("%s → %s", (state, expected) => {
    expect(canWalk(state)).toBe(expected);
  });
});

describe("GameState", () => {
  it("emits one stateChanged per accepted event and none for rejected ones", () => {
    const bus = new EventBus<GameEvents>();
    const game = new GameState(bus);
    const seen: string[] = [];
    bus.on("stateChanged", ({ from, to }) => seen.push(`${from}→${to}`));

    expect(game.send({ type: "START" })).toBe(true);
    expect(game.send({ type: "START" })).toBe(false);
    game.send({ type: "SCAN_CONFIRMED", chainId: "eggs" });

    expect(seen).toEqual(["INTRO→STORE", "STORE→SCANNING"]);
    expect(game.snapshot).toEqual({ state: "SCANNING", activeChain: "eggs" });
  });
});
