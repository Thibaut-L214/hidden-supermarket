import { BoxGeometry, Group, Mesh } from "three";
import { describe, expect, it } from "vitest";
import { CollisionWorld, moveCircle, pushOut, type Rect } from "../src/world/CollisionWorld";

const R = 0.3;
// A wall 0.2 m thick along x = 0 … 0.2, from z = -5 to z = 5.
const wall: Rect = { minX: 0, maxX: 0.2, minZ: -5, maxZ: 5 };

describe("pushOut", () => {
  it("ignores a circle that does not touch the rect", () => {
    expect(pushOut({ x: -0.5, z: 0 }, R, wall)).toBeNull();
  });

  it("pushes a grazing circle back along the contact normal", () => {
    const push = pushOut({ x: -0.2, z: 0 }, R, wall);
    expect(push?.x).toBeCloseTo(-0.1);
    expect(push?.z).toBeCloseTo(0);
  });

  it("evicts a centre inside the rect through the nearest side", () => {
    const push = pushOut({ x: 0.15, z: 0 }, R, wall);
    expect(push).toEqual({ x: expect.closeTo(0.35), z: 0 });
  });
});

describe("moveCircle", () => {
  it("stops against a wall", () => {
    const end = moveCircle({ x: -1, z: 0 }, { x: 2, z: 0 }, R, [wall]);
    expect(end.x).toBeCloseTo(-R);
  });

  it("slides along a wall when moving diagonally", () => {
    const end = moveCircle({ x: -0.5, z: 0 }, { x: 1, z: 1 }, R, [wall]);
    expect(end.x).toBeCloseTo(-R);
    expect(end.z).toBeCloseTo(1);
  });

  it("does not tunnel through a thin wall on a large step", () => {
    const end = moveCircle({ x: -1, z: 0 }, { x: 20, z: 0 }, R, [wall]);
    expect(end.x).toBeLessThan(0);
  });

  it("settles in a corner between two walls", () => {
    const back: Rect = { minX: -5, maxX: 0.2, minZ: 0, maxZ: 0.2 };
    const end = moveCircle({ x: -1, z: -1 }, { x: 2, z: 2 }, R, [wall, back]);
    expect(end.x).toBeCloseTo(-R);
    expect(end.z).toBeCloseTo(-R);
  });
});

describe("CollisionWorld", () => {
  function scene() {
    const root = new Group();
    const col = new Mesh(new BoxGeometry(2, 2, 2));
    col.name = "COL_BLOCK";
    col.position.set(5, 1, 0);
    const overhead = new Mesh(new BoxGeometry(2, 0.2, 2));
    overhead.name = "COL_LINTEL";
    overhead.position.set(0, 3, 0);
    const decor = new Mesh(new BoxGeometry(1, 1, 1));
    decor.name = "SHELF";
    root.add(col, overhead, decor);
    return { root, col };
  }

  it("keeps only COL_* footprints that overlap the player's height", () => {
    const world = new CollisionWorld();
    world.addFrom(scene().root);
    expect(world.rects).toEqual([{ minX: 4, maxX: 6, minZ: -1, maxZ: 1 }]);
  });

  it("follows a collider after refresh and forgets removed modules", () => {
    const { root, col } = scene();
    const world = new CollisionWorld();
    world.addFrom(root);
    col.position.x = 10;
    world.refresh();
    expect(world.rects[0]?.minX).toBe(9);
    world.removeFrom(root);
    expect(world.rects).toEqual([]);
  });
});
