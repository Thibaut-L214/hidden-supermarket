import {
  Color,
  EquirectangularReflectionMapping,
  FogExp2,
  PMREMGenerator,
  PerspectiveCamera,
  Scene,
  type Texture,
} from "three";
import { RoomEnvironment } from "three/addons/environments/RoomEnvironment.js";
import { HDRLoader } from "three/addons/loaders/HDRLoader.js";
import { AssetError, AssetManager } from "../core/AssetManager";
import { EventBus } from "../core/EventBus";
import { GameClock } from "../core/GameClock";
import { GameState, canWalk, type GameEvents } from "../core/GameState";
import { PerfMonitor } from "../core/PerfMonitor";
import { CHAINS } from "../data/chains";
import { EXIT_LINKS } from "../data/exitLinks";
import { TerraceStage } from "../features/chains/TerraceStage";
import { ExitScene } from "../features/exit/ExitScene";
import { TerraceTransition } from "../features/portal/TerraceTransition";
import { findScanTargets } from "../features/scanner/ScanTarget";
import { Scanner } from "../features/scanner/Scanner";
import { ScannerView, scannerRaised } from "../features/scanner/ScannerView";
import { EndMenu } from "../ui/EndMenu";
import { HUD } from "../ui/HUD";
import { IntroScreen } from "../ui/IntroScreen";
import { PauseMenu } from "../ui/PauseMenu";
import { PerfOverlay } from "../ui/PerfOverlay";
import { RecapPanel } from "../ui/RecapPanel";
import { SourcePanel } from "../ui/SourcePanel";
import { Subtitles } from "../ui/Subtitles";
import { CUE_SUBTITLES, type Cue, playCue } from "../ui/sound";
import { Atmosphere } from "../world/Atmosphere";
import { SkyDome, TERRACE_SKY } from "../world/SkyDome";
import { Soundscape } from "../world/Soundscape";
import { CollisionWorld } from "../world/CollisionWorld";
import { FPSController } from "../world/FPSController";
import { EYE_HEIGHT, StoreWorld } from "../world/StoreWorld";
import { createErrorLog, recoverFromError } from "./errors";
import { PostProcessing } from "./postprocessing";
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

// Rendering
const renderer = createRenderer(canvas);
const scene = new Scene();
// Hazy blue-grey horizon (docs/DA.md §03, terrace): the fog takes the sky's horizon colour, so
// distant hills fade into the sky dome. Exponential, so the store's depth is barely touched.
const HAZE = new Color(TERRACE_SKY.horizon);
scene.fog = new FogExp2(HAZE, 0.0042);
// Image-based light: a generic room until the baked store panorama is loaded (see `environments`).
const pmrem = new PMREMGenerator(renderer);
const fallbackEnvironment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
scene.environment = fallbackEnvironment;
scene.environmentIntensity = 0.5;
const camera = new PerspectiveCamera(70, 1, 0.05, 500);
// Two passes per frame (scene, then the hand-held scanner over it): clear and count manually.
renderer.autoClear = false;
renderer.info.autoReset = false;
/** First-person scanner, once its GLB is loaded (the game works without it). */
let scannerView: ScannerView | null = null;
/** GTAO, bloom and SMAA; absent in reduced quality. */
let postFx: PostProcessing | null = null;

function resize(): void {
  renderer.setSize(canvas.clientWidth, canvas.clientHeight, false);
  postFx?.setSize(canvas.clientWidth, canvas.clientHeight);
  camera.aspect = canvas.clientWidth / canvas.clientHeight;
  camera.updateProjectionMatrix();
  scannerView?.setAspect(camera.aspect);
}
window.addEventListener("resize", resize);

// Game systems
const settings = defaultSettings(matchMedia("(prefers-reduced-motion: reduce)").matches);
const bus = new EventBus<GameEvents>();
const game = new GameState(bus);
const session = new Session();
trackExploration(bus, session);
const clock = new GameClock();
const assets = new AssetManager(renderer);
const collisions = new CollisionWorld();
const fps = new FPSController(camera, canvas, collisions, settings, EYE_HEIGHT);
const hud = new HUD(element("#hud-prompt"), status, element("#caption"));
const atmosphere = new Atmosphere(scene, renderer);
const sky = new SkyDome(atmosphere.sunDirection);
scene.add(sky);
postFx = new PostProcessing(renderer, scene, camera, [sky]);
const subtitles = new Subtitles(element("#subtitles"));
const soundscape = new Soundscape(camera);
const perf = new PerfMonitor();
const perfOverlay = new PerfOverlay(element("#perf"), perf, renderer, assets.timings);
if (new URLSearchParams(location.search).has("perf")) perfOverlay.toggle();

function applySettings(): void {
  renderer.setPixelRatio(settings.lowQuality ? 1 : Math.min(window.devicePixelRatio, 2));
  atmosphere.setShadows(!settings.lowQuality);
  if (postFx) postFx.enabled = !settings.lowQuality;
  soundscape.setVolume(settings.volume);
  resize();
}
applySettings();

