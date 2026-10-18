import { BoxGeometry, Group, Mesh, Raycaster, Vector3 } from "three";
import { describe, expect, it } from "vitest";
import { findScanTargets } from "../src/features/scanner/ScanTarget";
import { HOLD_SECONDS, ScanInteraction, aimAt } from "../src/features/scanner/Scanner";

describe("ScanInteraction", () => {
  it("confirms after holding the click on a target", () => {
    const scan = new ScanInteraction();
    expect(scan.update("eggs", true, false, HOLD_SECONDS / 2)).toBeNull();
    expect(scan.progress).toBeCloseTo(0.5);
    expect(scan.update("eggs", true, false, HOLD_SECONDS / 2)).toBe("eggs");
  });

  it("confirms at once on E", () => {
    expect(new ScanInteraction().update("eggs", false, true, 0)).toBe("eggs");
  });

  it("activates only once per interaction", () => {
    const scan = new ScanInteraction();
    scan.update("eggs", true, false, HOLD_SECONDS);
    expect(scan.update("eggs", true, false, HOLD_SECONDS * 3)).toBeNull();
    scan.update("eggs", false, false, 0.016);
    expect(scan.update("eggs", true, false, HOLD_SECONDS)).toBe("eggs");
  });

  it("drops the progress when the aim leaves the shelf", () => {
    const scan = new ScanInteraction();
    scan.update("eggs", true, false, HOLD_SECONDS * 0.9);
    scan.update(null, true, false, 0.016);
    expect(scan.update("eggs", true, false, HOLD_SECONDS * 0.2)).toBeNull();
  });

  it("ignores a click still held after a reset", () => {
    const scan = new ScanInteraction();
    scan.reset();
    expect(scan.update("eggs", true, false, HOLD_SECONDS * 2)).toBeNull();
  });
});

describe("aimAt", () => {
  function store() {
    const root = new Group();
    const shelf = new Group();
    shelf.name = "SHELF_EGGS_ROOT";
    shelf.position.set(0, 0, -5);
    const scan = new Mesh(new BoxGeometry(3, 2, 0.6));
    scan.name = "SCAN_EGGS";
    scan.position.set(0, 1, 0);
    const door = new Mesh(new BoxGeometry(1.5, 2, 0.6));
    door.name = "COL_DOOR_EGGS_L";
    door.position.set(-0.75, 1, 0);
    shelf.add(scan, door);
    root.add(shelf);
    root.updateMatrixWorld(true);
    return { root, door };
  }

  function rayFrom(z: number) {
    const raycaster = new Raycaster(new Vector3(0, 1.6, z), new Vector3(0, 0, -1));
    raycaster.far = 4.5;
    return raycaster;
  }

  it("finds the shelf in range and ignores the shelf's own colliders", () => {
    const { root, door } = store();
    const targets = findScanTargets(root);
    expect(aimAt(rayFrom(-2), targets, [door])?.chainId).toBe("eggs");
  });

  it("returns nothing out of range", () => {
    const targets = findScanTargets(store().root);
    expect(aimAt(rayFrom(5), targets, [])).toBeNull();
  });

  it("is blocked by a collider standing in front of the shelf", () => {
    const { root } = store();
    const wall = new Mesh(new BoxGeometry(4, 3, 0.2));
    wall.name = "COL_GONDOLA";
    wall.position.set(0, 1, -3);
    root.add(wall);
    root.updateMatrixWorld(true);
    expect(aimAt(rayFrom(-1.5), findScanTargets(root), [wall])).toBeNull();
  });
});
