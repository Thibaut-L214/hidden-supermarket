import type { Object3D } from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { checkContract, isHiddenHelper, type AssetContract } from "./assetContract";

export class AssetError extends Error {
  constructor(
    readonly url: string,
    message: string,
  ) {
    super(message);
    this.name = "AssetError";
  }
}

/** Loads GLB files, checks them against their naming contract and hides helper volumes. */
export class AssetManager {
  private readonly loader = new GLTFLoader();
  private readonly cache = new Map<string, Promise<Object3D>>();

  load(contract: AssetContract): Promise<Object3D> {
    let pending = this.cache.get(contract.url);
    if (!pending) {
      pending = this.loadUncached(contract);
      // A failed load must stay retryable (docs/GDD.md §05).
      pending.catch(() => this.cache.delete(contract.url));
      this.cache.set(contract.url, pending);
    }
    return pending;
  }

  private async loadUncached(contract: AssetContract): Promise<Object3D> {
    let root: Object3D;
    try {
      root = (await this.loader.loadAsync(contract.url)).scene;
    } catch (cause) {
      throw new AssetError(contract.url, `chargement impossible (${String(cause)})`);
    }

    const nodes: { name: string; parentName: string | null }[] = [];
    root.traverse((object) => {
      if (object !== root && object.name) {
        nodes.push({ name: object.name, parentName: object.parent?.name || null });
      }
      if (isHiddenHelper(object.name)) object.visible = false;
    });
    const errors = checkContract(nodes, contract);
    if (errors.length > 0) throw new AssetError(contract.url, errors.join(" ; "));
    return root;
  }
}
