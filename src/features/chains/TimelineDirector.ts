// Timeline clock (docs/TECH.md §04–05). Knows only step durations: the whole scene state is a
// pure function of the elapsed time, so pause, replay and resume are deterministic.
import type { TimelineStep } from "./ChainModule";

export interface TimelineState {
  /** Progress of every step in [0, 1]; finished steps are 1, upcoming ones 0. */
  progress: number[];
  /** Index of the step under way (the last one once finished). */
  active: number;
  done: boolean;
}

export function evaluate(
  steps: readonly Pick<TimelineStep, "durationSec">[],
  t: number,
): TimelineState {
  let start = 0;
  let active = steps.length - 1;
  const progress = steps.map((step, i) => {
    const p = step.durationSec > 0 ? (t - start) / step.durationSec : t >= start ? 1 : 0;
    start += step.durationSec;
    const clamped = Math.min(Math.max(p, 0), 1);
    if (clamped < 1 && i < active) active = i;
    return clamped;
  });
  return { progress, active: Math.max(active, 0), done: t >= start };
}

export function totalDuration(steps: readonly Pick<TimelineStep, "durationSec">[]): number {
  return steps.reduce((sum, step) => sum + step.durationSec, 0);
}

export class TimelineDirector {
  elapsed = 0;

  constructor(readonly steps: readonly TimelineStep[]) {}

  get total(): number {
    return totalDuration(this.steps);
  }

  restart(): void {
    this.elapsed = 0;
  }

  /** Advances by game time (0 while paused) and returns the resulting state. */
  update(dt: number): TimelineState {
    this.elapsed = Math.min(this.elapsed + Math.max(dt, 0), this.total);
    return evaluate(this.steps, this.elapsed);
  }

  get state(): TimelineState {
    return evaluate(this.steps, this.elapsed);
  }
}
