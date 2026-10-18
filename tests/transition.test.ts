import { BoxGeometry, Group, Mesh, Object3D, Scene } from "three";
import { describe, expect, it } from "vitest";
import type { AssetContract } from "../src/core/assetContract";
import type { AssetManager } from "../src/core/AssetManager";
import { eggs } from "../src/data/chains/eggs";
import { EventBus } from "../src/core/EventBus";
import { GameState, type GameEvents } from "../src/core/GameState";
import {
  TerraceTransition,
  doorTarget,
  sideOf,
  type Threshold,
} from "../src/features/portal/TerraceTransition";
import { CollisionWorld, type Vec2 } from "../src/world/CollisionWorld";

const threshold: Threshold = {
  zone: { minX: -1.5, maxX: 1.5, minZ: -9.9, maxZ: -8.4 },
  centre: { x: 0, z: -9.15 },
  storeNormal: { x: 0, z: 1 },
};

describe("sideOf", () => {
  it.each([
    [{ x: 0, z: -6 }, "terrace", "store"],
    [{ x: 0, z: -12 }, "store", "terrace"],
    [{ x: 0, z: -9 }, "terrace", "terrace"],
    [{ x: 0, z: -9 }, "store", "store"],
  ] as const)("%o (was %s) → %s", (p, previous, expected) => {
    expect(sideOf(p, threshold, previous)).toBe(expected);
  });
});

describe("doorTarget", () => {
  it.each([
    ["OPENING", "store", false, "open"],
    ["OPENING", "store", true, "hold"],
    ["CHAIN", "store", true, "open"],
    ["RETURN", "terrace", true, "open"],
    ["RETURN", "store", true, "hold"],
    ["RETURN", "store", false, "closed"],
    ["STORE", "store", false, "closed"],
  ] as const)("%s, %s side, in swing %s → %s", (state, side, inSwing, expected) => {
    expect(doorTarget(state, side, inSwing)).toBe(expected);
  });
});

/** Store with the eggs shelf laid out like the blockout (glTF coordinates). */
function storeRoot() {
  const root = new Group();
  const shelf = new Group();
  shelf.name = "SHELF_EGGS_ROOT";
  shelf.position.set(0, 0, -8.4);
  for (const [side, x] of [
    ["L", -1.5],
    ["R", 1.5],
  ] as const) {
    const hinge = new Object3D();
    hinge.name = `HINGE_EGGS_${side}`;
    hinge.position.x = x;
    const door = new Mesh(
      new BoxGeometry(1.5, 2.2, 0.6).translate(-Math.sign(x) * 0.75, 1.1, -0.3),
    );
    door.name = `DOOR_EGGS_${side}`;
    const col = new Mesh(door.geometry);
    col.name = `COL_DOOR_EGGS_${side}`;
    door.add(col);
    hinge.add(door);
    shelf.add(hinge);
  }
  const scan = new Mesh(new BoxGeometry(3, 2.2, 0.6).translate(0, 1.1, -0.3));
  scan.name = "SCAN_EGGS";
  const entry = new Mesh(new BoxGeometry(3, 2.2, 1.5).translate(0, 1.1, -0.75));
  entry.name = "TRIGGER_EGGS_ENTRY";
  const anchor = new Object3D();
  anchor.name = "ANCHOR_EGGS_TERRACE";
  anchor.position.z = -0.9;
  shelf.add(scan, entry, anchor);
  root.add(shelf);
  root.updateMatrixWorld(true);
  return root;
}

