import { fileURLToPath } from 'node:url';

import react from '@vitejs/plugin-react';
import { loadEnv } from 'vite';
import { defineConfig } from 'vitest/config';

/** First non-empty string, so `VITE_GATEWAY_URL=""` (same-origin) is not a target. */
function firstNonEmpty(...values: Array<string | undefined>): string | undefined {
  return values.find((v) => v !== undefined && v !== '');
}

// `.env` lives at the repo root (root CLAUDE.md §1.5). Only VITE_* keys reach
// the browser; TRADE_* keys are read here, at config time, and never shipped.
const envDir = fileURLToPath(new URL('..', import.meta.url));

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, envDir, ['TRADE_', 'VITE_']);
  const port = Number(firstNonEmpty(env.TRADE_WEB_PORT, '5173'));
  const gateway = firstNonEmpty(
    env.TRADE_GATEWAY_URL,
    env.VITE_GATEWAY_URL,
    'http://localhost:8787',
  ) as string;

  return {
    plugins: [react()],
    envDir,
    server: {
      port,
      strictPort: true,
      proxy: {
        '/api': { target: gateway, changeOrigin: true },
        '/ws': { target: gateway.replace(/^http/, 'ws'), ws: true },
      },
    },
    preview: { port },
    test: {
      environment: 'jsdom',
      setupFiles: ['src/test/setup.ts'],
      include: ['src/**/*.test.{ts,tsx}'],
    },
  };
});
