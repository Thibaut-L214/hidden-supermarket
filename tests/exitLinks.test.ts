import { describe, expect, it } from "vitest";
import { EXIT_LINKS, OFFICIAL_HOSTS } from "../src/data/exitLinks";

describe("EXIT_LINKS", () => {
  it("offers the five choices of docs/GDD.md §09 (the return is a button)", () => {
    expect(EXIT_LINKS.map((l) => l.label)).toEqual([
      "Découvrir L214",
      "Lire les enquêtes",
      "Agir",
      "Faire un don",
    ]);
  });

  it("points only to official L214 hosts over HTTPS", () => {
    for (const link of EXIT_LINKS) {
      if (!link.url) continue;
      const url = new URL(link.url);
      expect(url.protocol).toBe("https:");
      expect(OFFICIAL_HOSTS).toContain(url.hostname);
    }
  });
});
