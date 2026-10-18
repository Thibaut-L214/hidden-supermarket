// Naming contract between Blender exports and the runtime (docs/TECH.md §03, docs/DECISIONS.md).
// Used at runtime to validate a loaded GLB and by tests/assets.test.ts on the exported files.

/** Helper volumes: exported in the GLB, never rendered. */
export const HIDDEN_PREFIXES = ["COL_", "SCAN_", "TRIGGER_"] as const;

export interface AssetContract {
  /** URL served by Vite (files live under public/). */
  url: string;
  /** Node names that must exist. */
  required: readonly string[];
  /** child name → expected direct parent name. */
  parents: Readonly<Record<string, string>>;
  /** Name prefixes that must match at least `min` nodes. */
  prefixes: readonly { prefix: string; min: number }[];
}

export const STORE_CONTRACT: AssetContract = {
  url: "/assets/store/store.glb",
  required: [
    "STORE_ROOT",
    "SPAWN_PLAYER",
    "TRIGGER_EXIT",
    "SHELF_EGGS_ROOT",
    "HINGE_EGGS_L",
    "HINGE_EGGS_R",
    "DOOR_EGGS_L",
    "DOOR_EGGS_R",
    "SCAN_EGGS",
    "TRIGGER_EGGS_ENTRY",
    "SIGN_EGGS",
  ],
  parents: {
    HINGE_EGGS_L: "SHELF_EGGS_ROOT",
    HINGE_EGGS_R: "SHELF_EGGS_ROOT",
    DOOR_EGGS_L: "HINGE_EGGS_L",
    DOOR_EGGS_R: "HINGE_EGGS_R",
    SCAN_EGGS: "SHELF_EGGS_ROOT",
    TRIGGER_EGGS_ENTRY: "SHELF_EGGS_ROOT",
  },
  prefixes: [{ prefix: "COL_", min: 1 }],
};

export interface ContractNode {
  name: string;
  parentName: string | null;
}

/** Returns human-readable violations; an empty list means the asset honours the contract. */
export function checkContract(nodes: readonly ContractNode[], contract: AssetContract): string[] {
  const byName = new Map<string, ContractNode>();
  const errors: string[] = [];
  for (const node of nodes) {
    if (byName.has(node.name)) errors.push(`nom dupliqué : ${node.name}`);
    byName.set(node.name, node);
  }
  for (const name of contract.required) {
    if (!byName.has(name)) errors.push(`nœud manquant : ${name}`);
  }
  for (const [child, parent] of Object.entries(contract.parents)) {
    const node = byName.get(child);
    if (node && node.parentName !== parent) {
      errors.push(
        `${child} doit être enfant de ${parent} (trouvé : ${node.parentName ?? "racine"})`,
      );
    }
  }
  for (const { prefix, min } of contract.prefixes) {
    const count = nodes.filter((n) => n.name.startsWith(prefix)).length;
    if (count < min) errors.push(`au moins ${min} nœud(s) ${prefix}* attendus, ${count} trouvé(s)`);
  }
  return errors;
}

export function isHiddenHelper(name: string): boolean {
  return HIDDEN_PREFIXES.some((prefix) => name.startsWith(prefix));
}
