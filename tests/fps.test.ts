import { describe, expect, it } from "vitest";
import {
  KEY_BINDINGS,
  applyLook,
  blendView,
  turnDelta,
  viewToward,
  walkDelta,
  type Control,
} from "../src/world/FPSController";

const held = (...d: Control[]) => new Set(d);

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

describe("viewToward", () => {
  it("looks straight ahead along -Z at yaw 0", () => {
    const view = viewToward({ x: 0, y: 1.6, z: 0 }, { x: 0, y: 1.6, z: -10 });
    expect(view.yaw).toBeCloseTo(0);
    expect(view.pitch).toBeCloseTo(0);
  });

  it("turns left towards -X and looks down at a lower point", () => {
    const view = viewToward({ x: 0, y: 10, z: 0 }, { x: -10, y: 0, z: 0 });
    expect(view.yaw).toBeCloseTo(Math.PI / 2);
    expect(view.pitch).toBeCloseTo(-Math.PI / 4);
  });
});

describe("blendView", () => {
  it("takes the shortest turn across ±π", () => {
    const mid = blendView({ yaw: 3, pitch: 0 }, { yaw: -3, pitch: 0 }, 0.5);
    expect(Math.abs(mid.yaw)).toBeGreaterThan(3);
  });
});

describe("keyboard turning", () => {
  it("binds ← / → to turning, ↑ / ↓ to walking, and keeps Q/D (A/D) for side steps", () => {
    expect(KEY_BINDINGS.ArrowLeft).toBe("turnLeft");
    expect(KEY_BINDINGS.ArrowRight).toBe("turnRight");
    expect(KEY_BINDINGS.ArrowUp).toBe("forward");
    expect(KEY_BINDINGS.ArrowDown).toBe("back");
    expect(KEY_BINDINGS.KeyA).toBe("left");
    expect(KEY_BINDINGS.KeyD).toBe("right");
  });

  it("turns left with a positive yaw change and right with a negative one", () => {
    expect(turnDelta(held("turnLeft"), 2, 0.5)).toBeCloseTo(1);
    expect(turnDelta(held("turnRight"), 2, 0.5)).toBeCloseTo(-1);
    expect(turnDelta(held("turnLeft", "turnRight"), 2, 0.5)).toBe(0);
    expect(turnDelta(held("turnLeft"), 2, 0)).toBe(0);
  });

  it("does not move the player when only turning", () => {
    expect(walkDelta(held("turnLeft"), 0, 2, 1)).toEqual({ x: 0, z: 0 });
  });
});
