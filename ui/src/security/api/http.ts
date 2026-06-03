import axios, { type AxiosInstance, type AxiosRequestConfig } from 'axios';

// Default to the in-process path served by nemo-backend. The legacy
// `http://localhost:8299` (standalone Spring service) is gone now; staff
// endpoints live at `/security-api/api/*` on the same origin as nemo-ui.
const baseURL = import.meta.env.VITE_API_BASE || '/security-api';

interface ApiClient extends AxiosInstance {
  get<T = unknown>(url: string, config?: AxiosRequestConfig): Promise<T>;
  post<T = unknown>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T>;
  put<T = unknown>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T>;
  delete<T = unknown>(url: string, config?: AxiosRequestConfig): Promise<T>;
}

export const api = axios.create({
  baseURL,
  timeout: 15000
}) as ApiClient;

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('security.token');
  if (token) {
    config.headers = config.headers || {};
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => {
    const payload = response.data;
    if (payload && typeof payload.code === 'number') {
      if (payload.code !== 200) {
        return Promise.reject(new Error(payload.message || '请求失败'));
      }
      return payload.data;
    }
    return payload;
  },
  (error) => {
    const status = error.response?.status;
    if (status === 401) {
      localStorage.removeItem('security.token');
      localStorage.removeItem('security.user');
      // Staff SPA is now mounted under /security/ inside nemo-ui, so the
      // login path moves with it.
      if (!window.location.pathname.startsWith('/security/login')) {
        window.location.href = '/security/login';
      }
    }
    return Promise.reject(error);
  }
);
