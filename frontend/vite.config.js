import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// base './' keeps asset paths relative so the built app works from any subpath
// (GitHub Pages project sites, Vercel, or a plain static host).
export default defineConfig({
  plugins: [react()],
  base: './',
})
