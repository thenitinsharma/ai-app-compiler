import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

const isVercel = process.env.BUILD_TARGET === 'vercel' || process.env.VERCEL === '1';

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
  ],
  base: isVercel ? '/' : '/static/',
  build: {
    outDir: isVercel ? 'dist' : '../static',
    emptyOutDir: true,
  }
})

