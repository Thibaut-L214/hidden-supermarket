import { NodeIO, type Document } from "@gltf-transform/core";
import { resolve } from "node:path";
import { beforeAll, describe, expect, it } from "vitest";
import {
  STORE_CONTRACT,
  TERRACE_EGGS_CONTRACT,
  checkContract,
  type AssetContract,
  type ContractNode,
} from "../src/core/assetContract";

function contractNodes(doc: Document): ContractNode[] {
  return doc
    .getRoot()
    .listNodes()
    .map((node) => ({ name: node.getName(), parentName: node.getParentNode()?.getName() ?? null }));
}

describe("checkContract", () => {
  const contract: AssetContract = {
    url: "",
    required: ["ROOT", "DOOR"],
    parents: { DOOR: "HINGE" },
    prefixes: [{ prefix: "COL_", min: 1 }],
  };

  it("accepts a conforming hierarchy", () => {
    const nodes = [
      { name: "ROOT", parentName: null },
      { name: "HINGE", parentName: "ROOT" },
      { name: "DOOR", parentName: "HINGE" },
      { name: "COL_DOOR", parentName: "DOOR" },
    ];
    expect(checkContract(nodes, contract)).toEqual([]);
  });

  it("reports missing nodes, wrong parents, duplicates and missing prefixes", () => {
    const nodes = [
      { name: "DOOR", parentName: "ROOT" },
      { name: "DOOR", parentName: "ROOT" },
    ];
    expect(checkContract(nodes, contract)).toEqual([
      "nom dupliqué : DOOR",
      "nœud manquant : ROOT",
      "DOOR doit être enfant de HINGE (trouvé : ROOT)",
      "au moins 1 nœud(s) COL_* attendus, 0 trouvé(s)",
    ]);
  });
});

describe.each([STORE_CONTRACT, TERRACE_EGGS_CONTRACT])("$url", (contract) => {
  let doc: Document;

  beforeAll(async () => {
    doc = await new NodeIO().read(resolve("public", `.${contract.url}`));
  });

  it("honours the naming contract", () => {
    expect(checkContract(contractNodes(doc), contract)).toEqual([]);
  });

  it("keeps every node at unit scale (transforms applied before export)", () => {
    const scaled = doc
      .getRoot()
      .listNodes()
      .filter((node) => node.getScale().some((s) => Math.abs(s - 1) > 1e-6))
      .map((node) => node.getName());
    expect(scaled).toEqual([]);
  });
});
