import type { AssetContract } from "../../core/assetContract";
import type { ChainId } from "../../core/chain";
import type { Caption, SourceRef, TODO_SOURCE } from "../content/types";

/**
 * One step of a chain's schematic timeline (docs/TECH.md §04, docs/DECISIONS.md).
 * Node names refer to the chain's terrace GLB.
 * - collect / load / process / deliver: units move from `from` to `to` (groups whose children
 *   are shown or hidden one by one); collect has only `to`, deliver only `from`.
 * - carry (on a load step): the units visibly travel from their slot in `from` to the matching
 *   slot in `to` one after the other, instead of switching places.
 * - drive: `vehicle` follows the PATH_<pathId>_<NN> empties.
 */
export interface TimelineStep {
  id: string;
  event: "collect" | "load" | "walk" | "drive" | "process" | "deliver";
  durationSec: number;
  captionId: string;
  from?: string;
  to?: string;
  /** Units travel between their slots (load steps). */
  carry?: boolean;
  vehicle?: string;
  /** Vehicle route, or intermediate ground/ramp waypoints for a walk between animal groups. */
  pathId?: string;
}

/** An information marker floating over a node of the terrace once the roof is off. */
export interface StageMarker {
  /** Node name of the anchor in the terrace GLB. */
  anchor: string;
  /** Caption it shows: sourced facts stay in captions, never in the marker itself. */
  captionId: string;
}

/** What a shelf brings to the shared systems (docs/TECH.md §04). */
export interface ChainConfig {
  id: ChainId;
  /** Shelf name shown on its sign and in the interface. */
  label: string;
  /** Terrace module loaded on demand when the shelf is scanned. */
  terrace: AssetContract;
  /** Farming system the terrace depicts; unknown until editorially chosen. */
  systemType: string | typeof TODO_SOURCE;
  captions: readonly Caption[];
  /** Caption shown when the player first steps onto the terrace. */
  terraceCaption: string;
  /** Caption shown when the roof comes off: what system the interior represents. */
  revealCaption: string;
  timeline: readonly TimelineStep[];
  /** Markers over the site, shown from the reveal on. */
  markers?: readonly StageMarker[];
  /** At most three caption ids for the recap (docs/GDD.md §06.5). */
  recap: readonly string[];
  sources: readonly SourceRef[];
}

export function captionById(config: ChainConfig, id: string): Caption {
  const caption = config.captions.find((c) => c.id === id);
  if (!caption) throw new Error(`cartel inconnu : ${id}`);
  return caption;
}
