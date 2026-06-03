import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useAppStore = defineStore('app', () => {
    const sidebarCollapsed = ref(false)
    const theme = ref<'light' | 'dark'>('light')
    const loading = ref(false)

    // 切换侧边栏
    const toggleSidebar = () => {
        sidebarCollapsed.value = !sidebarCollapsed.value
    }

    // 设置主题
    const setTheme = (newTheme: 'light' | 'dark') => {
        theme.value = newTheme
        document.documentElement.className = newTheme
        localStorage.setItem('theme', newTheme)
    }

    // 初始化主题
    const initTheme = () => {
        const savedTheme = localStorage.getItem('theme') as 'light' | 'dark' | null
        if (savedTheme) {
            setTheme(savedTheme)
        }
    }

    // 全局加载状态
    const setLoading = (value: boolean) => {
        loading.value = value
    }

    return {
        sidebarCollapsed,
        theme,
        loading,
        toggleSidebar,
        setTheme,
        initTheme,
        setLoading,
    }
})
