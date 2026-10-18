import { PMREMGenerator, PerspectiveCamera, Scene } from "three";
import { RoomEnvironment } from "three/addons/environments/RoomEnvironment.js";
import { AssetError, AssetManager } from "../core/AssetManager";
import { EventBus } from "../core/EventBus";
import { GameClock } from "../core/GameClock";
import { GameState, canWalk, type GameEvents } from "../core/GameState";
import { IntroScreen } from "../ui/IntroScreen";
import { PauseMenu } from "../ui/PauseMenu";
import { CollisionWorld } from "../world/CollisionWorld";
import { FPSController } from "../world/FPSController";
import { EYE_HEIGHT, StoreWorld } from "../world/StoreWorld";
import { createRenderer } from "./renderer";
import { Session, trackExploration } from "./session";
import { defaultSettings } from "./settings";

function element<T extends HTMLElement>(selector: string): T {
  const found = document.querySelector<T>(selector);
  if (!found) throw new Error(`index.html : ${selector} manquant`);
  return found;
}

const canvas = element<HTMLCanvasElement>("#scene");
const status = element<HTMLParagraphElement>("#status");
const reticle = element<HTMLDivElement>("#reticle");

// Rendering
const renderer = createRenderer(canvas);
const scene = new Scene();
// Soft image-based lighting for PBR materials; no HDR file to ship.
const pmrem = new PMREMGenerator(renderer);
scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
scene.environmentIntensity = 0.5;
pmrem.dispose();
const camera = new PerspectiveCamera(70, 1, 0.05, 500);

function resize(): void {
  renderer.setSize(canvas.clientWidth, canvas.clientHeight, false);
  camera.aspect = canvas.clientWidth / canvas.clientHeight;
  camera.updateProjectionMatrix();
}
window.addEventListener("resize", resize);
resize();

// Game systems
const settings = defaultSettings(matchMedia("(prefers-reduced-motion: reduce)").matches);
const bus = new EventBus<GameEvents>();
const game = new GameState(bus);
const session = new Session();
trackExploration(bus, session);
const clock = new GameClock();
const collisions = new CollisionWorld();
const fps = new FPSController(camera, canvas, collisions, settings, EYE_HEIGHT);

// Pause is a flag orthogonal to the game state (docs/DECISIONS.md).
const pauseMenu = new PauseMenu(element("#pause"), settings, resume);
const intro = new IntroScreen(element("#intro"), settings, () => {
  game.send({ type: "START" });
  resume();
});
clock.setPaused("menu", true);

function pause(): void {
  if (pauseMenu.visible || !canWalk(game.snapshot.state)) return;
  clock.setPaused("menu", true);
  fps.deactivate();
  reticle.hidden = true;
  pauseMenu.show();
}

function resume(): void {
  pauseMenu.hide();
  reticle.hidden = false;
  clock.setPaused("menu", false);
  void fps.activate();
}

fps.onLockLost = pause;
document.addEventListener("keydown", (event) => {
  if (event.code !== "KeyP" || event.repeat) return;
  if (pauseMenu.visible) resume();
  else pause();
});
document.addEventListener("visibilitychange", () => clock.setPaused("hidden", document.hidden));

function showStatus(message: string, kind: "info" | "error" = "info"): void {
  status.textContent = message;
  status.dataset.kind = kind;
}

async function start(): Promise<void> {
  try {
    const store = await StoreWorld.load(new AssetManager(), scene);
    collisions.addFrom(store.root);
    const spawn = store.spawnPose();
    fps.setPose(spawn.position, spawn.yaw);
    showStatus("");
    intro.setReady();
  } catch (error) {
    const detail = error instanceof AssetError ? `${error.url} : ${error.message}` : String(error);
    showStatus(`Impossible de charger le magasin. ${detail}`, "error");
    intro.setFailed();
    console.error(error);
  }
  renderer.setAnimationLoop((now) => {
    fps.update(clock.tick(now));
    renderer.render(scene, camera);
  });
}

if (import.meta.env.DEV) {
  Object.assign(window, { __dlr: { game, session, clock, fps, collisions, camera, settings } });
}

void start();
