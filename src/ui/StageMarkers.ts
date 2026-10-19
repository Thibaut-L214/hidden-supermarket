import { type Camera, Vector3 } from "three";
import type { Caption } from "../features/content/types";
import { captionBadge } from "../features/content/types";

export interface MarkerItem {
  caption: Caption;
  /** World position the marker floats over. */
  position: Vector3;
}

/** Normalised screen position (0–1, origin top-left) of a world point, or null when it is
 * behind the camera or well outside the view. */
export function projectToScreen(
  position: Vector3,
  camera: Camera,
  margin = 0.04,
): { x: number; y: number } | null {
  const p = position.clone().project(camera);
  if (p.z < -1 || p.z > 1) return null;
  const x = (p.x + 1) / 2;
  const y = (1 - p.y) / 2;
  if (x < -margin || x > 1 + margin || y < -margin || y > 1 + margin) return null;
  return { x, y };
}

export interface MarkerBox {
  /** Anchor point, in pixels. */
  x: number;
  y: number;
  /** Label size, in pixels; the label sits centred above the anchor. */
  width: number;
  height: number;
}

/**
 * Vertical lift (px) of each label so none overlaps another: the lowest anchor keeps its natural
 * place, the others rise above whatever is already placed. The anchor stays put; a leader joins it.
 */
export function declutter(boxes: readonly MarkerBox[], gap = 8): number[] {
  const lifts = boxes.map(() => 0);
  const placed: { left: number; right: number; top: number }[] = [];
  const order = boxes.map((_, i) => i).sort((a, b) => boxes[b]!.y - boxes[a]!.y);
  for (const i of order) {
    const { x, y, width, height } = boxes[i]!;
    const left = x - width / 2;
    const right = x + width / 2;
    let lift = 0;
    for (const other of placed) {
      if (left < other.right + gap && right > other.left - gap) {
        const bottom = y - lift;
        if (bottom > other.top - gap) lift = y - (other.top - gap);
      }
    }
    lifts[i] = lift;
    placed.push({ left, right, top: y - lift - height });
  }
  return lifts;
}

/** Information markers over the terrace (docs/GDD.md §06): each carries a caption, so every
 * statement keeps its source and its status. Real text in the DOM, no motion. */
export class StageMarkers {
  private entries: { element: HTMLLIElement; position: Vector3 }[] = [];

  constructor(
    private readonly list: HTMLElement,
    private readonly camera: Camera,
  ) {}

  set(items: readonly MarkerItem[]): void {
    this.list.replaceChildren();
    this.entries = items.map(({ caption, position }) => {
      const element = document.createElement("li");
      element.className = "stage-marker";
      const badge = document.createElement("p");
      badge.className = "stage-marker-badge";
      badge.textContent = captionBadge(caption);
      const title = document.createElement("strong");
      title.textContent = caption.title;
      const text = document.createElement("p");
      text.className = "stage-marker-text";
      text.textContent = caption.short;
      element.append(badge, title, text);
      this.list.append(element);
      return { element, position };
    });
    this.list.hidden = this.entries.length === 0;
    this.update();
  }

  /** Repositions the markers for the current camera; call once per frame. */
  update(): void {
    const width = this.list.clientWidth;
    const height = this.list.clientHeight;
    const shown = this.entries
      .map((entry) => ({ entry, screen: projectToScreen(entry.position, this.camera) }))
      .filter((item): item is typeof item & { screen: { x: number; y: number } } => {
        item.entry.element.hidden = !item.screen;
        return item.screen !== null;
      });
    const boxes = shown.map(({ entry, screen }) => ({
      x: screen.x * width,
      y: screen.y * height,
      width: entry.element.offsetWidth,
      height: entry.element.offsetHeight,
    }));
    const lifts = declutter(boxes);
    shown.forEach(({ entry, screen }, i) => {
      const { element } = entry;
      element.style.left = `${(screen.x * 100).toFixed(2)}%`;
      element.style.top = `${(screen.y * height - lifts[i]!).toFixed(1)}px`;
      element.style.setProperty("--lift", `${lifts[i]!.toFixed(1)}px`);
    });
  }
}
