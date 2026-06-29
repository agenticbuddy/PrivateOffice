import { fileURLToPath, URL } from "node:url";
import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

// SPA build. In dev the dist/ is bind-mounted into the app container and served
// by FastAPI; the API is reached at /api on the same origin (no proxy needed).
export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) },
  },
  build: { outDir: "dist", emptyOutDir: true },
});
