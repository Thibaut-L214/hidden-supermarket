// Satin reflection of the store floor (docs/DA.md §02 A: « sol clair légèrement satiné »).
// The scene is drawn once more from the camera mirrored under the floor, into a small target
// whose mip chain gives the blur; the floor material then adds that image at grazing angles,
// rougher tiles reflecting less and more blurred. Skipped in reduced quality and whenever the
// player is not standing on the floor.
import {
  HalfFloatType,
  LinearFilter,
  LinearMipmapLinearFilter,
  Matrix4,
  Mesh,
  MeshStandardMaterial,
  type Object3D,
  PerspectiveCamera,
  Plane,
  type Scene,
  Vector3,
  Vector4,
  WebGLRenderTarget,
  type WebGLRenderer,
} from "three";

const SIZE = 512;
/** Share of the mirrored image added head-on and at grazing angles. */
const FACING = 0.035;
const GRAZING = 0.7;
/** Metres around the floor's outline where the reflection is still drawn. */
const MARGIN = 0.5;
const UP = new Vector3(0, 1, 0);

/** Mirror image of a point in the horizontal plane at `height`. */
export function mirrorPoint(point: Vector3, height: number, out = new Vector3()): Vector3 {
  return out.set(point.x, 2 * height - point.y, point.z);
}

export class FloorReflection {
  private readonly target = new WebGLRenderTarget(SIZE, SIZE, {
    type: HalfFloatType,
    generateMipmaps: true,
    minFilter: LinearMipmapLinearFilter,
    magFilter: LinearFilter,
  });
  private readonly mirror = new PerspectiveCamera();
  private readonly uniforms = {
    uFloorMirror: { value: this.target.texture },
    uFloorMatrix: { value: new Matrix4() },
    uFloorStrength: { value: 0 },
  };
  private readonly floors: Mesh[] = [];
  private readonly height: number;
  private readonly bounds: { minX: number; maxX: number; minZ: number; maxZ: number };

  /** @param floor the flat, horizontal floor mesh; meshes sharing its material reflect too. */
  constructor(root: Object3D, floor: Mesh) {
    const material = floor.material;
    if (!(material instanceof MeshStandardMaterial)) throw new Error("Sol sans matériau standard");
    floor.geometry.computeBoundingBox();
    const box = floor.geometry.boundingBox!.clone().applyMatrix4(floor.matrixWorld);
    this.height = box.max.y;
    this.bounds = { minX: box.min.x, maxX: box.max.x, minZ: box.min.z, maxZ: box.max.z };
    root.traverse((object) => {
      if (object instanceof Mesh && object.material === material) this.floors.push(object);
    });
    this.patch(material);
  }

  private patch(material: MeshStandardMaterial): void {
    material.onBeforeCompile = (shader) => {
      Object.assign(shader.uniforms, this.uniforms);
      shader.vertexShader = shader.vertexShader
        .replace(
          "#include <common>",
          `#include <common>
          uniform mat4 uFloorMatrix;
          varying vec4 vFloorUv;`,
        )
        .replace(
          "#include <project_vertex>",
          `#include <project_vertex>
          vFloorUv = uFloorMatrix * modelMatrix * vec4(transformed, 1.0);`,
        );
      shader.fragmentShader = shader.fragmentShader
        .replace(
          "#include <common>",
          `#include <common>
          uniform sampler2D uFloorMirror;
          uniform float uFloorStrength;
          varying vec4 vFloorUv;`,
        )
        .replace(
          "#include <opaque_fragment>",
          `
          // The normal map ripples the image; roughness blurs it through the mip chain.
          vec3 floorNormal = inverseTransformDirection(normal, viewMatrix);
          vec2 floorUv = vFloorUv.xy / vFloorUv.w + floorNormal.xz * 0.03;
          float floorFresnel = pow(1.0 - saturate(dot(geometryViewDir, normal)), 4.0);
          vec3 floorImage = texture2D(uFloorMirror, floorUv, 1.0 + roughnessFactor * 5.0).rgb;
          outgoingLight += floorImage * uFloorStrength * (1.0 - roughnessFactor)
            * mix(${FACING.toFixed(3)}, ${GRAZING.toFixed(3)}, floorFresnel);
          #include <opaque_fragment>`,
        );
    };
    material.customProgramCacheKey = () => "floor-reflection";
    material.needsUpdate = true;
  }

