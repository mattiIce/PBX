import { defineConfig } from 'vite';
import { resolve } from 'path';

export default defineConfig({
  root: resolve(__dirname),
  build: {
    outDir: 'dist',
    rollupOptions: {
      input: {
        main: resolve(__dirname, 'index.html'),
        login: resolve(__dirname, 'html/login.html'),
      },
    },
  },
  server: {
    proxy: {
      '/api': 'http://localhost:9000',
      '/health': 'http://localhost:9000',
      '/provision': 'http://localhost:9000',
    },
  },
});
