import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import 'element-plus/theme-chalk/dark/css-vars.css'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'

import App from './App.vue'
import router from './router'
import { useAuthStore } from '@/stores/auth' // Import auth store
import { useProjectContextStore } from '@/stores/project-context'
import './assets/styles/main.css'
// Staff (security) SPA styles. Scoped to .staff-* selectors / its own
// shell, so it won't clobber nemo's styling — see security/styles/global.css.
import '@/security/styles/global.css'

async function bootstrap() {
    const app = createApp(App)
    const pinia = createPinia()

    // 注册所有 Element Plus 图标
    for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
        app.component(key, component)
    }

    app.use(pinia)

    const authStore = useAuthStore()
    await authStore.initializeAuth()
    const projectContextStore = useProjectContextStore()
    projectContextStore.hydrate()

    // Staff (internal-employee) area has its own auth store. Hydrating it
    // here means the staff SPA can read token state synchronously on first
    // render, exactly like the nemo store above.
    const { useStaffAuthStore } = await import('@/security/stores/auth')
    useStaffAuthStore().hydrate()

    app.use(router)
    app.use(ElementPlus)

    await router.isReady()
    app.mount('#app')
}

bootstrap()
