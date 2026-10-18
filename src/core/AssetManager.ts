import type { Object3D, WebGLRenderer } from "three";
import { MeshoptDecoder } from "three/addons/libs/meshopt_decoder.module.js";
import { type GLTF, GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { KTX2Loader } from "three/addons/loaders/KTX2Loader.js";
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
  private readonly loader = new GLTFLoader().setMeshoptDecoder(MeshoptDecoder);
  private readonly cache = new Map<string, Promise<Object3D>>();
  /** Load and validation time of each asset, in milliseconds (docs/TECH.md §07). */
  readonly timings = new Map<string, number>();

  /**
   * GLBs are meshopt-compressed by scripts/optimize-glb.mjs; KTX2 textures, when present, are
   * transcoded with the Basis files copied to /basis/ (scripts/copy-basis.mjs).
   */
  constructor(renderer?: WebGLRenderer) {
    if (renderer) {
      this.loader.setKTX2Loader(
        new KTX2Loader().setTranscoderPath("/basis/").detectSupport(renderer),
      );
    }
  }

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
    const started = performance.now();
    let gltf: GLTF;
    try {
      gltf = await this.loader.loadAsync(contract.url);
    } catch (cause) {
      throw new AssetError(contract.url, `chargement impossible (${String(cause)})`);
    }
    const root = gltf.scene;

    // Only objects created for glTF nodes count: three also creates one child per primitive
    // of a multi-material mesh, and a mesh shared by several nodes repeats those names.
    const isNode = (object: Object3D) => gltf.parser.associations.get(object)?.nodes !== undefined;
    const nodes: { name: string; parentName: string | null }[] = [];
    root.traverse((object) => {
      if (object !== root && object.name && isNode(object)) {
        nodes.push({ name: object.name, parentName: object.parent?.name || null });
      }
      if (isHiddenHelper(object.name)) object.visible = false;
    });
    const errors = checkContract(nodes, contract);
    if (errors.length > 0) throw new AssetError(contract.url, errors.join(" ; "));
    this.timings.set(contract.url, performance.now() - started);
    return root;
  }
}
