import { describe, expect, it } from "vitest";
import { RUNTIME_FAILURE, createErrorLog, recoverFromError } from "../src/app/errors";
import { EventBus } from "../src/core/EventBus";
import { GameState, type GameEvents } from "../src/core/GameState";

function game() {
  const g = new GameState(new EventBus<GameEvents>());
  g.send({ type: "START" });
  return g;
}

describe("recoverFromError", () => {
  it("starts the safe return when a shelf is open", () => {
    const g = game();
    g.send({ type: "SCAN_CONFIRMED", chainId: "eggs" });
    expect(recoverFromError(g)).toBe(true);
    expect(g.snapshot).toEqual({ state: "ERROR", activeChain: "eggs", error: RUNTIME_FAILURE });
  });

  it("does nothing in the store or while already recovering", () => {
    const g = game();
    expect(recoverFromError(g)).toBe(false);
    g.send({ type: "SCAN_CONFIRMED", chainId: "eggs" });
    recoverFromError(g);
    expect(recoverFromError(g)).toBe(false);
  });
});

describe("createErrorLog", () => {
  it("logs a repeated error once", () => {
    const seen: unknown[] = [];
    const log = createErrorLog((e) => seen.push(e));
    const error = new Error("boom");
    log(error);
    log(new Error("boom"));
    log(new Error("other"));
    expect(seen).toHaveLength(2);
  });
});
