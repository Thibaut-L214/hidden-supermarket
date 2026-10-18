// Comfort settings (docs/DA.md §08). Kept in memory for now; the full menu comes later.

export interface Settings {
  /** Radians of view rotation per pixel of mouse movement. */
  mouseSensitivity: number;
  /** Walking speed in metres per second. */
  moveSpeed: number;
  reducedMotion: boolean;
}

export const SETTINGS_RANGES = {
  mouseSensitivity: { min: 0.0005, max: 0.006, step: 0.0005 },
  moveSpeed: { min: 1, max: 4, step: 0.25 },
} as const;

export function defaultSettings(prefersReducedMotion: boolean): Settings {
  return { mouseSensitivity: 0.002, moveSpeed: 2.2, reducedMotion: prefersReducedMotion };
}
