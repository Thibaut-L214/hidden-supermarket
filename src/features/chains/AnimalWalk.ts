import { type Object3D, Quaternion, Vector3 } from "three";

/** Share of the step during which one animal traverses the corridor. */
const WALK_WINDOW = 0.4;

/** Grounded movement through a corridor, including ramps. Animal origins sit at hoof level.
 * Every pose comes from progress, so pause, seeking and replay never accumulate movement.
 */
export class AnimalWalk {
  private readonly rest = new Map<Object3D, { position: Vector3; rotation: Quaternion }>();
  private readonly legs = new Map<Object3D, { joint: Object3D; angle: number }[]>();

  constructor(
    private readonly root: Object3D,
    private readonly from: readonly Object3D[],
    private readonly to: readonly Object3D[],
    private readonly waypoints: readonly Vector3[],
    private readonly reducedMotion: () => boolean,
  ) {
    if (from.length === 0 || from.length !== to.length) {
      throw new Error("Marche : les groupes doivent contenir le même nombre d’animaux, non nul.");
    }
    for (const animal of to) {
      this.rest.set(animal, {
        position: animal.position.clone(),
        rotation: animal.quaternion.clone(),
      });
      const legs: { joint: Object3D; angle: number }[] = [];
      animal.traverse((joint) => {
        if (joint.name.startsWith("CATTLE_LEG_")) legs.push({ joint, angle: joint.rotation.x });
      });
      this.legs.set(animal, legs);
    }
  }

  reset(): void {
    for (const [animal, rest] of this.rest) {
      animal.position.copy(rest.position);
      animal.quaternion.copy(rest.rotation);
      for (const { joint, angle } of this.legs.get(animal)!) joint.rotation.x = angle;
    }
  }

  apply(progress: number): void {
    this.from.forEach((source, i) => {
      const start = (i / this.from.length) * (1 - WALK_WINDOW);
      const q = Math.min(Math.max((progress - start) / WALK_WINDOW, 0), 1);
      const animal = this.to[i]!;
      source.visible = q === 0;
      animal.visible = q > 0;
      if (q > 0 && q < 1) this.place(source, animal, q);
    });
  }

  private place(source: Object3D, animal: Object3D, q: number): void {
    const parent = animal.parent!;
    parent.updateWorldMatrix(true, false);
    const points = [
      parent.worldToLocal(source.getWorldPosition(new Vector3())),
      ...this.waypoints.map((point) => parent.worldToLocal(this.root.localToWorld(point.clone()))),
      this.rest.get(animal)!.position,
    ];
    const lengths = points.slice(1).map((point, i) => point.distanceTo(points[i]!));
    const total = lengths.reduce((sum, length) => sum + length, 0);
    let distance = total * q;
    for (let i = 0; i < lengths.length; i++) {
      const length = lengths[i]!;
      if (distance > length && i < lengths.length - 1) {
        distance -= length;
        continue;
      }
      animal.position.lerpVectors(points[i]!, points[i + 1]!, length ? distance / length : 1);
      const tangent = points[i + 1]!.clone().sub(points[i]!);
      if (Math.hypot(tangent.x, tangent.z) > 1e-6) {
        animal.rotation.set(0, Math.atan2(-tangent.x, -tangent.z), 0);
      }
      if (!this.reducedMotion()) {
        this.legs.get(animal)!.forEach(({ joint, angle }, leg) => {
          joint.rotation.x = angle + Math.sin(total * q * 5 + (leg % 2) * Math.PI) * 0.22;
        });
      }
      return;
    }
  }
}
