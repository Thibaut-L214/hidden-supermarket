// Scanner (docs/GDD.md §04, §06.0): aim at a shelf, then hold the click or press E.
// The scanner only reports which shelf was confirmed; it never decides any content.
import { type Camera, type Object3D, Raycaster, Vector2 } from "three";
import type { ChainId } from "../../core/chain";
import type { ScanTarget } from "./ScanTarget";

export const SCAN_RANGE = 4.5;
export const HOLD_SECONDS = 0.6;

/**
 * Confirmation logic. One confirmation per interaction: after a scan, the click must be
 * released (or E pressed again) before another one can start.
 */
export class ScanInteraction {
  /** Hold progress in [0, 1]. */
  progress = 0;
  private armed = true;

  /** @param pressed true on the frame E went down (edge, not level) */
  update(target: ChainId | null, holding: boolean, pressed: boolean, dt: number): ChainId | null {
    if (!holding && !pressed) {
      this.armed = true;
      this.progress = 0;
      return null;
    }
    if (!target || !this.armed) {
      this.progress = 0;
      return null;
    }
    if (!pressed) {
      this.progress = Math.min(this.progress + dt / HOLD_SECONDS, 1);
      if (this.progress < 1) return null;
    }
    this.armed = false;
    this.progress = 0;
    return target;
  }

  reset(): void {
    this.progress = 0;
    this.armed = false;
  }
}

function isInside(object: Object3D, root: Object3D): boolean {
  for (let node: Object3D | null = object; node; node = node.parent) {
    if (node === root) return true;
  }
  return false;
}

/**
 * Shelf under the reticle within range, or null. Colliders closer than the shelf block the
 * aim, except the shelf's own (its doors sit inside the scan volume).
 */
export function aimAt(
  raycaster: Raycaster,
  targets: readonly ScanTarget[],
  occluders: readonly Object3D[],
): ScanTarget | null {
  const [hit] = raycaster.intersectObjects(
    targets.map((t) => t.volume),
    false,
  );
  if (!hit) return null;
  const target = targets.find((t) => t.volume === hit.object) ?? null;
  if (!target) return null;
  const blockers = occluders.filter((o) => !isInside(o, target.shelfRoot));
  const [blocker] = raycaster.intersectObjects(blockers, false);
  return blocker && blocker.distance < hit.distance - 0.01 ? null : target;
}

export class Scanner {
  onConfirm: (chainId: ChainId) => void = () => {};
  /** Shelf currently aimed at (null when disabled). */
  target: ScanTarget | null = null;

  private readonly raycaster = new Raycaster();
  private readonly interaction = new ScanInteraction();
  private readonly centre = new Vector2(0, 0);
  private holding = false;
  private pressed = false;
  private enabled = false;

  constructor(
    private readonly camera: Camera,
    private readonly targets: readonly ScanTarget[],
    private readonly occluders: () => readonly Object3D[],
    element: HTMLElement,
  ) {
    this.raycaster.far = SCAN_RANGE;
    element.addEventListener("mousedown", (event) => {
      if (event.button === 0) this.holding = true;
    });
    window.addEventListener("mouseup", () => (this.holding = false));
    window.addEventListener("blur", () => (this.holding = false));
    document.addEventListener("keydown", (event) => {
      if (event.code === "KeyE" && !event.repeat) this.pressed = true;
    });
  }

  get progress(): number {
    return this.interaction.progress;
  }

  setEnabled(enabled: boolean): void {
    if (enabled === this.enabled) return;
    this.enabled = enabled;
    // A click or key still held from before must not scan on re-enable.
    this.interaction.reset();
    if (!enabled) this.setTarget(null);
  }

  update(dt: number): void {
    const pressed = this.pressed;
    this.pressed = false;
    if (!this.enabled) return;

    this.raycaster.setFromCamera(this.centre, this.camera);
    this.setTarget(aimAt(this.raycaster, this.targets, this.occluders()));
    const confirmed = this.interaction.update(
      this.target?.chainId ?? null,
      this.holding,
      pressed,
      dt,
    );
    if (confirmed) this.onConfirm(confirmed);
  }

  private setTarget(target: ScanTarget | null): void {
    if (target === this.target) return;
    if (this.target) this.target.outline.visible = false;
    if (target) target.outline.visible = true;
    this.target = target;
  }
}
