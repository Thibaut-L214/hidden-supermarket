// Ambient sound (docs/DA.md §07), synthesised so no recording needs licensing:
// - store: discreet ventilation and a soft, unrecognisable pad;
// - scan and opening: the store recedes under low mechanical tones;
// - terrace: wind, and engines located on the trucks actually visible;
// - forecourt: gentler wind, no music.
// No animal sounds, no cries. Master volume follows the settings; 0 is the no-audio mode.
import {
  Audio,
  AudioListener,
  type Object3D,
  type PerspectiveCamera,
  PositionalAudio,
  Vector3,
} from "three";
import type { GameStateId } from "../core/GameState";

export interface AmbienceMix {
  vent: number;
  music: number;
  hum: number;
  wind: number;
}

const CHAIN_STATES: readonly GameStateId[] = [
  "SCANNING",
  "OPENING",
  "TERRACE",
  "REVEAL",
  "CHAIN",
  "RECAP",
  "RETURN",
];
const FORECOURT_STATES: readonly GameStateId[] = ["EXIT", "END_MENU"];

/** Bed gains for a game state and an outdoor share in [0, 1] (pure, tested). */
export function ambienceMix(state: GameStateId, outdoor: number): AmbienceMix {
  const indoor = 1 - outdoor;
  const inChain = CHAIN_STATES.includes(state);
  const forecourt = FORECOURT_STATES.includes(state);
  return {
    vent: 0.05 * indoor,
    // The commercial ambience dips once a shelf is scanned (docs/DA.md §05).
    music: (inChain ? 0.012 : 0.035) * indoor,
    hum: inChain ? 0.05 * (0.4 + 0.6 * outdoor) : 0,
    wind: (forecourt ? 0.05 : 0.11) * outdoor,
  };
}

/** Soft chord loop: frequencies in Hz, changed every few seconds (no melody, no hook). */
const CHORDS = [
  [196.0, 246.94, 293.66, 369.99],
  [220.0, 261.63, 329.63, 392.0],
  [174.61, 220.0, 261.63, 329.63],
  [196.0, 246.94, 293.66, 329.63],
];
const CHORD_SECONDS = 8;

function noiseBuffer(ctx: BaseAudioContext, seconds: number, brown: boolean): AudioBuffer {
  const buffer = ctx.createBuffer(1, Math.ceil(ctx.sampleRate * seconds), ctx.sampleRate);
  const data = buffer.getChannelData(0);
  let last = 0;
  for (let i = 0; i < data.length; i++) {
    const white = Math.random() * 2 - 1;
    last = brown ? (last + 0.02 * white) / 1.02 : white;
    data[i] = brown ? last * 3.5 : white * 0.5;
  }
  return buffer;
}

interface Bed {
  audio: Audio;
  gain: GainNode;
}

export class Soundscape {
  /** Null when the browser has no Web Audio: every method then does nothing. */
  private readonly listener: AudioListener | null = null;
  private beds: Record<keyof AmbienceMix, Bed> | null = null;
  private pad: OscillatorNode[] = [];
  private chordTimer = 0;
  private chord = 0;
  private paused = false;
  private engines: {
    audio: PositionalAudio;
    gain: GainNode;
    oscillators: OscillatorNode[];
    last: Vector3;
  }[] = [];

  constructor(camera: PerspectiveCamera) {
    try {
      this.listener = new AudioListener();
      camera.add(this.listener);
    } catch (error) {
      console.warn("Audio indisponible", error);
    }
  }

  private get ctx(): AudioContext {
    return this.listener!.context;
  }

  /** Node cues connect to, so they follow the master volume; null without Web Audio. */
  get output(): AudioNode | null {
    return this.listener?.getInput() ?? null;
  }

  setVolume(volume: number): void {
    this.listener?.setMasterVolume(volume);
  }

  /** Builds the beds; call from a user gesture (browsers keep audio locked until then). */
  start(): void {
    if (this.beds || !this.listener) return;
    try {
      void this.ctx.resume();
      this.beds = {
        vent: this.noiseBed("bandpass", 320, false),
        music: this.padBed(),
        hum: this.humBed(),
        wind: this.noiseBed("lowpass", 480, true),
      };
    } catch (error) {
      // No Web Audio: the experience stays complete without sound.
      console.warn("Audio indisponible", error);
      this.beds = null;
    }
  }

  /** Suspends everything while paused or hidden; resumes without restarting anything. */
  setPaused(paused: boolean): void {
    if (!this.beds || paused === this.paused) return;
    this.paused = paused;
    void (paused ? this.ctx.suspend() : this.ctx.resume());
  }

