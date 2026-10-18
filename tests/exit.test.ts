import { BoxGeometry, Group, Mesh } from "three";
import { describe, expect, it } from "vitest";
import { EventBus } from "../src/core/EventBus";
import { GameState, type GameEvents } from "../src/core/GameState";
import { EXIT_DOOR_SECONDS, ExitScene } from "../src/features/exit/ExitScene";
import type { Vec2 } from "../src/world/CollisionWorld";

/** Entrance laid out like the blockout in glTF space: store interior at z < 9. */
function store() {
  const root = new Group();
  const add = (name: string, size: [number, number, number], at: [number, number, number]) => {
    const mesh = new Mesh(new BoxGeometry(...size));
    mesh.name = name;
    mesh.position.set(...at);
    root.add(mesh);
    return mesh;
  };
  const left = add("STORE_ENTRANCE_DOOR_L", [1.5, 2.6, 0.1], [-0.75, 1.3, 9.15]);
  const right = add("STORE_ENTRANCE_DOOR_R", [1.5, 2.6, 0.1], [0.75, 1.3, 9.15]);
  add("TRIGGER_EXIT", [3, 2.4, 0.8], [0, 1.2, 8.6]);
  add("TRIGGER_PARVIS", [20, 2.4, 2], [0, 1.2, 17]);
  root.updateMatrixWorld(true);
  return { root, left, right };
}

function setup() {
  const game = new GameState(new EventBus<GameEvents>());
  game.send({ type: "START" });
  const { root, left, right } = store();
  let position: Vec2 = { x: 0, z: 5 };
  let moves = 0;
  const exit = new ExitScene({
    game,
    storeRoot: root,
    player: { radius: 0.3, position: () => position },
    onDoorsMoved: () => moves++,
  });
  const at = (p: Vec2, seconds = 0.1) => {
    position = p;
    for (let t = 0; t < seconds; t += 0.1) exit.update(0.1);
  };
  return { game, exit, left, right, at, moves: () => moves };
}

const OPEN = EXIT_DOOR_SECONDS + 0.2;

describe("ExitScene", () => {
  it("keeps the doors shut while the player is away, and slides both leaves open on approach", () => {
    const { game, exit, left, right, at } = setup();
    at({ x: 0, z: 5 }, OPEN);
    expect(exit.openness).toBe(0);
    at({ x: 0.5, z: 8.0 }, OPEN);
    expect(exit.openness).toBe(1);
    expect(left.position.x).toBeCloseTo(-0.75 - 1.45);
    expect(right.position.x).toBeCloseTo(0.75 + 1.45);
    expect(game.snapshot.state).toBe("STORE");
  });

  it("starts the exit on stepping outside and reaches the end menu on the forecourt", () => {
    const { game, exit, at } = setup();
    at({ x: 0, z: 8.6 }, OPEN);
    at({ x: 0, z: 9.6 });
    expect(game.snapshot.state).toBe("EXIT");
    expect(exit.outdoorTarget).toBe(1);
    at({ x: 0, z: 17 });
    expect(game.snapshot.state).toBe("END_MENU");
  });

  it("cancels when the player walks back in, closes behind them, never on them", () => {
    const { game, exit, at } = setup();
    at({ x: 0, z: 8.6 }, OPEN);
    at({ x: 0, z: 10 });
    at({ x: 0, z: 7.5 });
    expect(game.snapshot.state).toBe("STORE");
    at({ x: 0, z: 5 });
    const closing = exit.openness;
    expect(closing).toBeLessThan(1);
    at({ x: 0, z: 9.15 }, 3); // back in the doorway: the leaves wait
    expect(exit.openness).toBeGreaterThanOrEqual(closing);
    at({ x: 0, z: 5 }, OPEN);
    expect(exit.openness).toBe(0);
  });

  it("opens for a player coming back from the forecourt", () => {
    const { exit, at } = setup();
    at({ x: 0, z: 8.6 }, OPEN);
    at({ x: 0, z: 15 }, OPEN); // far on the forecourt: the doors close behind
    expect(exit.openness).toBe(0);
    at({ x: 0, z: 11.5 }, OPEN);
    expect(exit.openness).toBe(1);
  });

  it("stays shut while a shelf is open", () => {
    const { game, exit, at } = setup();
    game.send({ type: "SCAN_CONFIRMED", chainId: "eggs" });
    at({ x: 0, z: 8.6 }, OPEN);
    expect(exit.openness).toBe(0);
  });
});
