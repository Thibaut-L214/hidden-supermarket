import { Vector3 } from "three";
import { describe, expect, it } from "vitest";
import { GRADES, gradeFor } from "../src/app/grade";
import { seeded } from "../src/world/Ambience";
import { mirrorPoint } from "../src/world/FloorReflection";
import { HEIGHT_FOG, heightFogAmount } from "../src/world/heightFog";
import { FX_UNIFORMS, fxOptionsFor, updateWorldFx } from "../src/world/WorldFx";

const EXP2 = 0.0036;
const EYE = 1.6;

describe("heightFogAmount", () => {
  it("is zero at the eye and grows with distance", () => {
    expect(heightFogAmount(0, EYE, EYE, EXP2)).toBe(0);
    const near = heightFogAmount(60, EYE, HEIGHT_FOG.floor, EXP2);
    const far = heightFogAmount(300, EYE, HEIGHT_FOG.floor, EXP2);
    expect(near).toBeGreaterThan(0);
    expect(far).toBeGreaterThan(near);
    expect(far).toBeLessThanOrEqual(1);
  });

  it("keeps the site under the terrace crisp", () => {
    expect(heightFogAmount(60, EYE, HEIGHT_FOG.floor, EXP2)).toBeLessThan(0.15);
  });

  it("is thicker towards the valley floor than towards a hilltop at the same distance", () => {
    const valley = heightFogAmount(250, EYE, HEIGHT_FOG.floor, EXP2);
    const hilltop = heightFogAmount(250, EYE, 30, EXP2);
    expect(valley).toBeGreaterThan(hilltop);
  });

  it("is continuous across a level ray", () => {
    const below = heightFogAmount(100, EYE, EYE - 1e-3, EXP2);
    const level = heightFogAmount(100, EYE, EYE, EXP2);
    const above = heightFogAmount(100, EYE, EYE + 1e-3, EXP2);
    expect(Math.abs(below - level)).toBeLessThan(1e-4);
    expect(Math.abs(above - level)).toBeLessThan(1e-4);
  });
});

describe("gradeFor", () => {
  it("returns each zone's grade at the ends of the blends", () => {
    expect(gradeFor(0, 0)).toEqual(GRADES.store);
    expect(gradeFor(0, 1)).toEqual(GRADES.store);
    expect(gradeFor(1, 0)).toEqual(GRADES.daylight);
    expect(gradeFor(1, 1)).toEqual(GRADES.industrial);
  });

  it("desaturates and cools an industrial site", () => {
    const natural = gradeFor(1, 0);
    const industrial = gradeFor(1, 1);
    expect(industrial.saturation).toBeLessThan(natural.saturation);
    expect(industrial.gain[2]).toBeGreaterThan(industrial.gain[0]);
    expect(natural.gain[0]).toBeGreaterThan(natural.gain[2]);
  });

  it("clamps out-of-range blends", () => {
    expect(gradeFor(-1, 2)).toEqual(gradeFor(0, 1));
    expect(gradeFor(2, -1)).toEqual(gradeFor(1, 0));
  });
});

describe("fxOptionsFor", () => {
  it("sways foliage only", () => {
    expect(fxOptionsFor("M_FOLIAGE_OAK", false, 0.2)).toEqual({
      wind: 0.2,
      idle: false,
      phase: false,
    });
    expect(fxOptionsFor("M_FOLIAGE_OAK", true, 0.2)).toEqual({
      wind: 0.2,
      idle: false,
      phase: true,
    });
    expect(fxOptionsFor("M_TREE_BARK", true, 0.2)).toEqual({ wind: 0, idle: false, phase: false });
  });

  it("animates animals only when the mesh carries a phase", () => {
    expect(fxOptionsFor("M_ANIMAL_HEN", true, 0.2)).toEqual({ wind: 0, idle: true, phase: true });
    expect(fxOptionsFor("M_ANIMAL_HEN", false, 0.2)).toEqual({
      wind: 0,
      idle: false,
      phase: false,
    });
    expect(fxOptionsFor("M_ROOF", true, 0.2)).toEqual({ wind: 0, idle: false, phase: false });
  });
});

describe("updateWorldFx", () => {
  it("freezes time and motion under reduced motion", () => {
    const sun = new Vector3(0, 1, 0);
    FX_UNIFORMS.uFxTime.value = 0;
    updateWorldFx(0.5, 1, sun, false);
    expect(FX_UNIFORMS.uFxTime.value).toBe(0.5);
    expect(FX_UNIFORMS.uFxMotion.value).toBe(1);
    updateWorldFx(0.5, 1, sun, true);
    expect(FX_UNIFORMS.uFxTime.value).toBe(0.5);
    expect(FX_UNIFORMS.uFxMotion.value).toBe(0);
  });

  it("casts no cloud shadow indoors", () => {
    updateWorldFx(0, 0, new Vector3(0, 1, 0), false);
    expect(FX_UNIFORMS.uFxCloudShade.value).toBe(0);
  });
});

describe("mirrorPoint", () => {
  it("reflects in the floor plane", () => {
    expect(mirrorPoint(new Vector3(2, 1.6, -3), 0).toArray()).toEqual([2, -1.6, -3]);
    expect(mirrorPoint(new Vector3(0, 1, 0), 0.25).toArray()).toEqual([0, -0.5, 0]);
  });
});

describe("seeded", () => {
  it("is deterministic and stays in [0, 1)", () => {
    for (let i = 0; i < 200; i++) {
      const value = seeded(i, 3);
      expect(value).toBe(seeded(i, 3));
      expect(value).toBeGreaterThanOrEqual(0);
      expect(value).toBeLessThan(1);
    }
  });
});
