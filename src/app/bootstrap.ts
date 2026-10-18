import { Color, Fog, PMREMGenerator, PerspectiveCamera, Scene } from "three";
import { RoomEnvironment } from "three/addons/environments/RoomEnvironment.js";
import { AssetError, AssetManager } from "../core/AssetManager";
import { EventBus } from "../core/EventBus";
import { GameClock } from "../core/GameClock";
import { GameState, canWalk, type GameEvents } from "../core/GameState";
import { CHAINS } from "../data/chains";
import { TerraceStage } from "../features/chains/TerraceStage";
import { TerraceTransition } from "../features/portal/TerraceTransition";
import { findScanTargets } from "../features/scanner/ScanTarget";
import { Scanner } from "../features/scanner/Scanner";
import { HUD } from "../ui/HUD";
import { IntroScreen } from "../ui/IntroScreen";
import { PauseMenu } from "../ui/PauseMenu";
import { RecapPanel } from "../ui/RecapPanel";
import { beep } from "../ui/sound";
import { Atmosphere } from "../world/Atmosphere";
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
const hud = new HUD(reticle, element("#hud-prompt"), status, element("#caption"));
const atmosphere = new Atmosphere(scene, renderer);

/** Systems that need the loaded store. */
let world: {
  store: StoreWorld;
  scanner: Scanner;
  transition: TerraceTransition;
  stage: TerraceStage;
} | null = null;

// Pause is a flag orthogonal to the game state (docs/DECISIONS.md).
const pauseMenu = new PauseMenu(element("#pause"), settings, resume, () => {
  resume();
  world?.transition.returnToStore();
});
const intro = new IntroScreen(element("#intro"), settings, () => {
  game.send({ type: "START" });
  resume();
});
const recap = new RecapPanel(element("#recap"), {
  onReplay: () => {
    recap.hide();
    game.send({ type: "REPLAY" });
    resume();
  },
  onReturn: () => {
    recap.hide();
    resume();
    world?.transition.returnToStore();
  },
  onStay: () => {
    recap.hide();
    resume();
  },
});
clock.setPaused("menu", true);

// End of a chain: mark the shelf and open the recap with the pointer released.
bus.on("stateChanged", ({ to, snapshot }) => {
  const config = snapshot.activeChain ? CHAINS[snapshot.activeChain] : undefined;
  if (to !== "RECAP" || !config) return;
  world?.store.markExplored(config.id);
  fps.deactivate();
  hud.setVisible(false);
  recap.show(config);
});

function pause(): void {
  if (pauseMenu.visible || recap.visible || !canWalk(game.snapshot.state)) return;
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
  if (event.code !== "KeyP" || event.repeat || recap.visible) return;
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
    hud: { setHint: (text) => hud.setHint("portal", text), alert: (text) => hud.alert(text) },
    player: {
      radius: collisions.radius,
      position: () => ({ x: camera.position.x, z: camera.position.z }),
      teleport: (position, yaw) => fps.setPose(position, yaw),
    },
  });
  const stage = new TerraceStage({
    game,
    bus,
    player: { position: () => ({ x: camera.position.x, z: camera.position.z }) },
    hud: {
      setHint: (text) => hud.setHint("stage", text),
      showCaption: (caption) => hud.showCaption(caption),
    },
    reducedMotion: () => settings.reducedMotion,
    glance: (target) => fps.glanceAt(target),
  });
  transition.onModuleChange = (chain, root) => {
    const config = CHAINS[chain];
    if (root && config) {
      atmosphere.shade(root);
      stage.attach(config, root);
    } else stage.detach();
  };
  return { store, scanner, transition, stage };
}

function frame(now: number): void {
  const dt = clock.tick(now);
  fps.update(dt);
  if (world) {
    const { scanner, transition, stage } = world;
    scanner.setEnabled(game.snapshot.state === "STORE" && !clock.paused);
    scanner.update(dt);
    const target = scanner.target?.chainId;
    hud.setAim(target ? (CHAINS[target]?.label ?? target) : null, scanner.progress);
    transition.update(dt);
    stage.update(dt);
    atmosphere.update(dt, transition.outdoorTarget);
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
      /** Freezes the current frame in an overlay image (background tabs do not composite the canvas); false removes it. */
      async capture(show = true) {
        document.querySelector("#dev-capture")?.remove();
        if (!show) return;
        renderer.render(scene, camera);
        const img = Object.assign(document.createElement("img"), {
          id: "dev-capture",
          src: canvas.toDataURL("image/jpeg", 0.85),
        });
        img.style.cssText =
          "position:fixed;inset:0;width:100%;height:100%;z-index:9;pointer-events:none";
        document.body.append(img);
        await img.decode();
      },
      step(seconds: number, fps = 60) {
        virtualNow = Math.max(virtualNow, performance.now());
        for (let i = 0; i < Math.round(seconds * fps); i++) frame((virtualNow += 1000 / fps));
      },
    },
  });
}

void start();
