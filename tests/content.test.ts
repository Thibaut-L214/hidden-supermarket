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
