import type { ChainId } from "../../core/chain";
import type { ChainConfig } from "../../features/chains/ChainModule";
import { eggs } from "./eggs";
import { beef } from "./beef";

/** Shelves available in this build; other chains keep their place in ChainId until they exist. */
export const CHAINS: Partial<Record<ChainId, ChainConfig>> = { eggs, beef };
