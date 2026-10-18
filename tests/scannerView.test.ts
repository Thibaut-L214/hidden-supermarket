import { describe, expect, it } from "vitest";
import { scannerRaised, screenText } from "../src/features/scanner/ScannerView";

describe("scannerRaised", () => {
  it.each([
    ["STORE", true],
    ["SCANNING", true],
    ["OPENING", true],
    ["TERRACE", false],
    ["CHAIN", false],
    ["EXIT", false],
  ] as const)("%s → %s", (state, expected) => {
    expect(scannerRaised(state)).toBe(expected);
  });
});

describe("screenText", () => {
  it("invites to aim when nothing is targeted", () => {
    expect(screenText(null, 0, false)).toEqual({
      title: "Prêt",
      subtitle: "Visez un rayon",
      progress: null,
    });
  });

  it("names the shelf aimed at and shows the hold progress", () => {
    expect(screenText("Œufs", 0.4, false)).toEqual({
      title: "Œufs",
      subtitle: "Maintenir pour scanner",
      progress: 0.4,
    });
  });

  it("confirms the scan", () => {
    expect(screenText("Œufs", 0, true)).toEqual({ title: "Scanné", subtitle: "Œufs", progress: 1 });
  });
});
