/// <reference types="vitest" />
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import basicSsl from '@vitejs/plugin-basic-ssl';

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    react(),
    basicSsl(),
  ],
  server: {
    port: 53000,
    strictPort: true, // Fail with port conflict rather than silently switching ports
    host: 'localhost',
    open: false,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:3978',
        changeOrigin: true,
      },
    },
  },
  preview: {
    port: 53000,
    strictPort: true,
    host: 'localhost',
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './src/test/setup.ts',
  },
});
