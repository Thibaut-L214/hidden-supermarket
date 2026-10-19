import { NodeIO, type Document, type Node } from "@gltf-transform/core";
import { ALL_EXTENSIONS } from "@gltf-transform/extensions";
import { MeshoptDecoder } from "meshoptimizer";
import {
  Box3,
  BufferAttribute,
  BufferGeometry,
  DoubleSide,
  Group,
  Mesh,
  MeshBasicMaterial,
  type Object3D,
  Vector3,
} from "three";
import { beforeAll, describe, expect, it } from "vitest";
import { beef } from "../src/data/chains/beef";
import { ChainTimeline } from "../src/features/chains/ChainTimeline";
import { evaluate, totalDuration } from "../src/features/chains/TimelineDirector";
import { ShelfDoor } from "../src/features/portal/ShelfDoor";
import { findScanTargets } from "../src/features/scanner/ScanTarget";
import { CollisionWorld } from "../src/world/CollisionWorld";

let store: Document;
let terrace: Document;

beforeAll(async () => {
  await MeshoptDecoder.ready;
  const io = new NodeIO()
    .registerExtensions(ALL_EXTENSIONS)
    .registerDependencies({ "meshopt.decoder": MeshoptDecoder });
  [store, terrace] = await Promise.all([
    io.read("public/assets/store/store.glb"),
    io.read("public/assets/beef/terrace_beef.glb"),
  ]);
});

/** Load actual exported geometry and transforms without a browser texture decoder.
 * No fabricated collider, animal slot or waypoint: those all come from the shipped GLBs.
 */
function scene(doc: Document): Group {
  const material = new MeshBasicMaterial({ side: DoubleSide });
  const objects = new Map<Node, Object3D>();
  for (const node of doc.getRoot().listNodes()) {
    const meshes = (node.getMesh()?.listPrimitives() ?? []).map((primitive) => {
      const geometry = new BufferGeometry();
      const positions = primitive.getAttribute("POSITION")!;
      geometry.setAttribute(
        "position",
        new BufferAttribute(new Float32Array(positions.getArray()!), 3, positions.getNormalized()),
      );
      const indices = primitive.getIndices();
      if (indices) geometry.setIndex(new BufferAttribute(new Uint32Array(indices.getArray()!), 1));
      return new Mesh(geometry, material);
    });
    const object = meshes.length === 1 ? meshes[0]! : new Group();
    if (meshes.length > 1) object.add(...meshes);
    object.name = node.getName();
    object.position.fromArray(node.getTranslation());
    object.quaternion.fromArray(node.getRotation());
    object.scale.fromArray(node.getScale());
    objects.set(node, object);
  }
  const root = new Group();
  for (const [node, object] of objects) {
    const parent = node.getParentNode();
    (parent ? objects.get(parent)! : root).add(object);
  }
  root.updateMatrixWorld(true);
  return root;
}

