import request from '@/utils/request'
import type { LoginRequest, LoginResponse, User } from '@/types'

// 登录
export function login(data: LoginRequest): Promise<LoginResponse> {
    return request({
        // Use JSON-capable login endpoint (backend also exposes OAuth2 form at /auth/login)
        url: '/auth/login/json',
        method: 'post',
        data,
    })
}

// 登出
export function logout(): Promise<void> {
    return request({
        url: '/auth/logout',
        method: 'post',
    })
}

// 获取当前用户信息
export function getCurrentUser(): Promise<User> {
    return request({
        url: '/auth/me',
        method: 'get',
    })
}

// 注册
export function register(data: any): Promise<User> {
    return request({
        url: '/auth/register',
        method: 'post',
        data
    })
}

export function sendVerificationCode(data: any): Promise<any> {
    return request({
        url: '/auth/verification-code',
        method: 'post',
        data,
    })
}
