import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          chart: ["chart.js", "react-chartjs-2"],
          three: ["three", "@react-three/fiber", "@react-three/drei"],
          vendor: ["@msgpack/msgpack", "lucide-react", "react", "react-dom", "zustand"]
        }
      }
    }
  },
  plugins: [react()],
  server: {
    host: "0.0.0.0",
    port: Number.parseInt(process.env.VITE_PORT ?? "5220", 10),
    strictPort: true
  }
});