/**
 * Image-based light per zone: the terrace's is prefiltered from the sky dome itself, the store's
 * from a panorama baked in Blender (blender/scripts/bake_env.py). A missing panorama keeps the
 * generic room.
 */
const environments: Promise<Texture> = (async () => {
  const skyScene = new Scene();
  skyScene.add(new SkyDome(atmosphere.sunDirection));
  const outdoor = pmrem.fromScene(skyScene, 0.02).texture;
  let store = fallbackEnvironment;
  try {
    const panorama = await new HDRLoader().loadAsync("/assets/shared/env_store.hdr");
    panorama.mapping = EquirectangularReflectionMapping;
    store = pmrem.fromEquirectangular(panorama).texture;
    panorama.dispose();
  } catch (error) {
    console.warn("Panorama du magasin indisponible, éclairage générique conservé.", error);
  }
  atmosphere.setEnvironments(store, outdoor);
  return store;
})();

/** Plays a sound cue and, when subtitles are on, describes it on screen. */
function cue(kind: Cue): void {
  const output = soundscape.output;
  if (output) playCue(kind, output);
  if (settings.subtitles) subtitles.show(CUE_SUBTITLES[kind]);
}

/** Systems that need the loaded store. */
let world: {
  store: StoreWorld;
  scanner: Scanner;
  transition: TerraceTransition;
  stage: TerraceStage;
  exit: ExitScene;
} | null = null;

