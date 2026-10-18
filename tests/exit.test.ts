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
  const hints: (string | null)[] = [];
  let moves = 0;
  const exit = new ExitScene({
    game,
    storeRoot: root,
    player: { radius: 0.3, position: () => position },
    hud: { setHint: (t) => hints.push(t) },
    onDoorsMoved: () => moves++,
  });
  const at = (p: Vec2, seconds = 0.1) => {
    position = p;
    for (let t = 0; t < seconds; t += 0.1) exit.update(0.1);
  };
  return { game, exit, left, right, hints, at, moves: () => moves };
}

describe("ExitScene", () => {
  it("offers the way out only at the door, on E", () => {
    const { game, exit, hints, at } = setup();
    exit.press();
    at({ x: 0, z: 5 });
    expect(game.snapshot.state).toBe("STORE");
    at({ x: 0, z: 8.6 });
    expect(hints.at(-1)).toBe("Appuyez sur E pour sortir du magasin.");
    exit.press();
    at({ x: 0, z: 8.6 });
    expect(game.snapshot.state).toBe("EXIT");
  });

  it("slides the leaves into the wall, then reaches the end menu on the forecourt", () => {
    const { game, exit, left, right, at } = setup();
    at({ x: 0, z: 8.6 });
    exit.press();
    at({ x: 0, z: 8.6 }, EXIT_DOOR_SECONDS + 0.2);
    expect(exit.openness).toBe(1);
    expect(left.position.x).toBeCloseTo(-0.75 - 1.45);
    expect(right.position.x).toBeCloseTo(0.75 + 1.45);
    expect(exit.outdoorTarget).toBeCloseTo(0.3);
    at({ x: 0, z: 12 });
    expect(exit.outdoorTarget).toBe(1);
    at({ x: 0, z: 17 });
    expect(game.snapshot.state).toBe("END_MENU");
  });

  it("cancels when the player walks back in, and never closes on them", () => {
    const { game, exit, at } = setup();
    at({ x: 0, z: 8.6 });
    exit.press();
    at({ x: 0, z: 8.6 }, EXIT_DOOR_SECONDS + 0.2);
    at({ x: 0, z: 7 });
    expect(game.snapshot.state).toBe("STORE");
    const closing = exit.openness;
    expect(closing).toBeLessThan(1);
    at({ x: 0, z: 9.15 }, 3); // standing in the doorway: doors hold
    expect(exit.openness).toBe(closing);
    at({ x: 0, z: 6 }, EXIT_DOOR_SECONDS + 0.2);
    expect(exit.openness).toBe(0);
  });
});
