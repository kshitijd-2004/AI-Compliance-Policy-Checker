import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import path from "path";

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
  ],

  resolve: {
    alias: {
      "@": path.resolve(__dirname, "src"),
      "@shared": path.resolve(__dirname, "shared"),
      "@assets": path.resolve(__dirname, "attached_assets"),
    },
  },

  css: {
    postcss: {
      plugins: [],
    },
  },

  root: ".", // frontend/ is the root
  publicDir: "public",

  build: {
    outDir: "dist",   // leave conventional Vite dist/
    emptyOutDir: true,
  },

  server: {
    host: "localhost",
    port: 5173,
    strictPort: true,
  }
});
