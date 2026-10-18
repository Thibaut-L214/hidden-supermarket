import { describe, expect, it } from "vitest";
import { GameClock } from "../src/core/GameClock";

describe("GameClock", () => {
  it("measures game time from consecutive ticks", () => {
    const clock = new GameClock();
    expect(clock.tick(1000)).toBe(0);
    expect(clock.tick(1016)).toBeCloseTo(0.016);
    expect(clock.tick(1066)).toBeCloseTo(0.05);
    expect(clock.elapsed).toBeCloseTo(0.066);
  });

  it("caps a stalled frame at maxDelta", () => {
    const clock = new GameClock(0.1);
    clock.tick(0);
    expect(clock.tick(3000)).toBe(0.1);
  });

  it("stands still while paused and resumes without a time jump", () => {
    const clock = new GameClock();
    clock.tick(0);
    clock.tick(16);
    clock.setPaused("hidden", true);
    expect(clock.tick(5000)).toBe(0);
    clock.setPaused("hidden", false);
    expect(clock.tick(60000)).toBe(0);
    expect(clock.tick(60016)).toBeCloseTo(0.016);
    expect(clock.elapsed).toBeCloseTo(0.032);
  });

  it("stays paused until every reason is lifted", () => {
    const clock = new GameClock();
    clock.setPaused("menu", true);
    clock.setPaused("hidden", true);
    clock.setPaused("hidden", false);
    expect(clock.paused).toBe(true);
    clock.setPaused("menu", false);
    expect(clock.paused).toBe(false);
  });
});
