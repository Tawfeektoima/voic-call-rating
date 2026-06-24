import { defineConfig } from 'vitest/config';
import path from 'path';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  test: {
    globals: true,
    environment: './src/app/__tests__/custom-jsdom-env.ts',
    setupFiles: './src/app/__tests__/setup.ts',
  },
});
