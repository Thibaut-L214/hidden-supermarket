export const CHAIN_IDS = ["eggs", "chicken", "pork", "fish"] as const;

export type ChainId = (typeof CHAIN_IDS)[number];
