import { defineConfig } from 'vite';
import { dirname, resolve } from 'path';
import { fileURLToPath } from 'url';
import { copyFileSync, cpSync, mkdirSync, existsSync } from 'fs';

const __dirname = dirname(fileURLToPath(import.meta.url));

/**
 * Vite plugin to copy non-module scripts and static assets to dist/.
 *
 * Vite only bundles <script type="module"> tags. The legacy non-module
 * scripts referenced in index.html (webrtc_phone.js, framework_features.js,
 * etc.) must be copied verbatim so they are available at runtime.
 */
function copyStaticAssets() {
  const nonModuleScripts = [
    'js/webrtc_phone.js',
    'js/framework_features.js',
    'js/auto_attendant.js',
    'js/voicemail_enhanced.js',
    'js/opensource_integrations.js',
  ];

  return {
    name: 'copy-static-assets',
    writeBundle() {
      const outDir = resolve(__dirname, 'dist');

      // Copy non-module JS files
      const jsDir = resolve(outDir, 'js');
      if (!existsSync(jsDir)) mkdirSync(jsDir, { recursive: true });

      for (const script of nonModuleScripts) {
        const src = resolve(__dirname, script);
        const dest = resolve(outDir, script);
        if (existsSync(src)) {
          copyFileSync(src, dest);
        }
      }

      // Copy static assets (favicons, logo)
      const imgSrc = resolve(__dirname, 'assets', 'images');
      const imgDest = resolve(outDir, 'assets', 'images');
      if (existsSync(imgSrc)) {
        cpSync(imgSrc, imgDest, { recursive: true });
      }
    },
  };
}

export default defineConfig({
  root: resolve(__dirname),
  base: '/admin/',
  build: {
    outDir: 'dist',
    target: 'es2024',
    sourcemap: false,
    minify: 'esbuild',
    cssMinify: true,
    rollupOptions: {
      input: {
        main: resolve(__dirname, 'index.html'),
        login: resolve(__dirname, 'login.html'),
      },
      output: {
        manualChunks: {
          vendor: [],
        },
        assetFileNames: 'assets/[name]-[hash][extname]',
        chunkFileNames: 'assets/[name]-[hash].js',
        entryFileNames: 'assets/[name]-[hash].js',
      },
    },
  },
  plugins: [copyStaticAssets()],
  server: {
    proxy: {
      '/api': 'http://localhost:9000',
      '/health': 'http://localhost:9000',
      '/provision': 'http://localhost:9000',
    },
  },
});