function setup(load: () => Promise<Object3D>) {
  const bus = new EventBus<GameEvents>();
  const game = new GameState(bus);
  const scene = new Scene();
  const collisions = new CollisionWorld();
  const root = storeRoot();
  scene.add(root);
  collisions.addFrom(root);
  let position: Vec2 = { x: 0, z: -4 };
  const alerts: string[] = [];
  const transition = new TerraceTransition({
    game,
    bus,
    scene,
    collisions,
    storeRoot: root,
    assets: { load } as unknown as AssetManager,
    chains: { eggs: { ...eggs, terrace: {} as AssetContract } },
    player: {
      radius: 0.3,
      position: () => position,
      teleport: (p) => (position = p),
    },
    hud: { setHint: () => {}, alert: (text) => alerts.push(text) },
  });
  const walkTo = (p: Vec2) => {
    position = p;
    transition.update(0.1);
  };
  const run = (seconds: number) => {
    for (let t = 0; t < seconds; t += 0.1) transition.update(0.1);
  };
  game.send({ type: "START" });
  return { game, scene, transition, walkTo, run, alerts, where: () => position };
}

const flush = () => new Promise((resolve) => setTimeout(resolve, 0));

describe("TerraceTransition", () => {
  it("plays scan → opening → terrace → return → store, leaving no module behind", async () => {
    const module = new Group();
    module.name = "TERRACE_EGGS_ROOT";
    const { game, scene, walkTo, run } = setup(async () => module);

    game.send({ type: "SCAN_CONFIRMED", chainId: "eggs" });
    await flush();
    expect(game.snapshot.state).toBe("OPENING");
    expect(module.parent).toBe(scene);
    expect(module.position.z).toBeCloseTo(-9.3);

    walkTo({ x: -1, z: -7.5 }); // in the sweep: the doors wait
    run(5);
    expect(game.snapshot.state).toBe("OPENING");
    walkTo({ x: 0, z: -4 });
    run(3);
    expect(game.snapshot.state).toBe("TERRACE");

    walkTo({ x: 0, z: -12 });
    walkTo({ x: 0, z: -7.8 });
    expect(game.snapshot.state).toBe("RETURN");
    run(5); // still in the sweep: doors stay open
    expect(game.snapshot.state).toBe("RETURN");
    walkTo({ x: 0, z: -4 });
    run(3);
    expect(game.snapshot).toEqual({ state: "STORE", activeChain: null });
    expect(module.parent).toBeNull();
  });

  it("reopens when the player turns back towards the terrace during the return", async () => {
    const { game, walkTo, run } = setup(async () => new Group());
    game.send({ type: "SCAN_CONFIRMED", chainId: "eggs" });
    await flush();
    run(3);
    walkTo({ x: 0, z: -12 });
    walkTo({ x: 0, z: -4 });
    run(1);
    walkTo({ x: 0, z: -12 });
    expect(game.snapshot.state).toBe("TERRACE");
  });

  it("recovers to the store with a message when the module fails to load", async () => {
    const { game, alerts } = setup(() => Promise.reject(new Error("404")));
    game.send({ type: "SCAN_CONFIRMED", chainId: "eggs" });
    await flush();
    await flush();
    expect(game.snapshot).toEqual({ state: "STORE", activeChain: null });
    expect(alerts).toEqual(["La filière n'a pas pu être chargée. Retour au magasin."]);
  });

  it("recovers when a loaded module cannot be staged", async () => {
    const { game, transition, alerts, scene } = setup(async () => new Group());
    transition.onModuleChange = (_, root) => {
      if (root) throw new Error("ANCHOR absent");
    };
    game.send({ type: "SCAN_CONFIRMED", chainId: "eggs" });
    await flush();
    await flush();
    expect(game.snapshot).toEqual({ state: "STORE", activeChain: null });
    expect(alerts).toEqual(["La filière n'a pas pu être préparée. Retour au magasin."]);
    expect(scene.children.filter((c) => c.type === "Group")).toHaveLength(1);
  });

  it("brings the player back in front of the shelf on a manual return", async () => {
    const { game, transition, walkTo, run, where } = setup(async () => new Group());
    game.send({ type: "SCAN_CONFIRMED", chainId: "eggs" });
    await flush();
    run(3);
    walkTo({ x: 0, z: -14 });
    transition.returnToStore();
    expect(where()).toEqual({ x: 0, z: expect.closeTo(-8.4 + 2.5) });
    run(3);
    expect(game.snapshot.state).toBe("STORE");
  });
});
