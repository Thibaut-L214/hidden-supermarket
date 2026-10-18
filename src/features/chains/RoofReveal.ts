// Roof removal (docs/DA.md §04: readable in 2–4 s, no gratuitous magic; docs/TECH.md §06).
// The roof rises a little while fading out; with reduced motion it only fades. Poses come from
// the reference transform, so the reveal replays identically after reset().
import { type Material, Mesh, type Object3D } from "three";
import { ease } from "../../core/easing";

export const ROOF_SECONDS = 3;
/** Rise in metres during the reveal (0 with reduced motion). */
export const ROOF_LIFT = 4;

export class RoofReveal {
  /** Linear progress in [0, 1]. */
  progress = 0;
  private readonly baseY: number;
  private readonly materials: Material[] = [];

  constructor(
    private readonly roof: Object3D,
    private readonly reducedMotion: () => boolean,
  ) {
    this.baseY = roof.position.y;
    // Own copies, so fading the roof never touches another object's material.
    roof.traverse((object) => {
      if (!(object instanceof Mesh)) return;
      const own = (Array.isArray(object.material) ? object.material : [object.material]).map((m) =>
        m.clone(),
      );
      object.material = Array.isArray(object.material) ? own : own[0]!;
      this.materials.push(...own);
    });
  }

  get done(): boolean {
    return this.progress === 1;
  }

  /** Advances the reveal; returns true once it is complete. */
  update(dt: number): boolean {
    if (dt > 0 && this.progress < 1) {
      this.progress = Math.min(this.progress + dt / ROOF_SECONDS, 1);
      this.apply();
    }
    return this.done;
  }

  /** Back to the closed roof (module unloaded, or a new visit). */
  reset(): void {
    this.progress = 0;
    this.apply();
  }

  private apply(): void {
    const t = ease(this.progress);
    this.roof.position.y = this.baseY + (this.reducedMotion() ? 0 : ROOF_LIFT * t);
    this.roof.visible = this.progress < 1;
    const fading = this.progress > 0 && this.progress < 1;
    for (const material of this.materials) {
      material.transparent = fading;
      material.depthWrite = !fading;
      material.opacity = 1 - t;
    }
  }
}
