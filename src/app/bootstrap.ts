import { PMREMGenerator, PerspectiveCamera, Scene, Vector3 } from "three";
import { RoomEnvironment } from "three/addons/environments/RoomEnvironment.js";
import { AssetError, AssetManager } from "../core/AssetManager";
import { StoreWorld } from "../world/StoreWorld";
import { createRenderer } from "./renderer";

const canvas = document.querySelector<HTMLCanvasElement>("#scene");
const status = document.querySelector<HTMLParagraphElement>("#status");
if (!canvas || !status) throw new Error("index.html : #scene ou #status manquant");

const renderer = createRenderer(canvas);
const scene = new Scene();
scene.background = null;
// Soft image-based lighting for PBR materials; no HDR file to ship.
const pmrem = new PMREMGenerator(renderer);
scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
scene.environmentIntensity = 0.5;
pmrem.dispose();

const camera = new PerspectiveCamera(70, 1, 0.05, 500);

function resize(): void {
  const { clientWidth: w, clientHeight: h } = canvas!;
  renderer.setSize(w, h, false);
  camera.aspect = w / h;
  camera.updateProjectionMatrix();
}
window.addEventListener("resize", resize);
resize();

function showStatus(message: string, kind: "info" | "error" = "info"): void {
  status!.textContent = message;
  status!.dataset.kind = kind;
}

async function start(): Promise<void> {
  const assets = new AssetManager();
  try {
    const store = await StoreWorld.load(assets, scene);
    const eye = store.spawnEye();
    camera.position.copy(eye);
    camera.lookAt(eye.clone().add(new Vector3(0, 0, -1)));
    showStatus("");
  } catch (error) {
    const detail = error instanceof AssetError ? `${error.url} : ${error.message}` : String(error);
    showStatus(`Impossible de charger le magasin. ${detail}`, "error");
    console.error(error);
  }
  renderer.setAnimationLoop(() => renderer.render(scene, camera));
}

void start();
