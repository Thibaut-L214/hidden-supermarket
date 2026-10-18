import type { AssetContract } from "../../core/assetContract";
import type { ChainId } from "../../core/chain";
import type { Caption, TODO_SOURCE } from "../content/types";

/** What a shelf brings to the shared systems (docs/TECH.md §04). */
export interface ChainConfig {
  id: ChainId;
  /** Shelf name shown on its sign and in the interface. */
  label: string;
  /** Terrace module loaded on demand when the shelf is scanned. */
  terrace: AssetContract;
  /** Farming system the terrace depicts; unknown until editorially chosen. */
  systemType: string | typeof TODO_SOURCE;
  captions: {
    /** Shown when the player first steps onto the terrace. */
    terrace: Caption;
    /** Shown when the roof comes off: what system the interior represents. */
    reveal: Caption;
  };
}
