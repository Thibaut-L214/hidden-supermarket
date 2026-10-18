import { describe, expect, it } from "vitest";
import { PerfMonitor, percentile } from "../src/core/PerfMonitor";

describe("percentile", () => {
  it("uses the nearest-rank method", () => {
    const values = Array.from({ length: 100 }, (_, i) => i + 1);
    expect(percentile(values, 95)).toBe(95);
    expect(percentile([5], 95)).toBe(5);
    expect(percentile([], 95)).toBe(0);
  });
});

describe("PerfMonitor", () => {
  it("averages a rolling window and ignores pauses", () => {
    const perf = new PerfMonitor(3);
    for (const t of [0, 16, 32, 48, 5000, 5016]) perf.frame(t);
    const { fps, samples, p95Ms } = perf.stats;
    expect(samples).toBe(3);
    expect(fps).toBeCloseTo(62.5);
    expect(p95Ms).toBe(16);
  });
});
