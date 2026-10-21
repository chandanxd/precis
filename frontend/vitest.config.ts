import { defineConfig } from "vitest/config";
import tsconfigPaths from "vite-tsconfig-paths";

// Tests deliberately don't reuse vite.config.ts: it wires in TanStack Start and
// nitro, which only make sense for a real build. Path aliases come from
// tsconfig.json so they are defined in one place.
export default defineConfig({
  plugins: [tsconfigPaths()],
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
    include: ["src/**/*.{test,spec}.{ts,tsx}"],
  },
});
