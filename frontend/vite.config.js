import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';

function parsePort(value) {
  if (value == null || String(value).trim() === '') return undefined;
  const n = Number.parseInt(String(value).trim(), 10);
  if (!Number.isFinite(n) || n < 1 || n > 65535) return undefined;
  return n;
}

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  const devPort = parsePort(env.FRONTEND_PORT) ?? 5173;

  return {
    plugins: [react()],
    server: {
      port: devPort,
      proxy: {
        '/api': {
          target: env.VITE_BACKEND_URL,
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/api/, '')
        }
      }
    }
  };
});
