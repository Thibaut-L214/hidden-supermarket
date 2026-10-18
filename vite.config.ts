import { defineConfig } from "vitest/config";

export default defineConfig({
  build: {
    target: "es2022",
    sourcemap: true,
    // three.js alone is ~600 kB minified; chains will be code-split when they load on demand.
    chunkSizeWarningLimit: 800,
  },
  test: {
    include: ["tests/**/*.test.ts"],
    environment: "node",
  },
});
