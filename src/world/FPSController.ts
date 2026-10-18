// First-person camera: mouse look (pointer lock, or drag when the lock is unavailable) and
// keyboard walking on flat floors. Keys are read by physical code, so ZQSD on AZERTY and WASD on
// QWERTY are the same keys (docs/DECISIONS.md, « Entrées »). No head bob or forced shake.
import type { PerspectiveCamera } from "three";
import type { Settings } from "../app/settings";
import type { CollisionWorld, Vec2 } from "./CollisionWorld";

export interface View {
  /** Radians around Y; 0 looks towards -Z. */
  yaw: number;
  /** Radians around X; positive looks up. */
  pitch: number;
}

export type Direction = "forward" | "back" | "left" | "right";

export const KEY_BINDINGS: Readonly<Record<string, Direction>> = {
  KeyW: "forward",
  ArrowUp: "forward",
  KeyS: "back",
  ArrowDown: "back",
  KeyA: "left",
  ArrowLeft: "left",
  KeyD: "right",
  ArrowRight: "right",
};

const PITCH_LIMIT = (85 * Math.PI) / 180;

export function applyLook(view: View, dx: number, dy: number, sensitivity: number): View {
  const pitch = view.pitch - dy * sensitivity;
  return {
    yaw: view.yaw - dx * sensitivity,
    pitch: Math.min(Math.max(pitch, -PITCH_LIMIT), PITCH_LIMIT),
  };
}

/** Horizontal displacement for one frame; diagonals are not faster than straight lines. */
export function walkDelta(
  held: ReadonlySet<Direction>,
  yaw: number,
  speed: number,
  dt: number,
): Vec2 {
  const ahead = (held.has("forward") ? 1 : 0) - (held.has("back") ? 1 : 0);
  const side = (held.has("right") ? 1 : 0) - (held.has("left") ? 1 : 0);
  const length = Math.hypot(ahead, side);
  if (length === 0 || dt <= 0) return { x: 0, z: 0 };
  const k = (speed * dt) / length;
  const sin = Math.sin(yaw);
  const cos = Math.cos(yaw);
  // forward = (-sin, -cos), right = (cos, -sin)
  return { x: (-sin * ahead + cos * side) * k, z: (-cos * ahead - sin * side) * k };
}

export class FPSController {
  view: View = { yaw: 0, pitch: 0 };
  /** Called when the pointer lock is lost without being asked for (Échap, focus loss). */
  onLockLost: () => void = () => {};

  private readonly held = new Set<Direction>();
  private active = false;
  private dragging = false;
  private releasing = false;

  constructor(
    private readonly camera: PerspectiveCamera,
    private readonly element: HTMLElement,
    private readonly collisions: CollisionWorld,
    private readonly settings: Settings,
    private readonly eyeHeight: number,
  ) {
    document.addEventListener("keydown", this.onKeyDown);
    document.addEventListener("keyup", this.onKeyUp);
    document.addEventListener("mousemove", this.onMouseMove);
    document.addEventListener("pointerlockchange", this.onLockChange);
    element.addEventListener("mousedown", this.onMouseDown);
    window.addEventListener("mouseup", this.onMouseUp);
    window.addEventListener("blur", this.releaseKeys);
  }

  get locked(): boolean {
    return document.pointerLockElement === this.element;
  }

  /** Enables input. Requests the pointer lock; drag-to-look remains if the browser refuses. */
  async activate(): Promise<void> {
    this.active = true;
    try {
      await this.element.requestPointerLock();
    } catch {
      // Pointer lock refused (browser policy, embedded frame): drag-to-look still works.
    }
  }

  /** Disables input and releases the pointer without reporting it as a lost lock. */
  deactivate(): void {
    this.active = false;
    this.releaseKeys();
    if (this.locked) {
      this.releasing = true;
      document.exitPointerLock();
    }
  }

  setPose(position: { x: number; z: number }, yaw: number): void {
    this.camera.position.set(position.x, this.eyeHeight, position.z);
    this.view = { yaw, pitch: 0 };
    this.applyView();
  }

  update(dt: number): void {
    if (!this.active) return;
    const delta = walkDelta(this.held, this.view.yaw, this.settings.moveSpeed, dt);
    const p = this.camera.position;
    const next = this.collisions.move({ x: p.x, z: p.z }, delta);
    p.set(next.x, this.eyeHeight, next.z);
  }

  private applyView(): void {
    this.camera.rotation.set(this.view.pitch, this.view.yaw, 0, "YXZ");
  }

  private readonly onKeyDown = (event: KeyboardEvent) => {
    const direction = KEY_BINDINGS[event.code];
    if (!direction || !this.active) return;
    this.held.add(direction);
    event.preventDefault();
  };

  private readonly onKeyUp = (event: KeyboardEvent) => {
    const direction = KEY_BINDINGS[event.code];
    if (direction) this.held.delete(direction);
  };

  private readonly onMouseMove = (event: MouseEvent) => {
    if (!this.active || !(this.locked || this.dragging)) return;
    this.view = applyLook(
      this.view,
      event.movementX,
      event.movementY,
      this.settings.mouseSensitivity,
    );
    this.applyView();
  };

  private readonly onMouseDown = (event: MouseEvent) => {
    if (event.button === 0 && !this.locked) this.dragging = true;
  };

  private readonly onMouseUp = () => {
    this.dragging = false;
  };

  private readonly onLockChange = () => {
    if (this.locked) return;
    if (this.releasing) {
      this.releasing = false;
      return;
    }
    if (this.active) this.onLockLost();
  };

  private readonly releaseKeys = () => {
    this.held.clear();
    this.dragging = false;
  };
}
