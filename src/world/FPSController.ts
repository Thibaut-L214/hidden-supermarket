// First-person camera: mouse look (pointer lock, or drag when the lock is unavailable),
// keyboard walking on flat floors, and keyboard turning with ← / → (docs/GDD.md §04: look with
// the keyboard as an alternative). Keys are read by physical code, so ZQSD on AZERTY and WASD on
// QWERTY are the same keys (docs/DECISIONS.md, « Entrées »). No head bob or forced shake.
import type { PerspectiveCamera, Vector3 } from "three";
import { ease } from "../core/easing";
import type { Settings } from "../app/settings";
import type { CollisionWorld, Vec2 } from "./CollisionWorld";

export interface View {
  /** Radians around Y; 0 looks towards -Z. */
  yaw: number;
  /** Radians around X; positive looks up. */
  pitch: number;
}

export type Direction = "forward" | "back" | "left" | "right";
export type Control = Direction | "turnLeft" | "turnRight";

export const KEY_BINDINGS: Readonly<Record<string, Control>> = {
  KeyW: "forward",
  ArrowUp: "forward",
  KeyS: "back",
  ArrowDown: "back",
  KeyA: "left",
  KeyD: "right",
  ArrowLeft: "turnLeft",
  ArrowRight: "turnRight",
};

/** Keyboard turning speed, in radians per second (about 100° per second). */
export const KEY_TURN_SPEED = 1.75;

const PITCH_LIMIT = (85 * Math.PI) / 180;

export function applyLook(view: View, dx: number, dy: number, sensitivity: number): View {
  const pitch = view.pitch - dy * sensitivity;
  return {
    yaw: view.yaw - dx * sensitivity,
    pitch: Math.min(Math.max(pitch, -PITCH_LIMIT), PITCH_LIMIT),
  };
}

/** View that looks from one point at another (pitch clamped like the mouse look). */
export function viewToward(
  from: { x: number; y: number; z: number },
  to: { x: number; y: number; z: number },
): View {
  const dx = to.x - from.x;
  const dy = to.y - from.y;
  const dz = to.z - from.z;
  // forward (-sin yaw, -cos yaw) must point along (dx, dz).
  const pitch = Math.atan2(dy, Math.hypot(dx, dz));
  return {
    yaw: Math.atan2(-dx, -dz),
    pitch: Math.min(Math.max(pitch, -PITCH_LIMIT), PITCH_LIMIT),
  };
}

/** Interpolates along the shortest turn, t in [0, 1]. */
export function blendView(a: View, b: View, t: number): View {
  const turn = Math.atan2(Math.sin(b.yaw - a.yaw), Math.cos(b.yaw - a.yaw));
  return { yaw: a.yaw + turn * t, pitch: a.pitch + (b.pitch - a.pitch) * t };
}

/** Yaw change for one frame from ← / →; positive turns left, like the yaw itself. */
export function turnDelta(held: ReadonlySet<Control>, speed: number, dt: number): number {
  if (dt <= 0) return 0;
  return ((held.has("turnLeft") ? 1 : 0) - (held.has("turnRight") ? 1 : 0)) * speed * dt;
}

/** Horizontal displacement for one frame; diagonals are not faster than straight lines. */
export function walkDelta(
  held: ReadonlySet<Control>,
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

  private readonly held = new Set<Control>();
  private active = false;
  private dragging = false;
  private releasing = false;
  private glance: { from: View; to: View; elapsed: number; seconds: number } | null = null;

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
    this.glance = null;
    this.applyView();
  }

  /**
   * Optional framing (docs/DA.md §05): turns the view towards a point over a few seconds.
   * Any mouse movement hands control straight back. Callers skip it under reduced motion.
   */
  glanceAt(target: Vector3, seconds = 1.8): void {
    const to = viewToward(this.camera.position, target);
    this.glance = { from: { ...this.view }, to, elapsed: 0, seconds };
  }

  update(dt: number): void {
    if (!this.active) return;
    if (this.glance && dt > 0) {
      const g = this.glance;
      g.elapsed = Math.min(g.elapsed + dt, g.seconds);
      this.view = blendView(g.from, g.to, ease(g.elapsed / g.seconds));
      this.applyView();
      if (g.elapsed === g.seconds) this.glance = null;
    }
    const turn = turnDelta(this.held, KEY_TURN_SPEED, dt);
    if (turn !== 0) {
      // Like the mouse, the keyboard takes the view back from an ongoing framing glance.
      this.glance = null;
      this.view = { ...this.view, yaw: this.view.yaw + turn };
      this.applyView();
    }
    const delta = walkDelta(this.held, this.view.yaw, this.settings.moveSpeed, dt);
    const p = this.camera.position;
    const next = this.collisions.move({ x: p.x, z: p.z }, delta);
    p.set(next.x, this.eyeHeight, next.z);
  }

  private applyView(): void {
    this.camera.rotation.set(this.view.pitch, this.view.yaw, 0, "YXZ");
  }

  private readonly onKeyDown = (event: KeyboardEvent) => {
    const control = KEY_BINDINGS[event.code];
    if (!control || !this.active) return;
    this.held.add(control);
    event.preventDefault();
  };

  private readonly onKeyUp = (event: KeyboardEvent) => {
    const control = KEY_BINDINGS[event.code];
    if (control) this.held.delete(control);
  };

  private readonly onMouseMove = (event: MouseEvent) => {
    if (!this.active || !(this.locked || this.dragging)) return;
    this.glance = null;
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
