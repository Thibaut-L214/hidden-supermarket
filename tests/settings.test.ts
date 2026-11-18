import { describe, expect, it } from "vitest";
import { defaultSettings, effectiveVolume } from "../src/app/settings";

describe("settings", () => {
  it("starts with sound on", () => {
    expect(defaultSettings(false).muted).toBe(false);
  });

  it("mutes without losing the chosen volume", () => {
    const settings = defaultSettings(false);
    settings.volume = 0.4;
    expect(effectiveVolume(settings)).toBe(0.4);
    settings.muted = true;
    expect(effectiveVolume(settings)).toBe(0);
    expect(settings.volume).toBe(0.4);
  });
});