  /** Engines follow every TRUCK_* object of a module; null removes them. */
  setVehicles(root: Object3D | null): void {
    for (const engine of this.engines) {
      engine.oscillators.forEach((osc) => osc.stop());
      engine.audio.disconnect();
      engine.audio.removeFromParent();
    }
    this.engines = [];
    if (!root || !this.beds) return;
    root.traverse((object) => {
      if (/^TRUCK_[A-Z_]+$/.test(object.name) && !object.name.endsWith("_BODY")) {
        this.engines.push(this.engine(object));
      }
    });
  }

  update(dt: number, state: GameStateId, outdoor: number): void {
    if (!this.beds || dt <= 0) return;
    const t = this.ctx.currentTime;
    const mix = ambienceMix(state, outdoor);
    for (const key of Object.keys(mix) as (keyof AmbienceMix)[]) {
      this.beds[key].gain.gain.setTargetAtTime(mix[key], t, 0.6);
    }

    this.chordTimer += dt;
    if (this.chordTimer >= CHORD_SECONDS) {
      this.chordTimer = 0;
      this.chord = (this.chord + 1) % CHORDS.length;
      this.pad.forEach((osc, i) => osc.frequency.setTargetAtTime(CHORDS[this.chord]![i]!, t, 1.5));
    }

    // Engines are audible only while their truck moves.
    for (const engine of this.engines) {
      const parent = engine.audio.parent!;
      const now = parent.getWorldPosition(new Vector3());
      const speed = now.distanceTo(engine.last) / dt;
      engine.last.copy(now);
      engine.gain.gain.setTargetAtTime(speed > 0.5 ? 0.5 : 0, t, 0.4);
    }
  }

  private bed(source: AudioNode, filter: BiquadFilterNode | null): Bed {
    const audio = new Audio(this.listener!);
    const gain = this.ctx.createGain();
    gain.gain.value = 0;
    if (filter) source.connect(filter).connect(gain);
    else source.connect(gain);
    // three's Audio only needs a node to connect from; the bed's sources run on their own.
    audio.setNodeSource(gain as unknown as AudioBufferSourceNode);
    return { audio, gain };
  }

  private noiseBed(type: BiquadFilterType, frequency: number, brown: boolean): Bed {
    const source = this.ctx.createBufferSource();
    source.buffer = noiseBuffer(this.ctx, 4, brown);
    source.loop = true;
    const filter = this.ctx.createBiquadFilter();
    filter.type = type;
    filter.frequency.value = frequency;
    filter.Q.value = 0.7;
    source.start();
    if (brown) {
      // Slow gusts: an LFO on the cutoff.
      const lfo = this.ctx.createOscillator();
      const depth = this.ctx.createGain();
      lfo.frequency.value = 0.08;
      depth.gain.value = 220;
      lfo.connect(depth).connect(filter.frequency);
      lfo.start();
    }
    return this.bed(source, filter);
  }

  private padBed(): Bed {
    const mixer = this.ctx.createGain();
    mixer.gain.value = 0.25;
    this.pad = CHORDS[0]!.map((frequency) => {
      const osc = this.ctx.createOscillator();
      osc.type = "triangle";
      osc.frequency.value = frequency;
      osc.connect(mixer);
      osc.start();
      return osc;
    });
    const filter = this.ctx.createBiquadFilter();
    filter.type = "lowpass";
    filter.frequency.value = 1100;
    return this.bed(mixer, filter);
  }

  private humBed(): Bed {
    const mixer = this.ctx.createGain();
    for (const [frequency, level] of [
      [55, 0.6],
      [82.4, 0.25],
    ] as const) {
      const osc = this.ctx.createOscillator();
      const g = this.ctx.createGain();
      osc.frequency.value = frequency;
      g.gain.value = level;
      osc.connect(g).connect(mixer);
      osc.start();
    }
    const filter = this.ctx.createBiquadFilter();
    filter.type = "lowpass";
    filter.frequency.value = 180;
    return this.bed(mixer, filter);
  }

  private engine(vehicle: Object3D) {
    const audio = new PositionalAudio(this.listener!);
    audio.setRefDistance(12);
    audio.setRolloffFactor(1.2);
    const mixer = this.ctx.createGain();
    const oscillators = [42, 84].map((frequency) => {
      const osc = this.ctx.createOscillator();
      osc.type = "sawtooth";
      osc.frequency.value = frequency;
      osc.connect(mixer);
      osc.start();
      return osc;
    });
    const filter = this.ctx.createBiquadFilter();
    filter.type = "lowpass";
    filter.frequency.value = 260;
    const gain = this.ctx.createGain();
    gain.gain.value = 0;
    mixer.connect(filter).connect(gain);
    audio.setNodeSource(gain as unknown as AudioBufferSourceNode);
    vehicle.add(audio);
    return { audio, gain, oscillators, last: vehicle.getWorldPosition(new Vector3()) };
  }
}
