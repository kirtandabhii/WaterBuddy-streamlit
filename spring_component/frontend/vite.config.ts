import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// `base: './'`: Streamlit serves the built component from its own folder, so every
// asset (scripts, Ripple's model, the still picture) must be referenced relatively.
export default defineConfig({
  base: './',
  plugins: [react()],
  build: { outDir: 'dist', emptyOutDir: true, chunkSizeWarningLimit: 1200 }
});
