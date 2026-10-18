import { EdgesGeometry, LineBasicMaterial, LineSegments, Mesh, type Object3D } from "three";
import { shelfNodes } from "../../core/assetContract";
import { CHAIN_IDS, type ChainId } from "../../core/chain";

export interface ScanTarget {
  chainId: ChainId;
  /** Invisible SCAN_* volume hit by the aiming ray. */
  volume: Object3D;
  shelfRoot: Object3D;
  /** Thin contour shown while the shelf is aimed at (docs/DA.md §05). */
  outline: LineSegments;
}

/** Scannable shelves present in the store, with their contour ready (hidden). */
export function findScanTargets(storeRoot: Object3D): ScanTarget[] {
  const targets: ScanTarget[] = [];
  for (const chainId of CHAIN_IDS) {
    const names = shelfNodes(chainId);
    const shelfRoot = storeRoot.getObjectByName(names.root);
    const volume = shelfRoot?.getObjectByName(names.scan);
    if (!shelfRoot || !(volume instanceof Mesh) || !volume.parent) continue;

    const outline = new LineSegments(
      new EdgesGeometry(volume.geometry),
      new LineBasicMaterial({ color: "#3f5a3c", transparent: true, opacity: 0.85 }),
    );
    outline.name = `${names.scan}_OUTLINE`;
    outline.position.copy(volume.position);
    outline.quaternion.copy(volume.quaternion);
    outline.scale.copy(volume.scale).multiplyScalar(1.01);
    outline.visible = false;
    volume.parent.add(outline);

    targets.push({ chainId, volume, shelfRoot, outline });
  }
  return targets;
}
