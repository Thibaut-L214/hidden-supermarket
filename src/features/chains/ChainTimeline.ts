// Applies a timeline state to a terrace module. The scene is rebuilt from its start state on
// every frame (start state, then every begun step in order), never moved incrementally: any
// time gives one pose, whatever happened before (docs/TECH.md §05, replay).
import {
  Box3,
  CatmullRomCurve3,
  type Object3D,
  Vector3,
} from "three";
import { ease } from "../../core/easing";
import type { TimelineStep } from "./ChainModule";
import type { TimelineState } from "./TimelineDirector";

/** Share of a carry step during which one unit is on its way; units start one after another. */
const CARRY_WINDOW = 0.4;
/** Height of the arc a carried unit follows, in metres. */
const CARRY_ARC = 0.7;

/** Visible-count of a group's units for a share in [0, 1]. */
export function unitsShown(total: number, share: number): number {
  return Math.round(total * Math.min(Math.max(share, 0), 1));
}

/**
 * Ordered PATH_<id>_<NN> points anywhere under root, expressed in `space`'s local frame (the
 * vehicle's parent, so positions can be assigned to the vehicle directly).
 */
export function pathPoints(root: Object3D, pathId: string, space: Object3D = root): Vector3[] {
  const points: { index: number; position: Vector3 }[] = [];
  const pattern = new RegExp(`^${pathId}_(\\d+)$`);
  root.updateWorldMatrix(true, true);
  root.traverse((object) => {
    const match = pattern.exec(object.name);
    if (!match) return;
    const position = space.worldToLocal(object.getWorldPosition(new Vector3()));
    points.push({ index: Number(match[1]), position });
  });
  return points.sort((a, b) => a.index - b.index).map((p) => p.position);
}

export class ChainTimeline {
  private readonly groups = new Map<string, Object3D[]>();
  private readonly paths = new Map<string, CatmullRomCurve3>();
  private readonly vehicles = new Map<string, Object3D>();
  /** Groups whose units are present before anything happens (sources nobody fills). */
  private readonly initiallyFull = new Set<string>();
  private readonly tangent = new Vector3();
  /** Rest position of every unit that a carry step moves, restored on each apply. */
  private readonly rest = new Map<Object3D, Vector3>();
  private readonly box = new Box3();

  constructor(
    root: Object3D,
    private readonly steps: readonly TimelineStep[],
  ) {
    const find = (name: string) => {
      const object = root.getObjectByName(name);
      if (!object) throw new Error(`${name} absent du module`);
      return object;
    };
    const filled = new Set(steps.flatMap((s) => (s.to ? [s.to] : [])));
    for (const step of steps) {
      for (const name of [step.from, step.to]) {
        if (name && !this.groups.has(name)) {
          this.groups.set(name, [...find(name).children]);
          if (!filled.has(name)) this.initiallyFull.add(name);
        }
      }
      if (step.carry && step.to) {
        for (const unit of this.groups.get(step.to) ?? []) this.rest.set(unit, unit.position.clone());
      }
      if (step.event === "drive" && step.vehicle && step.pathId) {
        const vehicle = find(step.vehicle);
        const points = pathPoints(root, step.pathId, vehicle.parent ?? root);
        if (points.length < 2) throw new Error(`${step.pathId} : au moins deux points requis`);
        this.paths.set(step.pathId, new CatmullRomCurve3(points, false, "centripetal"));
        this.vehicles.set(step.vehicle, vehicle);
      }
    }

    this.apply(null);
  }

  /** Poses the module for a timeline state; null gives the start state. */
  apply(state: TimelineState | null): void {
    for (const [unit, position] of this.rest) unit.position.copy(position);
    for (const [name, units] of this.groups) {
      const shown = this.initiallyFull.has(name) ? units.length : 0;
      units.forEach((unit, i) => (unit.visible = i < shown));
    }
    for (const step of this.steps) {
      if (step.event === "drive") this.drive(step, 0);
    }

    if (state) {
      this.steps.forEach((step, i) => {
        const p = state.progress[i] ?? 0;
        if (p > 0) this.applyStep(step, p);
      });
    }
  }

  private applyStep(step: TimelineStep, p: number): void {
    if (step.event === "drive") {
      this.drive(step, ease(p));
      return;
    }
    if (step.carry && step.from && step.to) {
      this.carry(step, p);
      return;
    }
    if (step.from) {
      const units = this.groups.get(step.from)!;
      const remaining = units.length - unitsShown(units.length, p);
      units.forEach((unit, i) => (unit.visible = i < remaining));
    }
    if (step.to) {
      const units = this.groups.get(step.to)!;
      const shown = unitsShown(units.length, p);
      units.forEach((unit, i) => (unit.visible = i < shown));
    }
  }

  /**
   * Units leave their slot in `from` one after another and arrive in the matching slot of `to`,
   * along a short arc. Units are meshes whose geometry sits at their slot (the origin is the
   * group's), so a unit is moved by the offset between the two slots' centres.
   */
  private carry(step: TimelineStep, p: number): void {
    const from = this.groups.get(step.from!)!;
    const to = this.groups.get(step.to!)!;
    const count = Math.min(from.length, to.length);
    for (let k = 0; k < count; k++) {
      const start = count > 1 ? (k / count) * (1 - CARRY_WINDOW) : 0;
      const q = Math.min(Math.max((p - start) / CARRY_WINDOW, 0), 1);
      const source = from[k]!;
      const target = to[k]!;
      source.visible = q === 0;
      target.visible = q > 0;
      if (q > 0 && q < 1) this.place(source, target, ease(q), q);
    }
  }

  private place(source: Object3D, target: Object3D, e: number, q: number): void {
    const parent = target.parent;
    if (!parent) return;
    source.updateWorldMatrix(true, false);
    target.updateWorldMatrix(true, false);
    const from = this.centre(source, new Vector3());
    const to = this.centre(target, new Vector3());
    // Offset between the slots, in the target's parent frame, shrinking to zero on arrival.
    const offset = parent.worldToLocal(from).sub(parent.worldToLocal(to)).multiplyScalar(1 - e);
    offset.y += Math.sin(Math.PI * q) * CARRY_ARC;
    target.position.copy(this.rest.get(target) ?? target.position).add(offset);
  }

  /** World centre of an object's geometry at its rest pose. */
  private centre(object: Object3D, into: Vector3): Vector3 {
    const rest = this.rest.get(object);
    const moved = rest ? object.position.clone() : null;
    if (rest) object.position.copy(rest);
    object.updateWorldMatrix(true, true);
    this.box.setFromObject(object);
    if (moved) object.position.copy(moved);
    return this.box.getCenter(into);
  }

  private drive(step: TimelineStep, u: number): void {
    const curve = this.paths.get(step.pathId!);
    const vehicle = this.vehicles.get(step.vehicle!);
    if (!curve || !vehicle) return;
    curve.getPointAt(u, vehicle.position);
    curve.getTangentAt(Math.min(u, 0.999), this.tangent);
    // Vehicles face their local -Z (Blender +Y).
    vehicle.rotation.set(0, Math.atan2(-this.tangent.x, -this.tangent.z), 0);
  }
}
