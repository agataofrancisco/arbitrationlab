import { defineConfig } from "vite";

// Em desenvolvimento, o painel fala com a API local sem CORS: os caminhos da API sao reencaminhados.
const API_TARGET = process.env.ARBITRATIONLAB_API ?? "http://127.0.0.1:8000";
const API_PATHS = ["/arbitrations", "/schemas", "/metrics", "/reviews", "/health"];

export default defineConfig({
  server: {
    proxy: Object.fromEntries(API_PATHS.map((path) => [path, { target: API_TARGET }])),
  },
});
