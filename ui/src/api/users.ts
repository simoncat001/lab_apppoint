/**
 * 用户管理 API
 */

import request from '@/utils/request'
import type { User } from '@/types'

/**
 * 获取用户列表
 */
export const getUsers = (params?: {
    skip?: number
    limit?: number
}) => {
    return request.get<User[]>('/users/', { params })
}

/**
 * 获取单个用户详情
 */
export const getUser = (id: number) => {
    return request.get<User>(`/users/${id}`)
}

/**
 * 创建新用户
 */
export const createUser = (data: Partial<User> & { password: string }) => {
    return request.post<User>('/users/', data)
}

/**
 * 更新用户信息
 */
export const updateUser = (id: number, data: Partial<User>) => {
    return request.put<User>(`/users/${id}`, data)
}

/**
 * 删除用户
 */
export const deleteUser = (id: number) => {
    return request.delete(`/users/${id}`)
}

/**
 * 获取当前登录用户信息
 */
export const getCurrentUser = () => {
    return request.get<User>('/users/me')
}

/**
 * 更新当前用户信息
 */
export const updateCurrentUser = (data: Partial<User>) => {
    return request.put<User>('/users/me', data)
}

/**
 * 修改密码
 */
export const changePassword = (data: {
    old_password: string
    new_password: string
}) => {
    return request.post('/users/change-password', data)
}

/**
 * 激活用户
 */
export const activateUser = (id: number) => {
    return request.post<User>(`/users/${id}/activate`)
}

/**
 * 停用用户
 */
export const deactivateUser = (id: number) => {
    return request.post<User>(`/users/${id}/deactivate`)
}

/**
 * 获取用户统计信息
 */
export const getUserStats = (userId: number) => {
    // 这个可能需要聚合多个 API 的数据
    return Promise.all([
        request.get('/reservations/', { params: { user_id: userId, limit: 1000 } }),
        request.get('/usage-events/', { params: { user_id: userId, limit: 1000 } }),
        request.get('/tasks/', { params: { creator_id: userId, limit: 1000 } })
    ])
}
