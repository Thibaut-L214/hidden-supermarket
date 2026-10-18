import { BoxGeometry, Mesh, MeshStandardMaterial } from "three";
import { describe, expect, it } from "vitest";
import { ROOF_LIFT, ROOF_SECONDS, RoofReveal } from "../src/features/chains/RoofReveal";

function roof() {
  const shared = new MeshStandardMaterial();
  const mesh = new Mesh(new BoxGeometry(10, 0.5, 4), shared);
  mesh.position.y = -8.5;
  return { mesh, shared };
}

describe("RoofReveal", () => {
  it("rises and fades out in ROOF_SECONDS, then hides", () => {
    const { mesh } = roof();
    const reveal = new RoofReveal(mesh, () => false);
    reveal.update(ROOF_SECONDS / 2);
    const material = mesh.material as MeshStandardMaterial;
    expect(mesh.position.y).toBeCloseTo(-8.5 + ROOF_LIFT / 2);
    expect(material.opacity).toBeCloseTo(0.5);
    expect(material.transparent).toBe(true);
    expect(reveal.update(ROOF_SECONDS / 2)).toBe(true);
    expect(mesh.visible).toBe(false);
  });

  it("only fades with reduced motion", () => {
    const { mesh } = roof();
    const reveal = new RoofReveal(mesh, () => true);
    reveal.update(ROOF_SECONDS / 2);
    expect(mesh.position.y).toBe(-8.5);
    expect((mesh.material as MeshStandardMaterial).opacity).toBeCloseTo(0.5);
  });

  it("never alters the shared source material", () => {
    const { mesh, shared } = roof();
    new RoofReveal(mesh, () => false).update(ROOF_SECONDS / 2);
    expect(mesh.material).not.toBe(shared);
    expect(shared.opacity).toBe(1);
  });

  it("resets to the exact closed pose and replays identically", () => {
    const { mesh } = roof();
    const reveal = new RoofReveal(mesh, () => false);
    reveal.update(ROOF_SECONDS);
    reveal.reset();
    expect(mesh.position.y).toBe(-8.5);
    expect(mesh.visible).toBe(true);
    expect((mesh.material as MeshStandardMaterial).transparent).toBe(false);
    reveal.update(ROOF_SECONDS / 4);
    const quarter = mesh.position.y;
    reveal.reset();
    reveal.update(ROOF_SECONDS / 4);
    expect(mesh.position.y).toBe(quarter);
  });
});
