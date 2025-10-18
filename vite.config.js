// vite.config.js
import { defineConfig } from 'vite';
import { fileURLToPath, URL } from 'url';

export default defineConfig({
  clearScreen: false,
  cacheDir: 'node_modules/.vite-emergence',

  server: {
    port: 5173,
    fs: {
      strict: true,
      // On limite explicitement aux fichiers front utiles
      allow: ['.', './src/frontend', './index.html'],
    },
    watch: {
      // Sous Windows, le polling ralentit tout : off
      usePolling: false,
      // On ignore tout ce qui n’est pas front
      ignored: [
        '**/src/backend/**',
        '**/src/backend/**/**',
        '**/src/backend/data/**',
        '**/.venv/**',
        '**/.git/**',
        '**/dist/**',
      ],
    },
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false,
      },
      '/ws': {
        target: 'ws://localhost:8000',
        ws: true,
        changeOrigin: true,
        rewriteWsOrigin: true,
      },
    }
  },

  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src/frontend', import.meta.url))
    }
  },

  optimizeDeps: {
    // Pré-bundle au bon endroit en dev
    entries: ['src/frontend/main.js'],
    include: ['marked'],
  },

  build: {
    outDir: './dist',
    emptyOutDir: true,
    target: 'es2019',
    cssCodeSplit: true,
    rollupOptions: {
      output: {
        // Sépare tout node_modules en "vendor"
        manualChunks(id) {
          return id.includes('node_modules') ? 'vendor' : undefined;
        }
      }
    }
  },

  esbuild: { legalComments: 'none' }
});
