import { BoxGeometry, Group, Mesh, Object3D } from "three";
import { describe, expect, it } from "vitest";
import type { TimelineStep } from "../src/features/chains/ChainModule";
import { ChainTimeline, pathPoints, unitsShown } from "../src/features/chains/ChainTimeline";
import { TimelineDirector, evaluate } from "../src/features/chains/TimelineDirector";

const steps: TimelineStep[] = [
  { id: "collect", event: "collect", durationSec: 2, captionId: "c", to: "CRATES" },
  { id: "load", event: "load", durationSec: 2, captionId: "c", from: "CRATES", to: "CARGO" },
  {
    id: "drive",
    event: "drive",
    durationSec: 4,
    captionId: "d",
    vehicle: "TRUCK",
    pathId: "PATH_T",
  },
  { id: "deliver", event: "deliver", durationSec: 2, captionId: "d", from: "CARGO" },
];

describe("evaluate", () => {
  it("reports per-step progress, the active step and completion", () => {
    expect(evaluate(steps, 0)).toEqual({ progress: [0, 0, 0, 0], active: 0, done: false });
    expect(evaluate(steps, 5)).toEqual({ progress: [1, 1, 0.25, 0], active: 2, done: false });
    expect(evaluate(steps, 10)).toEqual({ progress: [1, 1, 1, 1], active: 3, done: true });
  });
});

describe("TimelineDirector", () => {
  it("advances with game time only, stops at the end and restarts from zero", () => {
    const director = new TimelineDirector(steps);
    director.update(3);
    director.update(0);
    expect(director.elapsed).toBe(3);
    expect(director.update(100).done).toBe(true);
    expect(director.elapsed).toBe(10);
    director.restart();
    expect(director.state.progress).toEqual([0, 0, 0, 0]);
  });
});

describe("unitsShown", () => {
  it("rounds and clamps", () => {
    expect(unitsShown(6, 0.5)).toBe(3);
    expect(unitsShown(6, 1.4)).toBe(6);
    expect(unitsShown(6, -1)).toBe(0);
  });
});

function module() {
  const root = new Group();
  const group = (name: string, count: number, parent: Object3D) => {
    const g = new Group();
    g.name = name;
    for (let i = 0; i < count; i++) g.add(new Mesh(new BoxGeometry()));
    parent.add(g);
    return g;
  };
  group("CRATES", 4, root);
  const truck = new Group();
  truck.name = "TRUCK";
  root.add(truck);
  group("CARGO", 4, truck);
  // Path along -Z then turning towards +X.
  [
    [0, 0, 0],
    [0, 0, -10],
    [10, 0, -20],
  ].forEach(([x, y, z], i) => {
    const point = new Object3D();
    point.name = `PATH_T_0${i}`;
    point.position.set(x!, y!, z!);
    root.add(point);
  });
  root.updateMatrixWorld(true);
  return { root, truck };
}

const visible = (root: Object3D, name: string) =>
  root.getObjectByName(name)!.children.filter((c) => c.visible).length;

