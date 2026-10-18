import { Color, Fog, PMREMGenerator, PerspectiveCamera, Scene } from "three";
import { RoomEnvironment } from "three/addons/environments/RoomEnvironment.js";
import { AssetError, AssetManager } from "../core/AssetManager";
import { EventBus } from "../core/EventBus";
import { GameClock } from "../core/GameClock";
import { GameState, canWalk, type GameEvents } from "../core/GameState";
import { CHAINS } from "../data/chains";
import { TerraceTransition } from "../features/portal/TerraceTransition";
import { findScanTargets } from "../features/scanner/ScanTarget";
import { Scanner } from "../features/scanner/Scanner";
import { HUD } from "../ui/HUD";
import { IntroScreen } from "../ui/IntroScreen";
import { PauseMenu } from "../ui/PauseMenu";
import { beep } from "../ui/sound";
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
// Hazy blue-grey horizon (docs/DA.md §03, terrace); fog starts beyond the store's depth.
const HAZE = new Color("#cfd6d8");
scene.background = HAZE;
scene.fog = new Fog(HAZE, 60, 420);
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
const assets = new AssetManager();
const collisions = new CollisionWorld();
const fps = new FPSController(camera, canvas, collisions, settings, EYE_HEIGHT);
const hud = new HUD(reticle, element("#hud-prompt"), status);

/** Systems that need the loaded store. */
let world: { scanner: Scanner; transition: TerraceTransition } | null = null;

// Pause is a flag orthogonal to the game state (docs/DECISIONS.md).
const pauseMenu = new PauseMenu(element("#pause"), settings, resume, () => {
  resume();
  world?.transition.returnToStore();
});
const intro = new IntroScreen(element("#intro"), settings, () => {
  game.send({ type: "START" });
  resume();
});
clock.setPaused("menu", true);

function pause(): void {
  if (pauseMenu.visible || !canWalk(game.snapshot.state)) return;
  clock.setPaused("menu", true);
  fps.deactivate();
  hud.setVisible(false);
  pauseMenu.show(world?.transition.canReturn ?? false);
}

function resume(): void {
  pauseMenu.hide();
  hud.setVisible(true);
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

function createWorld(store: StoreWorld) {
  const scanner = new Scanner(
    camera,
    findScanTargets(store.root),
    () => collisions.objects,
    canvas,
  );
  scanner.onConfirm = (chainId) => {
    beep();
    hud.alert(`Rayon ${CHAINS[chainId]?.label ?? chainId} scanné.`, 3);
    game.send({ type: "SCAN_CONFIRMED", chainId });
  };
  const transition = new TerraceTransition({
    game,
    bus,
    assets,
    scene,
    collisions,
    storeRoot: store.root,
    chains: CHAINS,
    hud,
    player: {
      radius: collisions.radius,
      position: () => ({ x: camera.position.x, z: camera.position.z }),
      teleport: (position, yaw) => fps.setPose(position, yaw),
    },
  });
  return { scanner, transition };
}

function frame(now: number): void {
  const dt = clock.tick(now);
  fps.update(dt);
  if (world) {
    const { scanner, transition } = world;
    scanner.setEnabled(game.snapshot.state === "STORE" && !clock.paused);
    scanner.update(dt);
    const target = scanner.target?.chainId;
    hud.setAim(target ? (CHAINS[target]?.label ?? target) : null, scanner.progress);
    transition.update(dt);
  }
  renderer.render(scene, camera);
}

async function start(): Promise<void> {
  try {
    const store = await StoreWorld.load(assets, scene);
    collisions.addFrom(store.root);
    const spawn = store.spawnPose();
    fps.setPose(spawn.position, spawn.yaw);
    world = createWorld(store);
    status.textContent = "";
    intro.setReady();
  } catch (error) {
    const detail = error instanceof AssetError ? `${error.url} : ${error.message}` : String(error);
    status.textContent = `Impossible de charger le magasin. ${detail}`;
    status.dataset.kind = "error";
    intro.setFailed();
    console.error(error);
  }
  renderer.setAnimationLoop(frame);
}

let virtualNow = 0;
if (import.meta.env.DEV) {
  Object.assign(window, {
    __dlr: {
      game,
      session,
      clock,
      fps,
      collisions,
      camera,
      settings,
      get world() {
        return world;
      },
      /** Advances the game by `seconds` of synthetic frames (pages in a background tab get no rAF). */
      step(seconds: number, fps = 60) {
        virtualNow = Math.max(virtualNow, performance.now());
        for (let i = 0; i < Math.round(seconds * fps); i++) frame((virtualNow += 1000 / fps));
      },
    },
  });
}

void start();
