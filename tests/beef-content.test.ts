import { describe, expect, it } from "vitest";
import { CHAINS } from "../src/data/chains";
import { SHORT_MAX, TODO_SOURCE } from "../src/features/content/types";

describe("beef chain", () => {
  it("makes the complete beef scenario available from the chain registry", () => {
    expect(CHAINS.beef).toBeDefined();
    expect(CHAINS.beef!.label).toBe("Viande bovine");
  });

  it("follows living cattle before chilling, cutting, packing and delivery", () => {
    const { timeline } = CHAINS.beef!;
    expect(timeline.map((step) => step.id)).toEqual([
      "load-cattle",
      "to-slaughterhouse",
      "unload-cattle",
      "approach",
      "slaughter",
      "chill",
      "cut",
      "pack",
      "load-delivery",
      "to-store",
      "deliver",
    ]);
    expect(timeline.filter((step) => step.event === "walk").map((step) => step.pathId)).toEqual([
      "PATH_BEEF_LOAD",
      "PATH_BEEF_UNLOAD",
      "PATH_BEEF_APPROACH",
    ]);
    const slaughter = timeline.find((step) => step.id === "slaughter")!;
    expect(slaughter.from).toBe("CATTLE_BEEF_APPROACH");
    expect(slaughter.to).toBeUndefined();
    expect(timeline.find((step) => step.id === "chill")!.to).toBe("MEAT_BEEF_CHILLED");
    expect(timeline.find((step) => step.id === "cut")!.to).toBe("MEAT_BEEF_CUT");
    expect(timeline.find((step) => step.id === "pack")!.to).toBe("CARTONS_BEEF_PACKED");
    expect(timeline.at(-1)!.from).toBe("CARGO_BEEF_DELIVERY");
  });

  it("names offscreen stunning and killing without promising effective stunning", () => {
    const { captions, timeline } = CHAINS.beef!;
    const slaughter = captions.find(
      (caption) => caption.id === timeline.find((step) => step.id === "slaughter")!.captionId,
    )!;
    expect(slaughter.short).toMatch(/hors champ/i);
    expect(slaughter.short).toMatch(/étourdissement/i);
    expect(slaughter.short).toMatch(/saignée/i);
    expect(slaughter.short).toMatch(/mise à mort/i);
    expect(slaughter.detail).toMatch(/échouer/i);
    expect(slaughter.detail).toMatch(/ne décrit pas toutes les pratiques/i);
    expect(slaughter.status).toBe("review");
  });

  it("limits the indoor scenario and identifies welfare risks and cattle origins", () => {
    const { captions, recap } = CHAINS.beef!;
    const text = captions.map((caption) => `${caption.short} ${caption.detail}`).join(" ");
    expect(text).toMatch(/engraissement en bâtiment/i);
    expect(text).toMatch(/allaitants.*laitiers/i);
    expect(text).toMatch(/prairie/i);
    expect(text).toMatch(/manque d’espace/i);
    expect(text).toMatch(/repos/i);
    expect(text).toMatch(/eau/i);
    expect(text).toMatch(/fourrage/i);
    expect(recap).toHaveLength(3);
  });

  it("keeps sourced claims under editorial review and schematic captions as drafts", () => {
    const { captions, sources } = CHAINS.beef!;
    for (const caption of captions) {
      expect(caption.short.length).toBeLessThanOrEqual(SHORT_MAX);
      if (caption.kind === "verified") {
        expect(caption.status).toBe("review");
        expect(caption.source).not.toBe(TODO_SOURCE);
        expect(sources).toContainEqual(caption.source);
      } else {
        expect(caption.status).toBe("draft");
        expect(`${caption.short} ${caption.detail}`).not.toMatch(/\d/);
      }
    }
    for (const source of sources) expect(source.consultedAt).toBe("2026-10-19");
  });
});