describe("exported beef route", () => {
  it("identifies steaks and minced beef separately on the exported product signs", () => {
    const signs = store
      .getRoot()
      .listNodes()
      .filter((node) => node.getName().startsWith("PRODUCT_SIGN_BEEF_"));
    expect(signs.map((node) => node.getExtras().label).sort()).toEqual(["Steaks", "Viande hachée"]);
  });

  it("centres product sign geometry on its origin so labels stay on the plates", () => {
    const root = scene(store);
    for (const name of ["PRODUCT_SIGN_BEEF_STEAK", "PRODUCT_SIGN_BEEF_MINCE"]) {
      const sign = root.getObjectByName(name)!;
      const centre = new Box3().setFromObject(sign).getCenter(new Vector3());
      expect(centre.distanceTo(sign.getWorldPosition(new Vector3()))).toBeLessThan(0.001);
    }
  });

  it("aligns the livestock truck's rear deck with its loading ramp before any animal moves", () => {
    const root = scene(terrace);
    new ChainTimeline(root, beef.timeline);
    const truck = root.getObjectByName("TRUCK_BEEF_ANIMALS")!;
    const rear = truck.localToWorld(new Vector3(0, 0.9, 4.3));
    const rampTop = root.getObjectByName("PATH_BEEF_LOAD_05")!.getWorldPosition(new Vector3());
    expect(rear.distanceTo(rampTop)).toBeLessThan(0.15);
  });

  it("keeps walking cattle clear of fixed farm, waiting and approach barriers", () => {
    const root = scene(terrace);
    const timeline = new ChainTimeline(root, beef.timeline);
    const fences: { name: string; bounds: Box3 }[] = [];
    root.traverse((object) => {
      if (/^BEEF_(LANE_|WAITING_RAIL_|APPROACH_RAIL_|FEED_BARRIER)/.test(object.name)) {
        fences.push({
          name: object.name,
          bounds: new Box3().setFromObject(object).expandByVector(new Vector3(0.3, 0, 0.3)),
        });
      }
    });
    expect(fences.length).toBeGreaterThan(5);
    let elapsed = 0;
    const crossings = new Set<string>();
    for (const step of beef.timeline) {
      if (step.event === "walk") {
        for (let sample = 0; sample <= 120; sample++) {
          timeline.apply(evaluate(beef.timeline, elapsed + (step.durationSec * sample) / 120));
          const target = root.getObjectByName(step.to!)!;
          for (const animal of target.children.filter((object) => object.visible)) {
            const centre = animal.getWorldPosition(new Vector3()).add(new Vector3(0, 0.8, 0));
            for (const fence of fences) {
              if (fence.bounds.containsPoint(centre)) crossings.add(`${step.id}: ${fence.name}`);
            }
          }
        }
      }
      elapsed += step.durationSec;
    }
    expect([...crossings]).toEqual([]);
  });

  it("offers both shelves to the scanner and opens a traversable beef doorway", () => {
    const root = scene(store);
    expect(findScanTargets(root).map((target) => target.chainId)).toEqual(["eggs", "beef"]);
    const collisions = new CollisionWorld();
    collisions.addFrom(root);
    const start = { x: 6, z: -6 };
    const closed = collisions.move(start, { x: 0, z: -6 });
    expect(closed.z).toBeGreaterThan(-8.5);
    const door = new ShelfDoor(root.getObjectByName("SHELF_BEEF_ROOT")!, "beef");
    door.update(3, "open");
    collisions.refresh();
    const opened = collisions.move(start, { x: 0, z: -6 });
    expect(opened.x).toBeCloseTo(6);
    expect(opened.z).toBeCloseTo(-12);
    door.snapClosed();
    collisions.refresh();
    expect(collisions.move(start, { x: 0, z: -6 }).z).toBeCloseTo(closed.z);
  });

  it("encloses the terrace on all sides except its store threshold", () => {
    const root = scene(terrace);
    const collisions = new CollisionWorld();
    collisions.addFrom(root);
    const from = { x: 0, z: -3 };
    expect(collisions.move(from, { x: 0, z: -10 }).z).toBeGreaterThan(-7);
    expect(collisions.move(from, { x: 10, z: 0 }).x).toBeLessThan(6);
    expect(collisions.move(from, { x: -10, z: 0 }).x).toBeGreaterThan(-6);
    expect(collisions.move(from, { x: 0, z: 5 }).z).toBeCloseTo(2);
  });

  it("moves all six cattle through actual exported routes and restores them on replay", () => {
    const root = scene(terrace);
    const timeline = new ChainTimeline(root, beef.timeline);
    const names = [
      "CATTLE_BEEF_FARM",
      "CATTLE_BEEF_TRUCK",
      "CATTLE_BEEF_WAITING",
      "CATTLE_BEEF_APPROACH",
    ];
    const groups = names.map((name) => root.getObjectByName(name)!);
    expect(groups.map((group) => group.children.length)).toEqual([6, 6, 6, 6]);
    for (const [seconds, counts] of [
      [0, [6, 0, 0, 0]],
      [10, [0, 6, 0, 0]],
      [30, [0, 0, 6, 0]],
      [39, [0, 0, 0, 6]],
      [48, [0, 0, 0, 0]],
    ] as const) {
      timeline.apply(evaluate(beef.timeline, seconds));
      expect(
        groups.map((group) => group.children.filter((animal) => animal.visible).length),
      ).toEqual(counts);
    }
    timeline.apply(evaluate(beef.timeline, 23));
    const first = groups[2]!.children[0]!;
    const pose = first.getWorldPosition(new Vector3()).toArray();
    timeline.apply(evaluate(beef.timeline, totalDuration(beef.timeline)));
    expect(
      root.getObjectByName("CARGO_BEEF_DELIVERY")!.children.every((unit) => !unit.visible),
    ).toBe(true);
    timeline.apply(null);
    expect(groups[0]!.children.every((animal) => animal.visible)).toBe(true);
    timeline.apply(evaluate(beef.timeline, 23));
    expect(first.getWorldPosition(new Vector3()).toArray()).toEqual(pose);
  });
});
