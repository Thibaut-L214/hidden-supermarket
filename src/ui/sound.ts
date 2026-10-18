// Short synthesised cues; every cue also has a text equivalent on screen (docs/DA.md §07–08).
let context: AudioContext | null = null;

/** Brief, soft confirmation beep (docs/DA.md §05). Silently skipped if audio is unavailable. */
export function beep(frequency = 880, seconds = 0.09, volume = 0.06): void {
  try {
    context ??= new AudioContext();
    const t = context.currentTime;
    const osc = context.createOscillator();
    const gain = context.createGain();
    osc.frequency.value = frequency;
    gain.gain.setValueAtTime(volume, t);
    gain.gain.exponentialRampToValueAtTime(0.0001, t + seconds);
    osc.connect(gain).connect(context.destination);
    osc.start(t);
    osc.stop(t + seconds);
  } catch {
    // No audio output: the on-screen message carries the information.
  }
}
