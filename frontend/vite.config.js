import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
import { VitePWA } from 'vite-plugin-pwa';

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    vue(),
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['favicon.ico', 'apple-touch-icon.png', 'masked-icon.svg'],
      manifest: {
        name: 'School POS System',
        short_name: 'SchoolPOS',
        description: 'Sistema de Gestión de Cafetería Escolar',
        theme_color: '#3b82f6',
        icons: [
          {
            src: 'pwa-192x192.png', // Debes crear estos iconos luego
            sizes: '192x192',
            type: 'image/png'
          },
          {
            src: 'pwa-512x512.png',
            sizes: '512x512',
            type: 'image/png'
          },
          {
            src: 'pwa-512x512.png',
            sizes: '512x512',
            type: 'image/png',
            purpose: 'any maskable' // Importante para Android
          }
        ]
      }
    })
  ],
  server: {
    host: true // Importante para probar en movil via red local
  }
});