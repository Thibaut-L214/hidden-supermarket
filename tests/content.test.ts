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

  it("follows the eggs to the store before the separate end-of-lay sequence", () => {
    const { timeline } = CHAINS.eggs!;
    expect(timeline.map((step) => step.id)).toEqual([
      "collect",
      "load-farm",
      "to-packing",
      "process",
      "load-delivery",
      "to-store",
      "deliver",
      "load-hens",
      "hens-leave",
    ]);
  });

  it("documents the caged-hen case without presenting it as the French majority", () => {
    const { captions, sources } = CHAINS.eggs!;
    const system = captions.find((caption) => caption.id === "eggs.system")!;
    const transport = captions.find((caption) => caption.id === "eggs.transport")!;
    const scope = captions.find((caption) => caption.id === "eggs.recap.scope")!;

    expect(system.kind).toBe("verified");
    expect(system.short).toContain("750 cm²");
    expect(system.detail).toContain("600 cm² utilisables");
    expect(system.detail).toContain("15 cm de perchoir");
    expect(system.detail).toContain("ne montre pas tous ces équipements");
    expect(transport.kind).toBe("verified");
    expect(transport.detail).toContain("peut être installé sur le même site");
    expect(scope.kind).toBe("verified");
    expect(scope.short).toContain("72 %");
    expect(scope.short).toContain("hors cage");
    expect(sources.map((source) => source.id)).toEqual([
      "eu-laying-hens-1999-74",
      "eu-eggs-marketing-2023-2465",
      "fr-eggs-production-2024",
      "efsa-poultry-transport-2022",
    ]);
  });

  it("identifies the hens' end-of-lay transport and its off-screen destination", () => {
    const { timeline, captions } = CHAINS.eggs!;
    const animalSteps = timeline.filter((s) => /HENCRATES|ANIMALS/.test(`${s.from}${s.to}${s.vehicle}`));
    expect(animalSteps.map((s) => s.id)).toEqual(["load-hens", "hens-leave"]);
    for (const step of animalSteps) {
      const caption = captions.find((c) => c.id === step.captionId)!;
      expect(caption.kind).toBe("verified");
      expect(caption.source).not.toBe(TODO_SOURCE);
      expect(caption.status).toBe("review");
    }
    expect(captions.find((caption) => caption.id === "eggs.hens.leave")!.short).toMatch(
      /abattoir/i,
    );
  });
});
