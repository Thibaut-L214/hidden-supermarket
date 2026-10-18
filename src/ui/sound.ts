// Short synthesised cues (docs/DA.md §05, §07). Each cue has a subtitle describing it, shown
// when subtitles are on (docs/DA.md §08), so no information depends on hearing.
let context: AudioContext | null = null;

export type Cue = "scan" | "doors";

export const CUE_SUBTITLES: Record<Cue, string> = {
  scan: "[Bip de confirmation]",
  doors: "[Mécanisme feutré des portes]",
};

function audio(): AudioContext | null {
  try {
    context ??= new AudioContext();
    return context;
  } catch {
    return null;
  }
}

/** Plays a cue at the given master volume (0 = silent). Skipped if audio is unavailable. */
export function playCue(cue: Cue, volume: number): void {
  const ctx = volume > 0 ? audio() : null;
  if (!ctx) return;
  const t = ctx.currentTime;
  const gain = ctx.createGain();
  gain.connect(ctx.destination);

  if (cue === "scan") {
    const osc = ctx.createOscillator();
    osc.frequency.value = 880;
    gain.gain.setValueAtTime(0.08 * volume, t);
    gain.gain.exponentialRampToValueAtTime(0.0001, t + 0.09);
    osc.connect(gain);
    osc.start(t);
    osc.stop(t + 0.09);
    return;
  }

  // Doors: low, muffled noise swelling and fading over the opening time.
  const seconds = 2.5;
  const buffer = ctx.createBuffer(1, Math.ceil(ctx.sampleRate * seconds), ctx.sampleRate);
  const data = buffer.getChannelData(0);
  let last = 0;
  for (let i = 0; i < data.length; i++) {
    last = (last + 0.02 * (Math.random() * 2 - 1)) / 1.02;
    data[i] = last * 3.5;
  }
  const source = ctx.createBufferSource();
  source.buffer = buffer;
  const lowpass = ctx.createBiquadFilter();
  lowpass.type = "lowpass";
  lowpass.frequency.value = 260;
  gain.gain.setValueAtTime(0.0001, t);
  gain.gain.exponentialRampToValueAtTime(0.25 * volume, t + 0.4);
  gain.gain.exponentialRampToValueAtTime(0.0001, t + seconds);
  source.connect(lowpass).connect(gain);
  source.start(t);
}
