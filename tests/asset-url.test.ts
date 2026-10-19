import { describe, expect, it } from "vitest";
import { assetUrl } from "../src/core/assetUrl";

describe("assetUrl", () => {
  it("resolves an asset from a relative deployment base", () => {
    expect(assetUrl("/assets/store/store.glb", "./")).toBe("./assets/store/store.glb");
  });

  it("resolves an asset from a repository deployment base", () => {
    expect(assetUrl("assets/store/store.glb", "/hidden-supermarket/")).toBe(
      "/hidden-supermarket/assets/store/store.glb",
    );
  });
});