// Dialogs. Pause is a flag orthogonal to the game state (docs/DECISIONS.md); every dialog
// releases the pointer and freezes walking, and only one is open at a time.
const pauseMenu = new PauseMenu(
  element("#pause"),
  settings,
  resume,
  () => {
    resume();
    world?.transition.returnToStore();
  },
  applySettings,
);
const intro = new IntroScreen(element("#intro"), settings, () => {
  soundscape.start();
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
const sourcePanel = new SourcePanel(element("#source-panel"), () => {
  sourcePanel.hide();
  resume();
});
const endMenu = new EndMenu(element("#end-menu"), element("#end-screen"), EXIT_LINKS, {
  onBack: () => {
    endMenu.hide();
    game.send({ type: "RESUME_STORE" });
    if (world) {
      const spawn = world.store.spawnPose();
      fps.setPose(spawn.position, spawn.yaw);
    }
    resume();
  },
  onFinish: () => endMenu.finish(),
});
clock.setPaused("menu", true);

function dialogOpen(): boolean {
  return pauseMenu.visible || recap.visible || sourcePanel.visible || endMenu.visible;
}

/** Releases the pointer and hides the HUD under a dialog; `freeze` also stops game time. */
function openDialog(freeze: boolean): void {
  if (freeze) clock.setPaused("menu", true);
  fps.deactivate();
  hud.setVisible(false);
}

function pause(): void {
  if (dialogOpen() || !canWalk(game.snapshot.state)) return;
  openDialog(true);
  pauseMenu.show(world?.transition.canReturn ?? false);
}

function resume(): void {
  pauseMenu.hide();
  hud.setVisible(true);
  clock.setPaused("menu", false);
  void fps.activate();
}

function showDetail(): void {
  const caption = hud.currentCaption;
  if (!caption || dialogOpen() || !canWalk(game.snapshot.state)) return;
  // Reading never races the animation (docs/GDD.md §08): game time stops meanwhile.
  openDialog(true);
  sourcePanel.show(caption);
}

fps.onLockLost = pause;
document.addEventListener("keydown", (event) => {
  if (event.repeat) return;
  if (event.code === "Backquote") perfOverlay.toggle();
  if (event.code === "KeyI" && !sourcePanel.visible) showDetail();
  if (event.code === "KeyP" && !recap.visible && !sourcePanel.visible && !endMenu.visible) {
    if (pauseMenu.visible) resume();
    else pause();
  }
});
document.addEventListener("visibilitychange", () => clock.setPaused("hidden", document.hidden));

bus.on("stateChanged", ({ to, snapshot }) => {
  // End of a chain: mark the shelf and open the recap.
  const config = snapshot.activeChain ? CHAINS[snapshot.activeChain] : undefined;
  if (to === "RECAP" && config) {
    world?.store.markExplored(config.id);
    openDialog(false);
    recap.show(config);
  }
  if (to === "END_MENU") {
    openDialog(false);
    endMenu.show(session.exploredChains.map((id) => CHAINS[id]?.label ?? id));
  }
});

function createWorld(store: StoreWorld) {
  const player = {
    radius: collisions.radius,
    position: () => ({ x: camera.position.x, z: camera.position.z }),
    teleport: (position: { x: number; z: number }, yaw: number) => fps.setPose(position, yaw),
  };
  const scanner = new Scanner(
    camera,
    findScanTargets(store.root),
    () => collisions.objects,
    canvas,
  );
  scanner.onConfirm = (chainId) => {
    cue("scan");
    scannerView?.confirm();
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
    player,
  });
  transition.onDoorsMove = () => cue("doors");
  const stage = new TerraceStage({
    game,
    bus,
    player,
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
      postFx?.excludeGlass(root);
      stage.attach(config, root);
    } else stage.detach();
    soundscape.setVehicles(root);
  };
  const exit = new ExitScene({
    game,
    storeRoot: store.root,
    player,
    onDoorsMoved: () => collisions.refresh(),
  });
  return { store, scanner, transition, stage, exit };
}

// Frame loop, guarded: an unexpected error unwinds to a safe state instead of freezing.
const logError = createErrorLog();

function onRuntimeError(error: unknown): void {
  logError(error);
  recoverFromError(game);
}
window.addEventListener("error", (event) => onRuntimeError(event.error ?? event.message));
window.addEventListener("unhandledrejection", (event) => onRuntimeError(event.reason));

canvas.addEventListener("webglcontextlost", (event) => {
  // Lets three.js restore the context if the browser allows it.
  event.preventDefault();
  pause();
  status.textContent =
    "Le rendu 3D a été interrompu par le navigateur. Rechargez la page si l'image ne revient pas.";
  status.dataset.kind = "error";
});
canvas.addEventListener("webglcontextrestored", () => (status.textContent = ""));

let lastFrame = 0;
function frame(now: number): void {
  perf.frame(now);
  try {
    step(clock.tick(now), Math.min(Math.max((now - lastFrame) / 1000, 0), 0.1));
  } catch (error) {
    onRuntimeError(error);
  }
  perfOverlay.update(now - lastFrame);
  lastFrame = now;
}

function draw(): void {
  renderer.info.reset();
  sky.follow(camera.position);
  if (postFx?.enabled) {
    postFx.setOutdoor(atmosphere.outdoor);
    postFx.render(0);
  } else {
    renderer.clear();
    renderer.render(scene, camera);
  }
  scannerView?.render(renderer);
}

function step(dt: number, realDt: number): void {
  fps.update(dt);
  if (world) {
    const { scanner, transition, stage, exit } = world;
    scanner.setEnabled(game.snapshot.state === "STORE" && !clock.paused);
    scanner.update(dt);
    const target = scanner.target?.chainId;
    const label = target ? (CHAINS[target]?.label ?? target) : null;
    hud.setAim(label);
    const { state } = game.snapshot;
    scannerView?.update(realDt, {
      visible: !dialogOpen() && state !== "INTRO" && state !== "END_MENU",
      raised: scannerRaised(state) && !clock.paused,
      label,
      progress: scanner.progress,
    });
    // Aiming at a shelf is a strong hint: fetch its module now so the doors open sooner.
    const terrace = target ? CHAINS[target]?.terrace : undefined;
    if (terrace) assets.load(terrace).catch(() => {});
    transition.update(dt);
    stage.update(dt);
    exit.update(dt);
    atmosphere.update(dt, Math.max(transition.outdoorTarget, exit.outdoorTarget));
  }
  soundscape.setPaused(clock.paused);
  soundscape.update(dt, game.snapshot.state, atmosphere.outdoor);
  draw();
}

async function loadStore(): Promise<void> {
  status.textContent = "Chargement du magasin…";
  status.dataset.kind = "info";
  try {
    const store = await StoreWorld.load(assets, scene);
    atmosphere.shadeStore(store.root);
    postFx?.excludeGlass(store.root);
    collisions.addFrom(store.root);
    const spawn = store.spawnPose();
    fps.setPose(spawn.position, spawn.yaw);
    world = createWorld(store);
    // The hand-held scanner is a nicety: a failed load leaves the shelf outline and the prompt.
    scannerView = await ScannerView.load(
      assets,
      await environments,
      () => settings.reducedMotion,
    ).catch((error: unknown) => {
      console.error(error);
      return null;
    });
    scannerView?.setAspect(camera.aspect);
    status.textContent = "";
    intro.setReady();
  } catch (error) {
    const detail = error instanceof AssetError ? `${error.url} : ${error.message}` : String(error);
    status.textContent = `Impossible de charger le magasin. ${detail}`;
    status.dataset.kind = "error";
    intro.setFailed(() => void loadStore());
    console.error(error);
  }
}

async function start(): Promise<void> {
  await loadStore();
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
      renderer,
      assets,
      soundscape,
      get world() {
        return world;
      },
      get scannerView() {
        return scannerView;
      },
      get postFx() {
        return postFx;
      },
      /** Freezes the current frame in an overlay image (background tabs do not composite the canvas); false removes it. */
      async capture(show = true) {
        document.querySelector("#dev-capture")?.remove();
        if (!show) return;
        draw();
        const img = Object.assign(document.createElement("img"), {
          id: "dev-capture",
          src: canvas.toDataURL("image/jpeg", 0.85),
        });
        img.style.cssText =
          "position:fixed;inset:0;width:100%;height:100%;z-index:9;pointer-events:none";
        document.body.append(img);
        await img.decode();
      },
      /** Advances the game by `seconds` of synthetic frames (pages in a background tab get no rAF). */
      step(seconds: number, rate = 60) {
        virtualNow = Math.max(virtualNow, performance.now());
        for (let i = 0; i < Math.round(seconds * rate); i++) frame((virtualNow += 1000 / rate));
      },
    },
  });
}

void start();
