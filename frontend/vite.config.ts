import { defineConfig } from "vite";
import { tanstackStart } from "@tanstack/react-start/plugin/vite";
import viteReact from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import tsConfigPaths from "vite-tsconfig-paths";
import { nitro } from "nitro/vite";

export default defineConfig(({ command }) => ({
  plugins: [
    tsConfigPaths(),
    tailwindcss(),
    tanstackStart({
      // Use src/server.ts (our SSR error wrapper) as the server entry.
      server: { entry: "server" },
    }),
    // Nitro only runs for production builds; build a Node server.
    ...(command === "build" ? [nitro({ preset: "node-server" })] : []),
    viteReact(),
  ],
}));
