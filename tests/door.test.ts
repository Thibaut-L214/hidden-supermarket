import { BoxGeometry, Group, Mesh, Object3D, Vector3 } from "three";
import { describe, expect, it } from "vitest";
import { DOOR_SECONDS, ShelfDoor, inSwingZone } from "../src/features/portal/ShelfDoor";

/** Same layout as the store blockout: shelf front at z = -8.4, store towards +Z. */
function shelf() {
  const root = new Group();
  root.name = "SHELF_EGGS_ROOT";
  root.position.set(0, 0, -8.4);
  for (const [side, x] of [
    ["L", -1.5],
    ["R", 1.5],
  ] as const) {
    const hinge = new Object3D();
    hinge.name = `HINGE_EGGS_${side}`;
    hinge.position.set(x, 0, 0);
    const door = new Mesh(
      new BoxGeometry(1.5, 2.2, 0.6).translate(-Math.sign(x) * 0.75, 1.1, -0.3),
    );
    door.name = `DOOR_EGGS_${side}`;
    hinge.add(door);
    root.add(hinge);
  }
  const scan = new Mesh(new BoxGeometry(3, 2.2, 0.6));
  scan.name = "SCAN_EGGS";
  scan.position.set(0, 1.1, -0.3);
  root.add(scan);
  return root;
}

/** World position of the door's free edge (the corner that was at the shelf centre). */
function freeEdge(root: Group, side: "L" | "R"): Vector3 {
  root.updateMatrixWorld(true);
  const door = root.getObjectByName(`DOOR_EGGS_${side}`)!;
  return door.localToWorld(new Vector3(side === "L" ? 1.5 : -1.5, 0, 0));
}

describe("ShelfDoor", () => {
  it("derives the swing geometry from the GLB nodes", () => {
    const door = new ShelfDoor(shelf(), "eggs");
    expect(door.geometry.hinges).toEqual([
      { x: -1.5, z: -8.4 },
      { x: 1.5, z: -8.4 },
    ]);
    expect(door.geometry.storeNormal.z).toBeCloseTo(1);
    expect(door.geometry.width).toBeCloseTo(1.5);
    expect(door.geometry.depth).toBeCloseTo(0.6);
  });

  it("swings both leaves towards the store in DOOR_SECONDS", () => {
    const root = shelf();
    const door = new ShelfDoor(root, "eggs");
    door.update(DOOR_SECONDS / 2, "open");
    expect(door.isOpen).toBe(false);
    door.update(DOOR_SECONDS / 2, "open");
    expect(door.isOpen).toBe(true);
    for (const side of ["L", "R"] as const) {
      const edge = freeEdge(root, side);
      expect(edge.z).toBeCloseTo(-8.4 + 1.5);
      expect(Math.abs(edge.x)).toBeCloseTo(1.5);
    }
  });

  it("holds its pose on demand and replays without drift", () => {
    const root = shelf();
    const door = new ShelfDoor(root, "eggs");
    const left = root.getObjectByName("DOOR_EGGS_L")!;
    door.update(1, "open");
    expect(door.update(1, "hold")).toBe(false);
    for (let i = 0; i < 50; i++) {
      door.update(0.37, i % 2 ? "closed" : "open");
    }
    door.update(DOOR_SECONDS, "closed");
    expect(door.isClosed).toBe(true);
    expect(left.quaternion.toArray()).toEqual([0, 0, 0, 1]);
  });
});

describe("inSwingZone", () => {
  const g = new ShelfDoor(shelf(), "eggs").geometry;

  it.each([
    ["in front of a hinge", { x: -1.2, z: -7.5 }, true],
    ["in the doorway between the walls", { x: 0, z: -9 }, true],
    ["back in the aisle", { x: 0, z: -5.5 }, false],
    ["on the terrace past the wall", { x: 0, z: -10.5 }, false],
  ])("%s → %s", (_, p, expected) => {
    expect(inSwingZone(p, g, 0.3)).toBe(expected);
  });
});
