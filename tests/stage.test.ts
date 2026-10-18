import { BoxGeometry, Group, Mesh, MeshStandardMaterial, Object3D, Vector3 } from "three";
import { describe, expect, it } from "vitest";
import { EventBus } from "../src/core/EventBus";
import { GameState, type GameEvents } from "../src/core/GameState";
import { eggs } from "../src/data/chains/eggs";
import { ROOF_SECONDS } from "../src/features/chains/RoofReveal";
import { TerraceStage } from "../src/features/chains/TerraceStage";
import type { Caption } from "../src/features/content/types";
import type { Vec2 } from "../src/world/CollisionWorld";

/** Terrace module placed like the blockout: threshold at z = -9.3, terrace towards -Z. */
function module() {
  const root = new Group();
  root.name = "TERRACE_EGGS_ROOT";
  root.position.z = -9.3;
  const view = new Object3D();
  view.name = "ANCHOR_EGGS_VIEW";
  view.position.z = -6.2;
  const focus = new Object3D();
  focus.name = "ANCHOR_EGGS_FOCUS";
  focus.position.set(0, -13, -40);
  const roof = new Mesh(new BoxGeometry(70, 0.5, 16), new MeshStandardMaterial());
  roof.name = "ROOF_EGGS";
  roof.position.set(0, -8.75, -40);
  root.add(view, focus, roof);
  root.updateMatrixWorld(true);
  return { root, roof };
}

function setup(reducedMotion = false) {
  const bus = new EventBus<GameEvents>();
  const game = new GameState(bus);
  let position: Vec2 = { x: 0, z: -7 };
  const captions: (string | null)[] = [];
  const glances: Vector3[] = [];
  const stage = new TerraceStage({
    game,
    bus,
    player: { position: () => position },
    hud: {
      setHint: () => {},
      showCaption: (c: Caption | null) => captions.push(c?.id ?? null),
    },
    reducedMotion: () => reducedMotion,
    glance: (target) => glances.push(target),
  });
  const { root, roof } = module();
  // Timeline objects are covered by tests/timeline.test.ts; this module has none.
  stage.attach({ ...eggs, timeline: [] }, root);
  for (const type of ["START", "MODULE_READY", "DOORS_OPEN"] as const) {
    if (type === "MODULE_READY") game.send({ type: "SCAN_CONFIRMED", chainId: "eggs" });
    game.send({ type });
  }
  const at = (p: Vec2) => {
    position = p;
    stage.update(0.1);
  };
  return { game, stage, roof, captions, glances, at };
}

describe("TerraceStage", () => {
  it("welcomes once on the terrace, then reveals the roof from the viewpoint", () => {
    const { game, stage, roof, captions, glances, at } = setup();
    at({ x: 0, z: -7 }); // still in the store
    expect(captions).toEqual([]);
    at({ x: 0, z: -11 });
    at({ x: 0, z: -12 });
    expect(captions).toEqual(["eggs.terrace"]);

    at({ x: 0.5, z: -15.6 });
    expect(game.snapshot.state).toBe("REVEAL");
    expect(captions).toEqual(["eggs.terrace", "eggs.system"]);
    expect(glances).toHaveLength(1);

    for (let t = 0; t < ROOF_SECONDS + 0.2; t += 0.1) stage.update(0.1);
    // An empty timeline finishes at once: the chain reaches the recap.
    expect(game.snapshot.state).toBe("RECAP");
    expect(roof.visible).toBe(false);
  });

  it("skips the framing glance under reduced motion", () => {
    const { game, glances, at } = setup(true);
    at({ x: 0, z: -15.6 });
    expect(game.snapshot.state).toBe("REVEAL");
    expect(glances).toEqual([]);
  });

  it("closes the roof again when the module is detached", () => {
    const { stage, roof, at } = setup();
    at({ x: 0, z: -15.6 });
    for (let t = 0; t < ROOF_SECONDS + 0.2; t += 0.1) stage.update(0.1);
    stage.detach();
    expect(roof.visible).toBe(true);
    expect(roof.position.y).toBe(-8.75);
  });
});
