import axios, {
    AxiosInstance,
    AxiosResponse,
    AxiosError,
    InternalAxiosRequestConfig,
    AxiosRequestConfig,
} from 'axios'
import { ElMessage } from 'element-plus'
import router from '@/router'

const AUTH_BYPASS_PATHS = new Set([
    '/auth/login',
    '/auth/login/json',
    '/auth/register',
    '/auth/verification-code',
])

function isAuthBypassRequest(url?: string): boolean {
    if (!url) return false
    for (const path of AUTH_BYPASS_PATHS) {
        if (url.startsWith(path)) return true
    }
    return false
}

// 创建 axios 实例
const service: AxiosInstance = axios.create({
    baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
    timeout: 30000,
    headers: {
        'Content-Type': 'application/json',
    },
})

// 请求拦截器
service.interceptors.request.use(
    (config: InternalAxiosRequestConfig) => {
        // 添加 token
        const token = localStorage.getItem('access_token')
        if (token) {
            config.headers = config.headers || {}
                ; (config.headers as any).Authorization = `Bearer ${token}`
        }
        const currentProjectId = localStorage.getItem('current_project_id')
        if (currentProjectId) {
            config.headers = config.headers || {}
            ; (config.headers as any)['X-Current-Project-Id'] = currentProjectId
        }
        return config
    },
    (error: AxiosError) => {
        console.error('Request error:', error)
        return Promise.reject(error)
    }
)

// 响应拦截器
service.interceptors.response.use(
    (response: AxiosResponse) => {
        const data = response.data
        const totalHeader = response.headers?.['x-total-count']
        if (totalHeader != null && data && typeof data === 'object') {
            try {
                Object.defineProperty(data, '_total', {
                    value: Number(totalHeader),
                    enumerable: false,
                    configurable: true,
                    writable: true,
                })
            } catch {
                // ignore: data is frozen / not extensible
            }
        }
        return data
    },
    (error: AxiosError) => {
        if ((error.config as any)?.skipGlobalErrorHandler) {
            return Promise.reject(error)
        }

        console.error('Response error:', error)

        if (error.response) {
            const requestUrl = String(error.config?.url || '')
            switch (error.response.status) {
                case 401:
                    if (isAuthBypassRequest(requestUrl)) {
                        break
                    }

                    ElMessage.error('登录已过期，请重新登录')
                    localStorage.removeItem('access_token')
                    localStorage.removeItem('user')
                    localStorage.removeItem('current_project_id')
                    localStorage.removeItem('current_project_name')

                    if (router.currentRoute.value.name !== 'Login') {
                        const redirect = router.currentRoute.value.fullPath
                        const loginUrl =
                            redirect && redirect !== '/login'
                                ? `/login?redirect=${encodeURIComponent(redirect)}`
                                : '/login'
                        window.location.assign(loginUrl)
                    }
                    break
                case 403:
                    ElMessage.error('没有权限访问该资源')
                    break
                case 404:
                    ElMessage.error('请求的资源不存在')
                    break
                case 500:
                    ElMessage.error('服务器内部错误')
                    break
                default:
                    ElMessage.error((error.response.data as any)?.detail || '请求失败')
            }
        } else if (error.request) {
            ElMessage.error('网络连接失败，请检查网络')
        } else {
            ElMessage.error('请求配置错误')
        }

        return Promise.reject(error)
    }
)

type DataResponseRequest = Omit<
    AxiosInstance,
    'get' | 'delete' | 'post' | 'put' | 'patch' | 'head' | 'options'
> & {
    <T = any>(config: AxiosRequestConfig): Promise<T>
    <T = any>(url: string, config?: AxiosRequestConfig): Promise<T>
    get<T = any>(url: string, config?: AxiosRequestConfig): Promise<T>
    delete<T = any>(url: string, config?: AxiosRequestConfig): Promise<T>
    post<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T>
    put<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T>
    patch<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T>
    head<T = any>(url: string, config?: AxiosRequestConfig): Promise<T>
    options<T = any>(url: string, config?: AxiosRequestConfig): Promise<T>
}

export default service as DataResponseRequest
