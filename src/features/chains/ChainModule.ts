import type { AssetContract } from "../../core/assetContract";
import type { ChainId } from "../../core/chain";

/** What a shelf brings to the shared systems (docs/TECH.md §04). */
export interface ChainConfig {
  id: ChainId;
  /** Shelf name shown on its sign and in the interface. */
  label: string;
  /** Terrace module loaded on demand when the shelf is scanned. */
  terrace: AssetContract;
}
