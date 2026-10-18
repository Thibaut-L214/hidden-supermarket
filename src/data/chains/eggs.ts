import { TERRACE_EGGS_CONTRACT } from "../../core/assetContract";
import type { ChainConfig } from "../../features/chains/ChainModule";

export const eggs: ChainConfig = {
  id: "eggs",
  label: "Œufs",
  terrace: TERRACE_EGGS_CONTRACT,
};
