/** Smoothstep easing on [0, 1]: gentle start and stop, no overshoot. */
export function ease(t: number): number {
  return t * t * (3 - 2 * t);
}
