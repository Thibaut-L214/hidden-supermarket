import { describe, expect, it } from "vitest";
import { CHAINS } from "../src/data/chains";
import { SHORT_MAX, TODO_SOURCE, type Caption } from "../src/features/content/types";

const captions: Caption[] = Object.values(CHAINS).flatMap((chain) => Object.values(chain.captions));

describe("chain captions", () => {
  it.each(captions.map((c) => [c.id, c]))("%s respects the content schema", (_, caption) => {
    expect(caption.short.length).toBeLessThanOrEqual(SHORT_MAX);
    expect(caption.title.trim()).not.toBe("");
    expect(caption.detail.trim()).not.toBe("");
    if (caption.kind === "verified") expect(caption.source).toBeDefined();
  });

  it("uses unique ids", () => {
    const ids = captions.map((c) => c.id);
    expect(new Set(ids).size).toBe(ids.length);
  });

  it("states no digits in captions still lacking a source", () => {
    // Guards against invented figures (docs/TECH.md §08).
    const unsourced = captions.filter((c) => c.source === undefined || c.source === TODO_SOURCE);
    for (const caption of unsourced) {
      const text = `${caption.short} ${caption.detail}`.replaceAll("L214", "");
      expect(text).not.toMatch(/\d/);
    }
  });
});

describe("chain configs", () => {
  it.each(Object.values(CHAINS).map((c) => [c.id, c]))(
    "%s references existing captions",
    (_, chain) => {
      const ids = new Set(chain.captions.map((c) => c.id));
      const referenced = [
        chain.terraceCaption,
        chain.revealCaption,
        ...chain.recap,
        ...chain.timeline.map((s) => s.captionId),
      ];
      expect(referenced.filter((id) => !ids.has(id))).toEqual([]);
      expect(chain.recap.length).toBeLessThanOrEqual(3);
    },
  );

  it.each(Object.values(CHAINS).map((c) => [c.id, c]))(
    "%s timeline steps are well formed",
    (_, chain) => {
      for (const step of chain.timeline) {
        expect(step.durationSec).toBeGreaterThan(0);
        if (step.event === "drive") {
          expect(step.vehicle && step.pathId).toBeTruthy();
        } else {
          expect(step.from ?? step.to).toBeTruthy();
        }
      }
    },
  );

  it("never stages animal transport or slaughter in the eggs chain", () => {
    // docs/GDD.md §06.4 and docs/TECH.md §06.
    const names = CHAINS.eggs!.timeline.flatMap((s) => [s.from, s.to, s.vehicle, s.pathId]);
    expect(names.join(" ")).not.toMatch(/ANIMAL|LIVESTOCK|SLAUGHTER|ABATTOIR/i);
  });
});
