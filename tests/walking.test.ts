import { Group, Object3D, Vector3 } from "three";
import { describe, expect, it } from "vitest";
import { ChainTimeline } from "../src/features/chains/ChainTimeline";
import type { TimelineStep } from "../src/features/chains/ChainModule";
import { evaluate } from "../src/features/chains/TimelineDirector";

const steps: TimelineStep[] = [
  {
    id: "load",
    event: "walk",
    durationSec: 10,
    captionId: "load",
    from: "FARM",
    to: "CATTLE",
    pathId: "RAMP",
  },
];

function scene() {
  const root = new Group();
  root.position.set(5, -12, -9);
  const farm = new Group();
  farm.name = "FARM";
  const truck = new Group();
  truck.position.set(10, 1, -10);
  const cattle = new Group();
  cattle.name = "CATTLE";
  for (let i = 0; i < 3; i++) {
    const source = new Group();
    source.position.set(i * 2, 0, 0);
    const target = new Group();
    target.position.set(0, 0, i === 0 ? 0 : -i * 2);
    const leg = new Object3D();
    leg.name = `CATTLE_LEG_${i}`;
    target.add(leg);
    farm.add(source);
    cattle.add(target);
  }
  truck.add(cattle);
  root.add(farm, truck);
  [
    [0, 0, -5],
    [0, 1, -10],
  ].forEach(([x, y, z], i) => {
    const point = new Object3D();
    point.name = `RAMP_0${i}`;
    point.position.set(x!, y!, z!);
    root.add(point);
  });
  root.updateMatrixWorld(true);
  return { root, farm, cattle, truck };
}

describe("walking animals", () => {
  it("follows the ground corridor and ramp before entering the truck, with a staggered departure", () => {
    const { root, farm, cattle } = scene();
    const timeline = new ChainTimeline(root, steps);
    timeline.apply(evaluate(steps, 0.5));
    root.updateMatrixWorld(true);
    const first = root.worldToLocal(cattle.children[0]!.getWorldPosition(new Vector3()));
    expect(first.x).toBeCloseTo(0);
    expect(first.y).toBeCloseTo(0);
    expect(first.z).toBeLessThan(0);
    expect(first.z).toBeGreaterThan(-5);
    expect(farm.children[0]!.visible).toBe(false);
    expect(cattle.children[0]!.visible).toBe(true);
    expect(farm.children[2]!.visible).toBe(true);
    expect(cattle.children[2]!.visible).toBe(false);
  });

  it("restores positions, headings, legs and visibility on replay and after revisiting", () => {
    const { root, farm, cattle } = scene();
    const timeline = new ChainTimeline(root, steps);
    timeline.apply(evaluate(steps, 1));
    const pose = cattle.children[0]!.position.toArray();
    timeline.apply(evaluate(steps, 10));
    expect(farm.children.every((animal) => !animal.visible)).toBe(true);
    expect(cattle.children.every((animal) => animal.visible)).toBe(true);
    timeline.apply(null);
    expect(farm.children.every((animal) => animal.visible)).toBe(true);
    expect(cattle.children.every((animal) => !animal.visible)).toBe(true);
    expect(cattle.children[0]!.position.toArray()).toEqual([0, 0, 0]);
    expect(cattle.children[0]!.rotation.y).toBe(0);
    expect(cattle.children[0]!.children[0]!.rotation.x).toBe(0);
    timeline.apply(evaluate(steps, 1));
    expect(cattle.children[0]!.position.toArray()).toEqual(pose);
  });

  it("uses the truck's arrival position for unloading, even when time jumps forward", () => {
    const { root, cattle, truck } = scene();
    truck.name = "TRUCK";
    const waiting = new Group();
    waiting.name = "WAITING";
    for (let i = 0; i < 3; i++) {
      const animal = new Group();
      animal.position.set(30 + i * 2, 0, -20);
      waiting.add(animal);
    }
    root.add(waiting);
    [
      [10, 1, -10],
      [20, 1, -10],
    ].forEach(([x, y, z], i) => {
      const point = new Object3D();
      point.name = `ROAD_0${i}`;
      point.position.set(x!, y!, z!);
      root.add(point);
    });
    const route: TimelineStep[] = [
      steps[0]!,
      {
        id: "drive",
        event: "drive",
        durationSec: 10,
        captionId: "drive",
        vehicle: "TRUCK",
        pathId: "ROAD",
      },
      {
        id: "unload",
        event: "walk",
        durationSec: 10,
        captionId: "unload",
        from: "CATTLE",
        to: "WAITING",
        pathId: "RAMP",
      },
    ];
    const timeline = new ChainTimeline(root, route);
    timeline.apply(evaluate(route, 20.01));
    root.updateMatrixWorld(true);
    const first = root.worldToLocal(waiting.children[0]!.getWorldPosition(new Vector3()));
    expect(first.x).toBeCloseTo(20, 0);
    expect(first.y).toBeCloseTo(1, 0);
    expect(first.z).toBeCloseTo(-10, 0);
    expect(cattle.children[0]!.visible).toBe(false);
  });

  it("disables the gait under reduced motion while preserving the route", () => {
    const { root, cattle } = scene();
    const timeline = new ChainTimeline(root, steps, () => true);
    timeline.apply(evaluate(steps, 1));
    expect(cattle.children[0]!.children[0]!.rotation.x).toBe(0);
    expect(cattle.children[0]!.visible).toBe(true);
  });

  it("rejects a missing route instead of silently teleporting the animals", () => {
    const { root } = scene();
    expect(() => new ChainTimeline(root, [{ ...steps[0]!, pathId: "MISSING" }])).toThrow(/MISSING/);
  });
});
