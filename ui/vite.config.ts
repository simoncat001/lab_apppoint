import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'
import AutoImport from 'unplugin-auto-import/vite'
import Components from 'unplugin-vue-components/vite'
import { ElementPlusResolver } from 'unplugin-vue-components/resolvers'

// https://vitejs.dev/config/
export default defineConfig({
    plugins: [
        vue(),
        AutoImport({
            // Element Plus styles are already imported globally in `src/main.ts`.
            // Disabling per-component style imports avoids Vite re-optimizing deep
            // `element-plus/es/components/*/style/css` deps during dev.
            resolvers: [ElementPlusResolver({ importStyle: false })],
            imports: ['vue', 'vue-router', 'pinia'],
            dts: 'src/auto-imports.d.ts',
        }),
        Components({
            resolvers: [ElementPlusResolver({ importStyle: false })],
            dts: 'src/components.d.ts',
        }),
    ],
    resolve: {
        alias: {
            '@': resolve(__dirname, 'src'),
        },
    },
    server: {
        host: '0.0.0.0',
        port: 3000,
        proxy: {
            '/api': {
                target: 'http://127.0.0.1:8000',
                changeOrigin: true,
                // Keep FastAPI's trailing-slash redirects on the Vite origin
                // instead of leaking the backend origin to the browser.
                autoRewrite: true,
            },
            '/media': {
                target: 'http://127.0.0.1:8000',
                changeOrigin: true,
            },
            // Staff endpoints (ported from the old Spring service) live on
            // the same backend process under /security-api/api/*.
            '/security-api': {
                target: 'http://127.0.0.1:8000',
                changeOrigin: true,
            },
        },
    },
    build: {
        outDir: 'dist',
        sourcemap: false,
    },
})
