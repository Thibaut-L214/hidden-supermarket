import { describe, expect, it } from "vitest";
import { environmentBlend } from "../src/world/Atmosphere";

describe("environmentBlend", () => {
  it("uses the store panorama at full strength inside", () => {
    expect(environmentBlend(0)).toEqual({ outdoor: false, weight: 1 });
  });

  it("uses the terrace sky at full strength outside", () => {
    expect(environmentBlend(1)).toEqual({ outdoor: true, weight: 1 });
  });

  it("swaps at the midpoint, where the intensity is lowest but never black", () => {
    const before = environmentBlend(0.49);
    const after = environmentBlend(0.5);
    expect(before.outdoor).toBe(false);
    expect(after.outdoor).toBe(true);
    expect(after.weight).toBeGreaterThan(0.3);
    expect(after.weight).toBeLessThan(0.45);
  });

  it("clamps out-of-range blends", () => {
    expect(environmentBlend(-1)).toEqual(environmentBlend(0));
    expect(environmentBlend(2)).toEqual(environmentBlend(1));
  });
});
