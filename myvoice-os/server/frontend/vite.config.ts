import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { resolve } from 'path';

export default defineConfig({
  plugins: [react()],
  build: {
    outDir: process.env.VERCEL ? 'dist' : resolve(__dirname, '../static'),
    emptyOutDir: false,
  },
  server: {
    proxy: {
      '/api': {
        target: process.env.SERVER_URL || 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
});