describe("ChainTimeline", () => {
  it("reads paths in index order", () => {
    expect(pathPoints(module().root, "PATH_T").map((p) => p.z)).toEqual([0, -10, -20]);
  });

  it("finds path points nested under the GLB scene wrapper, in the vehicle's frame", () => {
    // GLTFLoader returns a scene whose child is the module root, itself offset here.
    const { root, truck } = module();
    const wrapper = new Group();
    root.position.set(5, 0, -9);
    wrapper.add(root);
    const timeline = new ChainTimeline(wrapper, steps);
    timeline.apply(evaluate(steps, 8));
    expect(truck.position.x).toBeCloseTo(10);
    expect(truck.position.z).toBeCloseTo(-20);
  });

  it("starts with empty groups and the vehicle at the start of its path, facing along it", () => {
    const { root, truck } = module();
    new ChainTimeline(root, steps);
    expect(visible(root, "CRATES")).toBe(0);
    expect(visible(root, "CARGO")).toBe(0);
    expect(truck.position.toArray()).toEqual([0, 0, 0]);
    expect(truck.rotation.y).toBeCloseTo(0);
  });

  it("moves units between groups and drives the vehicle to the end of its path", () => {
    const { root, truck } = module();
    const timeline = new ChainTimeline(root, steps);
    timeline.apply(evaluate(steps, 3));
    expect([visible(root, "CRATES"), visible(root, "CARGO")]).toEqual([2, 2]);
    timeline.apply(evaluate(steps, 8));
    expect(truck.position.x).toBeCloseTo(10);
    expect(truck.position.z).toBeCloseTo(-20);
    expect(visible(root, "CARGO")).toBe(4);
    timeline.apply(evaluate(steps, 10));
    expect(visible(root, "CARGO")).toBe(0);
  });

  it("gives the same pose for a time whatever was shown before (replay)", () => {
    const fresh = module();
    new ChainTimeline(fresh.root, steps).apply(evaluate(steps, 6));

    const replayed = module();
    const timeline = new ChainTimeline(replayed.root, steps);
    timeline.apply(evaluate(steps, 10));
    timeline.apply(evaluate(steps, 1));
    timeline.apply(evaluate(steps, 6));

    expect(replayed.truck.position.toArray()).toEqual(fresh.truck.position.toArray());
    expect(replayed.truck.rotation.y).toBe(fresh.truck.rotation.y);
    expect(visible(replayed.root, "CARGO")).toBe(visible(fresh.root, "CARGO"));
  });

  it("does not add a guide cone above timeline targets", () => {
    const { root } = module();
    new ChainTimeline(root, steps).apply(evaluate(steps, 6));
    expect(root.getObjectByName("TIMELINE_MARKER")).toBeUndefined();
  });
});

describe("ChainTimeline, carry steps", () => {
  const carry: TimelineStep[] = [
    { id: "load", event: "load", durationSec: 10, captionId: "c", from: "HALL", to: "TRUCK", carry: true },
  ];

  /** Two groups of unit meshes whose geometry sits at its slot, origins at the group's. */
  function slots() {
    const root = new Group();
    const make = (name: string, x: number) => {
      const g = new Group();
      g.name = name;
      g.position.x = 0;
      for (let i = 0; i < 3; i++) {
        // Geometry offset by the slot, object left at its origin: like the Blender units.
        const mesh = new Mesh(new BoxGeometry(0.2, 0.2, 0.2).translate(x, 0, i));
        g.add(mesh);
      }
      root.add(g);
      return g;
    };
    make("HALL", 0);
    make("TRUCK", 10);
    root.updateMatrixWorld(true);
    return root;
  }

  const unit = (root: Object3D, group: string, i: number) => root.getObjectByName(group)!.children[i]!;

  it("shows every unit in the hall before, and in the truck after, each at its own slot", () => {
    const root = slots();
    const timeline = new ChainTimeline(root, carry);
    timeline.apply(evaluate(carry, 0));
    expect([visible(root, "HALL"), visible(root, "TRUCK")]).toEqual([3, 0]);
    timeline.apply(evaluate(carry, 10));
    expect([visible(root, "HALL"), visible(root, "TRUCK")]).toEqual([0, 3]);
    for (let i = 0; i < 3; i++) expect(unit(root, "TRUCK", i).position.toArray()).toEqual([0, 0, 0]);
  });

  it("moves the units one after another, between the two slots, on an arc", () => {
    const root = slots();
    const timeline = new ChainTimeline(root, carry);
    // First unit is under way and the last has not left yet.
    timeline.apply(evaluate(carry, 1));
    const first = unit(root, "TRUCK", 0);
    expect(unit(root, "HALL", 0).visible).toBe(false);
    expect(first.visible).toBe(true);
    expect(first.position.x).toBeLessThan(0); // still near the hall (slot 10 minus the offset)
    expect(first.position.x).toBeGreaterThan(-10);
    expect(unit(root, "HALL", 2).visible).toBe(true);
    expect(unit(root, "TRUCK", 2).visible).toBe(false);
    timeline.apply(evaluate(carry, 5));
    expect(unit(root, "TRUCK", 0).position.toArray()).toEqual([0, 0, 0]);
  });

  it("restores rest positions when time goes back (replay)", () => {
    const root = slots();
    const timeline = new ChainTimeline(root, carry);
    timeline.apply(evaluate(carry, 2));
    timeline.apply(evaluate(carry, 0));
    for (let i = 0; i < 3; i++) expect(unit(root, "TRUCK", i).position.toArray()).toEqual([0, 0, 0]);
    expect(visible(root, "TRUCK")).toBe(0);
  });
});
