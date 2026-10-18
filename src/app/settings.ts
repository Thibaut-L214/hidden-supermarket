// Comfort and accessibility settings (docs/DA.md §08). Kept in memory for the session.

export interface Settings {
  /** Radians of view rotation per pixel of mouse movement. */
  mouseSensitivity: number;
  /** Walking speed in metres per second. */
  moveSpeed: number;
  /** Master volume in [0, 1]; 0 is the no-audio mode. */
  volume: number;
  reducedMotion: boolean;
  /** Text descriptions of sound cues. */
  subtitles: boolean;
  /** Lower pixel ratio, no shadows (docs/TECH.md §07). */
  lowQuality: boolean;
}

export type RangeSetting = "mouseSensitivity" | "moveSpeed" | "volume";

export const SETTINGS_RANGES: Record<RangeSetting, { min: number; max: number; step: number }> = {
  mouseSensitivity: { min: 0.0005, max: 0.006, step: 0.0005 },
  moveSpeed: { min: 1, max: 4, step: 0.25 },
  volume: { min: 0, max: 1, step: 0.1 },
};

export function isRangeSetting(key: keyof Settings): key is RangeSetting {
  return key in SETTINGS_RANGES;
}

export function defaultSettings(prefersReducedMotion: boolean): Settings {
  return {
    mouseSensitivity: 0.002,
    moveSpeed: 2.2,
    volume: 0.7,
    reducedMotion: prefersReducedMotion,
    subtitles: true,
    lowQuality: false,
  };
}
