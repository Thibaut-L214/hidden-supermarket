// Frame timing for the prototype budgets (docs/TECH.md §07: 60 fps target, p95 < 25 ms).

export function percentile(values: readonly number[], p: number): number {
  if (values.length === 0) return 0;
  const sorted = [...values].sort((a, b) => a - b);
  const index = Math.min(sorted.length - 1, Math.max(0, Math.ceil((p / 100) * sorted.length) - 1));
  return sorted[index]!;
}

export interface FrameStats {
  fps: number;
  avgMs: number;
  p95Ms: number;
  samples: number;
}

/** Rolling window of wall-clock frame durations. */
export class PerfMonitor {
  private readonly times: number[] = [];
  private last: number | null = null;

  constructor(private readonly window = 300) {}

  /** Call once per rendered frame with its rAF timestamp in milliseconds. */
  frame(nowMs: number): void {
    if (this.last !== null) this.record(nowMs - this.last);
    this.last = nowMs;
  }

  record(frameMs: number): void {
    // A hidden tab or a breakpoint is not a frame.
    if (frameMs <= 0 || frameMs > 1000) return;
    this.times.push(frameMs);
    if (this.times.length > this.window) this.times.shift();
  }

  get stats(): FrameStats {
    const n = this.times.length;
    const avgMs = n ? this.times.reduce((a, b) => a + b, 0) / n : 0;
    return { fps: avgMs ? 1000 / avgMs : 0, avgMs, p95Ms: percentile(this.times, 95), samples: n };
  }
}
