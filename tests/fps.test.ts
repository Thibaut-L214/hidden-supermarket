import { describe, expect, it } from "vitest";
import { applyLook, walkDelta, type Direction } from "../src/world/FPSController";

const held = (...d: Direction[]) => new Set(d);

describe("walkDelta", () => {
  it("walks towards -Z at yaw 0", () => {
    const d = walkDelta(held("forward"), 0, 2, 0.5);
    expect(d.x).toBeCloseTo(0);
    expect(d.z).toBeCloseTo(-1);
  });

  it("strafes right towards +X at yaw 0", () => {
    const d = walkDelta(held("right"), 0, 2, 0.5);
    expect(d.x).toBeCloseTo(1);
    expect(d.z).toBeCloseTo(0);
  });

  it("follows the yaw: a quarter turn left walks towards -X", () => {
    const d = walkDelta(held("forward"), Math.PI / 2, 1, 1);
    expect(d.x).toBeCloseTo(-1);
    expect(d.z).toBeCloseTo(0);
  });

  it("is not faster on diagonals", () => {
    const d = walkDelta(held("forward", "left"), 0, 2, 1);
    expect(Math.hypot(d.x, d.z)).toBeCloseTo(2);
  });

  it("stands still when opposite keys cancel out or time is frozen", () => {
    expect(walkDelta(held("forward", "back"), 0, 2, 1)).toEqual({ x: 0, z: 0 });
    expect(walkDelta(held("forward"), 0, 2, 0)).toEqual({ x: 0, z: 0 });
  });
});

describe("applyLook", () => {
  it("turns right when the mouse moves right and looks up when it moves up", () => {
    const view = applyLook({ yaw: 0, pitch: 0 }, 100, -50, 0.002);
    expect(view.yaw).toBeCloseTo(-0.2);
    expect(view.pitch).toBeCloseTo(0.1);
  });

  it("clamps the pitch short of the vertical", () => {
    const view = applyLook({ yaw: 0, pitch: 0 }, 0, -100000, 0.002);
    expect(view.pitch).toBeCloseTo((85 * Math.PI) / 180);
  });
});
