// Game time, separate from wall-clock time (docs/TECH.md §05): suspended while paused or while
// the tab is hidden, and resumed without a time jump.

export type PauseReason = "menu" | "hidden";

export class GameClock {
  /** Game seconds elapsed since creation, excluding pauses. */
  elapsed = 0;
  private last: number | null = null;
  private readonly reasons = new Set<PauseReason>();

  /** @param maxDelta upper bound of one step in seconds, so a stalled frame cannot teleport anything. */
  constructor(private readonly maxDelta = 0.1) {}

  get paused(): boolean {
    return this.reasons.size > 0;
  }

  setPaused(reason: PauseReason, paused: boolean): void {
    if (paused) this.reasons.add(reason);
    else this.reasons.delete(reason);
    this.last = null;
  }

  /** Advances with a wall-clock timestamp in milliseconds and returns the game delta in seconds. */
  tick(nowMs: number): number {
    if (this.paused || this.last === null) {
      this.last = this.paused ? null : nowMs;
      return 0;
    }
    const dt = Math.min(Math.max((nowMs - this.last) / 1000, 0), this.maxDelta);
    this.last = nowMs;
    this.elapsed += dt;
    return dt;
  }
}
