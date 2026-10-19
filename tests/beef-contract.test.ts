import { describe, expect, it } from "vitest";
import { STORE_CONTRACT, shelfNodes, terraceNodes } from "../src/core/assetContract";
import { CHAIN_IDS } from "../src/core/chain";

describe("beef asset registration", () => {
  it("requires a complete second scannable shelf in the store", () => {
    expect(CHAIN_IDS).toContain("beef");
    for (const name of Object.values(shelfNodes("beef"))) {
      expect(STORE_CONTRACT.required).toContain(name);
    }
    expect(STORE_CONTRACT.parents.DOOR_BEEF_L).toBe("HINGE_BEEF_L");
    expect(STORE_CONTRACT.parents.DOOR_BEEF_R).toBe("HINGE_BEEF_R");
  });

  it("identifies bovines as animals while preserving the existing eggs export", () => {
    expect(terraceNodes("beef").animals).toBe("ANIMALS_BEEF");
    expect(terraceNodes("eggs").animals).toBe("HENS_EGGS");
  });
});
