import type { WebGLRenderer } from "three";
import type { PerfMonitor } from "../core/PerfMonitor";

/** Developer readout (toggle with the key left of 1, or ?perf in the URL). Hidden from AT. */
export class PerfOverlay {
  private elapsed = 0;

  constructor(
    private readonly element: HTMLElement,
    private readonly perf: PerfMonitor,
    private readonly renderer: WebGLRenderer,
    private readonly timings: ReadonlyMap<string, number>,
  ) {}

  get visible(): boolean {
    return !this.element.hidden;
  }

  toggle(): void {
    this.element.hidden = !this.element.hidden;
  }

  /** Refreshes about four times a second, after the frame was rendered. */
  update(realDtMs: number): void {
    this.elapsed += realDtMs;
    if (this.element.hidden || this.elapsed < 250) return;
    this.elapsed = 0;
    const { fps, p95Ms, samples } = this.perf.stats;
    const { render, memory } = this.renderer.info;
    const heap = (performance as Performance & { memory?: { usedJSHeapSize: number } }).memory;
    const lines = [
      `${fps.toFixed(0)} fps · p95 ${p95Ms.toFixed(1)} ms (${samples} images)`,
      `draw calls ${render.calls} · triangles ${render.triangles.toLocaleString("fr-FR")}`,
      `géométries ${memory.geometries} · textures ${memory.textures}`,
      heap ? `tas JS ${(heap.usedJSHeapSize / 1048576).toFixed(0)} Mo` : "tas JS indisponible",
      ...[...this.timings].map(([url, ms]) => `${url.split("/").pop()} ${ms.toFixed(0)} ms`),
    ];
    this.element.textContent = lines.join("\n");
  }
}
