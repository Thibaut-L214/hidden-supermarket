// Applies a timeline state to a terrace module. The scene is rebuilt from its start state on
// every frame (start state, then every begun step in order), never moved incrementally: any
// time gives one pose, whatever happened before (docs/TECH.md §05, replay).
import {
  CatmullRomCurve3,
  ConeGeometry,
  Mesh,
  MeshBasicMaterial,
  type Object3D,
  Vector3,
} from "three";
import { ease } from "../../core/easing";
import type { TimelineStep } from "./ChainModule";
import type { TimelineState } from "./TimelineDirector";

/** Height of the guide marker above its target, in metres. */
const MARKER_HEIGHT = 6;

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
  /** Discreet guide above the step under way (docs/DA.md §05: graphic links, no dashboard). */
  readonly marker: Mesh;
  private readonly tangent = new Vector3();
  private readonly world = new Vector3();

  constructor(
    private readonly root: Object3D,
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
      if (step.event === "drive" && step.vehicle && step.pathId) {
        const vehicle = find(step.vehicle);
        const points = pathPoints(root, step.pathId, vehicle.parent ?? root);
        if (points.length < 2) throw new Error(`${step.pathId} : au moins deux points requis`);
        this.paths.set(step.pathId, new CatmullRomCurve3(points, false, "centripetal"));
        this.vehicles.set(step.vehicle, vehicle);
      }
    }

    this.marker = new Mesh(
      new ConeGeometry(0.9, 1.8, 16).rotateX(Math.PI),
      new MeshBasicMaterial({ color: "#5f8a58", transparent: true, opacity: 0.85, fog: false }),
    );
    this.marker.name = "TIMELINE_MARKER";
    this.marker.visible = false;
    root.add(this.marker);
    this.apply(null);
  }

  /** Poses the module for a timeline state; null gives the start state with no guide. */
  apply(state: TimelineState | null): void {
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
    this.placeMarker(state);
  }

  private applyStep(step: TimelineStep, p: number): void {
    if (step.event === "drive") {
      this.drive(step, ease(p));
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

  private drive(step: TimelineStep, u: number): void {
    const curve = this.paths.get(step.pathId!);
    const vehicle = this.vehicles.get(step.vehicle!);
    if (!curve || !vehicle) return;
    curve.getPointAt(u, vehicle.position);
    curve.getTangentAt(Math.min(u, 0.999), this.tangent);
    // Vehicles face their local -Z (Blender +Y).
    vehicle.rotation.set(0, Math.atan2(-this.tangent.x, -this.tangent.z), 0);
  }

  private placeMarker(state: TimelineState | null): void {
    const step = state && !state.done ? this.steps[state.active] : undefined;
    const name = step && (step.vehicle ?? step.to ?? step.from);
    const target = name ? (this.vehicles.get(name) ?? this.root.getObjectByName(name)) : undefined;
    this.marker.visible = Boolean(target);
    if (!target) return;
    target.getWorldPosition(this.world);
    this.root.worldToLocal(this.world);
    this.marker.position.set(this.world.x, this.world.y + MARKER_HEIGHT, this.world.z);
  }
}
