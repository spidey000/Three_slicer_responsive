import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  base: '/Three_slicer_responsive/',
  plugins: [react()],
  resolve: { dedupe: ['react', 'react-dom', 'three'] },
  worker: { format: 'es' },
  build: { target: 'es2022', sourcemap: true },
})