  /** Whether a camera at this position sees the floor from above, standing on it. */
  covers(position: Vector3): boolean {
    const { minX, maxX, minZ, maxZ } = this.bounds;
    return (
      position.y > this.height &&
      position.x > minX - MARGIN &&
      position.x < maxX + MARGIN &&
      position.z > minZ - MARGIN &&
      position.z < maxZ + MARGIN
    );
  }

  /**
   * Draws the mirrored view; call before the main render. `follow` re-centres what tracks the
   * camera (the sky dome) on the mirrored one, then back.
   */
  render(
    renderer: WebGLRenderer,
    scene: Scene,
    camera: PerspectiveCamera,
    enabled: boolean,
    follow: (position: Vector3) => void,
  ): void {
    const active = enabled && this.covers(camera.position);
    this.uniforms.uFloorStrength.value = active ? 1 : 0;
    if (!active) return;

    const mirror = this.mirror;
    const rotation = new Matrix4().extractRotation(camera.matrixWorld);
    const ahead = new Vector3(0, 0, -1).applyMatrix4(rotation).add(camera.position);
    mirrorPoint(camera.position, this.height, mirror.position);
    mirror.up.set(0, 1, 0).applyMatrix4(rotation).reflect(UP);
    mirror.lookAt(mirrorPoint(ahead, this.height));
    mirror.updateMatrixWorld();
    mirror.projectionMatrix.copy(camera.projectionMatrix);
    this.uniforms.uFloorMatrix.value
      .set(0.5, 0, 0, 0.5, 0, 0.5, 0, 0.5, 0, 0, 0.5, 0.5, 0, 0, 0, 1)
      .multiply(mirror.projectionMatrix)
      .multiply(mirror.matrixWorldInverse);

    // Oblique near plane on the floor (Lengyel): nothing under it leaks into the image.
    const plane = new Plane()
      .setFromNormalAndCoplanarPoint(UP, new Vector3(0, this.height, 0))
      .applyMatrix4(mirror.matrixWorldInverse);
    const clip = new Vector4(plane.normal.x, plane.normal.y, plane.normal.z, plane.constant);
    const p = mirror.projectionMatrix.elements;
    const q = new Vector4(
      (Math.sign(clip.x) + p[8]!) / p[0]!,
      (Math.sign(clip.y) + p[9]!) / p[5]!,
      -1,
      (1 + p[10]!) / p[14]!,
    );
    clip.multiplyScalar(2 / clip.dot(q));
    p[2] = clip.x;
    p[6] = clip.y;
    p[10] = clip.z + 1 - 0.003;
    p[14] = clip.w;

    // Shadow maps are already current for this frame; re-rendering them per pass is wasted.
    const lights: { shadow: { autoUpdate: boolean } }[] = [];
    scene.traverse((object) => {
      const shadow = (object as { shadow?: { autoUpdate: boolean } }).shadow;
      if (shadow?.autoUpdate) lights.push({ shadow });
    });
    for (const light of lights) light.shadow.autoUpdate = false;
    for (const floor of this.floors) floor.visible = false;
    follow(mirror.position);
    const previous = renderer.getRenderTarget();
    renderer.setRenderTarget(this.target);
    renderer.clear();
    renderer.render(scene, mirror);
    renderer.setRenderTarget(previous);
    follow(camera.position);
    for (const floor of this.floors) floor.visible = true;
    for (const light of lights) light.shadow.autoUpdate = true;
  }
}
