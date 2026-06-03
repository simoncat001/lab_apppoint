import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { User, LoginRequest } from '@/types'
import { login as loginApi, logout as logoutApi, getCurrentUser } from '@/api/auth'

export const useAuthStore = defineStore('auth', () => {
    const user = ref<User | null>(null)
    const token = ref<string>('')
    const isAuthenticated = ref(false)

    const clearAuthState = () => {
        token.value = ''
        user.value = null
        isAuthenticated.value = false

        localStorage.removeItem('access_token')
        localStorage.removeItem('user')
        localStorage.removeItem('current_project_id')
        localStorage.removeItem('current_project_name')
    }

    // 从 localStorage 恢复状态
    const checkAuth = () => {
        const savedToken = localStorage.getItem('access_token')
        const savedUser = localStorage.getItem('user')

        token.value = savedToken || ''
        user.value = null
        isAuthenticated.value = false

        if (savedUser && savedUser !== 'undefined') {
            try {
                user.value = JSON.parse(savedUser)
            } catch (_error) {
                localStorage.removeItem('user')
            }
        }

        isAuthenticated.value = !!token.value && !!user.value
    }

    const initializeAuth = async () => {
        checkAuth()
        if (!token.value) return

        try {
            const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL || '/api').replace(/\/$/, '')
            const response = await fetch(`${apiBaseUrl}/auth/me`, {
                headers: {
                    Authorization: `Bearer ${token.value}`,
                },
            })

            if (!response.ok) {
                throw new Error(`Auth initialization failed with status ${response.status}`)
            }

            const userData = (await response.json()) as User
            user.value = userData
            isAuthenticated.value = true
            localStorage.setItem('user', JSON.stringify(userData))
        } catch (_error) {
            clearAuthState()
        }
    }

    // 登录
    const login = async (credentials: LoginRequest) => {
        const response = await loginApi(credentials)
        token.value = response.access_token
        localStorage.setItem('access_token', response.access_token)

        if (response.user) {
            user.value = response.user
            localStorage.setItem('user', JSON.stringify(response.user))
        } else {
            // Fallback: fetch user if not provided in login response
            const userData = await getCurrentUser()
            user.value = userData
            localStorage.setItem('user', JSON.stringify(userData))
        }

        isAuthenticated.value = true

        return response
    }

    // 登出
    const logout = async () => {
        try {
            await logoutApi()
        } finally {
            clearAuthState()
        }
    }

    // 刷新用户信息
    const refreshUser = async () => {
        const userData = await getCurrentUser()
        user.value = userData
        localStorage.setItem('user', JSON.stringify(userData))
    }

    // 权限检查
    const hasPermission = (_permission: string): boolean => {
        if (!user.value) return false
        if (user.value.is_superuser) return true
        // 这里可以根据实际权限系统扩展
        return canUseManagementFeatures()
    }

    const isExternalUser = (): boolean => {
        if (!user.value) return false
        const source = (user.value.auth_source || 'local').toLowerCase()
        return source === 'local' && !user.value.is_superuser
    }

    const isInternalUser = (): boolean => {
        if (!user.value) return false
        return (user.value.auth_source || 'local').toLowerCase() === 'security_server'
    }

    const canUseManagementFeatures = (): boolean => {
        if (!user.value) return false
        if (user.value.is_superuser) return true
        if (isExternalUser()) return false
        return !!user.value.is_staff
    }

    const isStaff = (): boolean => {
        return canUseManagementFeatures()
    }

    const isSuperuser = (): boolean => {
        return user.value?.is_superuser || false
    }

    const isVerified = (): boolean => {
        return user.value?.is_verified || false
    }

    const canAccessReservations = (): boolean => {
        if (!user.value) return false
        if (isStaff()) return true
        return user.value.is_verified
    }

    return {
        user,
        token,
        isAuthenticated,
        clearAuthState,
        checkAuth,
        initializeAuth,
        login,
        logout,
        refreshUser,
        hasPermission,
        isExternalUser,
        isInternalUser,
        canUseManagementFeatures,
        isStaff,
        isSuperuser,
        isVerified,
        canAccessReservations,
    }
})
