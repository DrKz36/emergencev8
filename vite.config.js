// vite.config.js
import { defineConfig } from 'vite';
import { fileURLToPath, URL } from 'url';
import { visualizer } from 'rollup-plugin-visualizer';

const shouldAnalyze = process.env.ANALYZE_BUNDLE === '1';

export default defineConfig({
  clearScreen: false,
  cacheDir: 'node_modules/.vite-emergence',
  plugins: [
    shouldAnalyze && visualizer({
      filename: 'dist/bundle-report.html',
      template: 'treemap',
      gzipSize: true,
      brotliSize: true,
      emitFile: true,
    }),
    shouldAnalyze && visualizer({
      filename: 'dist/bundle-report.json',
      template: 'raw-data',
      gzipSize: true,
      brotliSize: true,
      emitFile: true,
    }),
  ].filter(Boolean),

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
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        secure: false,
      },
      '/ws': {
        target: 'ws://127.0.0.1:8000',
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
        // Regroupe les dépendances lourdes dans des chunks dédiés
        manualChunks(id) {
          if (!id.includes('node_modules')) return undefined;
          if (id.includes('marked')) return 'markdown';
          return 'vendor';
        }
      }
    }
  },

  esbuild: { legalComments: 'none' }
});
