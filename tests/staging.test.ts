import { Group, Mesh, BoxGeometry, MeshStandardMaterial, Object3D, PerspectiveCamera, Vector3 } from "three";
import { describe, expect, it } from "vitest";
import { EventBus } from "../src/core/EventBus";
import { GameState, type GameEvents } from "../src/core/GameState";
import { beef } from "../src/data/chains/beef";
import { eggs } from "../src/data/chains/eggs";
import { ROOF_SECONDS } from "../src/features/chains/RoofReveal";
import { TerraceStage } from "../src/features/chains/TerraceStage";
import { captionById } from "../src/features/chains/ChainModule";
import { SHORT_MAX } from "../src/features/content/types";
import { declutter, projectToScreen, type MarkerItem } from "../src/ui/StageMarkers";
import { Atmosphere } from "../src/world/Atmosphere";

function terrace() {
  const root = new Group();
  root.name = "TERRACE_EGGS_ROOT";
  const node = (name: string, x: number, y: number, z: number) => {
    const o = new Object3D();
    o.name = name;
    o.position.set(x, y, z);
    root.add(o);
  };
  node("ANCHOR_EGGS_VIEW", 0, 0, -6.2);
  node("ANCHOR_EGGS_FOCUS", 0, -13, -40);
  node("ANCHOR_EGGS_WIDE", 0, -22, -84);
  node("ANCHOR_EGGS_MARK_CAGES", -14, -9, -34);
  node("ANCHOR_EGGS_MARK_SITE", -24, -5, -106);
  node("HENS_EGGS", 0, 0, 0);
  const roof = new Mesh(new BoxGeometry(1, 1, 1), new MeshStandardMaterial());
  roof.name = "ROOF_EGGS";
  root.add(roof);
  root.updateMatrixWorld(true);
  return root;
}

function setup(reducedMotion = false) {
  const bus = new EventBus<GameEvents>();
  const game = new GameState(bus);
  const glances: { target: Vector3; seconds?: number }[] = [];
  const markers: (readonly MarkerItem[])[] = [];
  const mood: number[] = [];
  const stage = new TerraceStage({
    game,
    bus,
    player: { position: () => ({ x: 0.5, z: -6.2 }) },
    hud: { setHint: () => {}, showCaption: () => {} },
    reducedMotion: () => reducedMotion,
    glance: (target, seconds) => glances.push({ target, seconds }),
    markers: { set: (items) => markers.push(items) },
    mood: (amount) => mood.push(amount),
  });
  stage.attach({ ...eggs, timeline: [] }, terrace());
  for (const type of ["START", "MODULE_READY", "DOORS_OPEN"] as const) {
    if (type === "MODULE_READY") game.send({ type: "SCAN_CONFIRMED", chainId: "eggs" });
    game.send({ type });
  }
  return { game, stage, glances, markers, mood };
}

describe("reveal staging", () => {
  it("warms to the industrial mood on reveal, frames the whole site, then shows the markers", () => {
    const { stage, glances, markers, mood } = setup();
    stage.update(0.1); // at the viewpoint: REVEAL
    expect(mood.at(-1)).toBe(1);
    for (let t = 0; t < ROOF_SECONDS + 0.2; t += 0.1) stage.update(0.1);
    expect(glances).toHaveLength(2);
    expect(glances[1]!.target.z).toBeCloseTo(-84);
    expect(glances[1]!.seconds).toBeGreaterThan(glances[0]!.seconds ?? 0);
    const shown = markers.find((items) => items.length > 0)!;
    expect(shown.map((item) => item.caption.id)).toEqual(["eggs.system", "eggs.site"]);
    stage.detach();
    expect(markers.at(-1)).toEqual([]);
    expect(mood.at(-1)).toBe(0);
  });

  it("keeps the markers but skips the wide framing under reduced motion", () => {
    const { stage, glances, markers } = setup(true);
    for (let t = 0; t < ROOF_SECONDS + 0.4; t += 0.1) stage.update(0.1);
    expect(glances).toEqual([]);
    expect(markers.some((items) => items.length === 2)).toBe(true);
  });
});

describe("marker content", () => {
  it.each([eggs, beef])("$id markers cite existing, short captions", (config) => {
    expect(config.markers?.length).toBeGreaterThan(0);
    for (const { captionId, anchor } of config.markers ?? []) {
      const caption = captionById(config, captionId);
      expect(caption.short.length).toBeLessThanOrEqual(SHORT_MAX);
      expect(anchor.startsWith(`ANCHOR_${config.id.toUpperCase()}_MARK_`)).toBe(true);
    }
  });

  it("projects points in front of the camera and drops the ones behind", () => {
    const camera = new PerspectiveCamera(70, 1.5, 0.1, 500);
    camera.updateMatrixWorld(true);
    const ahead = projectToScreen(new Vector3(0, 0, -10), camera)!;
    expect(ahead.x).toBeCloseTo(0.5);
    expect(ahead.y).toBeCloseTo(0.5);
    expect(projectToScreen(new Vector3(0, 0, 10), camera)).toBeNull();
    expect(projectToScreen(new Vector3(100, 0, -10), camera)).toBeNull();
  });
});

describe("marker layout", () => {
  const box = (x: number, y: number) => ({ x, y, width: 200, height: 120 });

  it("lifts the upper label clear of the lower one and leaves distant ones alone", () => {
    const [upper, lower] = declutter([box(500, 600), box(450, 745)]);
    expect(lower).toBe(0);
    // Its bottom edge now sits above the lower label's top edge (745 - 120), with a gap.
    expect(600 - upper!).toBeLessThanOrEqual(745 - 120 - 8);
    expect(declutter([box(100, 300), box(700, 320)])).toEqual([0, 0]);
  });
});

describe("Atmosphere mood", () => {
  it("cools the outdoor light progressively and returns to natural light", () => {
    const renderer = { shadowMap: {}, toneMappingExposure: 1 } as never;
    const scene = { add: () => {} } as never;
    const atmosphere = new Atmosphere(scene, renderer);
    for (let i = 0; i < 100; i++) atmosphere.update(0.1, 1);
    const sun = (atmosphere as unknown as { sun: { intensity: number } }).sun;
    const natural = sun.intensity;
    atmosphere.setMood(1);
    atmosphere.update(0.1, 1);
    expect(atmosphere.mood).toBeGreaterThan(0);
    expect(atmosphere.mood).toBeLessThan(0.2);
    for (let i = 0; i < 100; i++) atmosphere.update(0.1, 1);
    expect(sun.intensity).toBeLessThan(natural);
    atmosphere.setMood(0);
    for (let i = 0; i < 200; i++) atmosphere.update(0.1, 1);
    expect(sun.intensity).toBeCloseTo(natural, 2);
  });
});
