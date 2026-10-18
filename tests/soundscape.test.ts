import { describe, expect, it } from "vitest";
import { ambienceMix } from "../src/world/Soundscape";

describe("ambienceMix", () => {
  it("keeps the store discreet: ventilation and soft music, no wind or machinery", () => {
    const mix = ambienceMix("STORE", 0);
    expect(mix.vent).toBeGreaterThan(0);
    expect(mix.music).toBeGreaterThan(0);
    expect(mix.wind).toBe(0);
    expect(mix.hum).toBe(0);
  });

  it("dips the commercial music once a shelf is scanned and adds low mechanical tones", () => {
    const store = ambienceMix("STORE", 0);
    const opening = ambienceMix("OPENING", 0);
    expect(opening.music).toBeLessThan(store.music);
    expect(opening.hum).toBeGreaterThan(0);
  });

  it("gives the terrace wind instead of indoor sound", () => {
    const mix = ambienceMix("CHAIN", 1);
    expect(mix.wind).toBeGreaterThan(0);
    expect(mix.vent).toBe(0);
    expect(mix.music).toBe(0);
  });

  it("is gentler on the forecourt than on the terrace", () => {
    expect(ambienceMix("END_MENU", 1).wind).toBeLessThan(ambienceMix("TERRACE", 1).wind);
    expect(ambienceMix("END_MENU", 1).hum).toBe(0);
  });
});
