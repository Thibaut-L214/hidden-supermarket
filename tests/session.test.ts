import { describe, expect, it } from "vitest";
import { Session, trackExploration } from "../src/app/session";
import { EventBus } from "../src/core/EventBus";
import { GameState, type GameEvents } from "../src/core/GameState";

function setup() {
  const bus = new EventBus<GameEvents>();
  const game = new GameState(bus);
  const session = new Session();
  trackExploration(bus, session);
  game.send({ type: "START" });
  game.send({ type: "SCAN_CONFIRMED", chainId: "eggs" });
  game.send({ type: "MODULE_READY" });
  game.send({ type: "DOORS_OPEN" });
  return { game, session };
}

describe("trackExploration", () => {
  it("marks the shelf explored once its chain reaches the recap, without duplicates", () => {
    const { game, session } = setup();
    game.send({ type: "VIEWPOINT_REACHED" });
    game.send({ type: "ROOF_REVEALED" });
    game.send({ type: "TIMELINE_DONE" });
    game.send({ type: "REPLAY" });
    game.send({ type: "TIMELINE_DONE" });
    game.send({ type: "RETURN_REQUESTED" });
    game.send({ type: "DOORS_CLOSED" });
    expect(session.exploredChains).toEqual(["eggs"]);
  });

  it("does not mark a shelf left before the end of its chain", () => {
    const { game, session } = setup();
    game.send({ type: "RETURN_REQUESTED" });
    game.send({ type: "DOORS_CLOSED" });
    expect(session.hasExplored("eggs")).toBe(false);
  });
});
