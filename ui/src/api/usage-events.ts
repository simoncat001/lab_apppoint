import request from '@/utils/request'
import type { UsageEvent, UsageEventStats } from '@/types'

// ==================== 使用事件管理 ====================

/**
 * 获取使用记录列表
 */
export const getUsageEvents = (params?: {
    tool_id?: number
    category_id?: number
    user_id?: number
    operator_id?: number
    project_id?: number
    status?: 'pending' | 'charged' | 'waived' | 'in_progress'
    validated?: boolean
    start_date?: string
    end_date?: string
    skip?: number
    limit?: number
}) => {
    return request.get<UsageEvent[]>('/usage-events/', { params }).then((res: any) => res as UsageEvent[])
}

/**
 * 创建使用记录
 */
export const createUsageEvent = (data: Partial<UsageEvent>) => {
    return request.post<UsageEvent>('/usage-events/', data).then((res: any) => res as UsageEvent)
}

/**
 * 获取使用记录详情
 */
export const getUsageEvent = (eventId: number) => {
    return request.get<UsageEvent>(`/usage-events/${eventId}`).then((res: any) => res as UsageEvent)
}

/**
 * 结束使用记录
 */
export const endUsageEvent = (eventId: number, data?: { run_data?: string }) => {
    return request.post<UsageEvent>(`/usage-events/${eventId}/end`, data || {}).then((res: any) => res as UsageEvent)
}

/**
 * 更新使用记录
 */
export const updateUsageEvent = (eventId: number, data: Partial<UsageEvent>) => {
    return request.put<UsageEvent>(`/usage-events/${eventId}`, data).then((res: any) => res as UsageEvent)
}

/**
 * 删除使用记录
 */
export const deleteUsageEvent = (eventId: number) => {
    return request.delete(`/usage-events/${eventId}`)
}

// ==================== 活动查询 ====================

/**
 * 获取工具的活动使用记录
 */
export const getToolActiveUsage = (toolId: number) => {
    return request
        .get<UsageEvent | null>(`/usage-events/tool/${toolId}/active`, {
            skipGlobalErrorHandler: true,
        } as any)
        .then((res: any) => (res || null) as UsageEvent | null)
        .catch((error: any) => {
            if (error?.response?.status === 404) return null
            return Promise.reject(error)
        })
}

/**
 * 获取用户的活动使用记录
 */
export const getUserActiveUsages = (userId: number) => {
    return request.get<UsageEvent[]>(`/usage-events/user/${userId}/active`).then((res: any) => res as UsageEvent[])
}

// ==================== 验证与豁免 ====================

/**
 * 验证使用记录
 */
export const validateUsageEvent = (eventId: number) => {
    return request.post<UsageEvent>(`/usage-events/${eventId}/validate`).then((res: any) => res as UsageEvent)
}

/**
 * 豁免使用记录
 */
export const waiveUsageEvent = (eventId: number) => {
    return request.post<UsageEvent>(`/usage-events/${eventId}/waive`).then((res: any) => res as UsageEvent)
}

/**
 * 重新激活（取消豁免）使用记录
 */
export const reactivateUsageEvent = (eventId: number) => {
    return request.post<UsageEvent>(`/usage-events/${eventId}/reactivate`).then((res: any) => res as UsageEvent)
}

// ==================== 统计 ====================

/**
 * 获取使用统计
 */
export const getUsageEventStats = (params?: {
    tool_id?: number
    user_id?: number
    category_id?: number
    status?: 'pending' | 'charged' | 'waived' | 'in_progress'
    start_date?: string
    end_date?: string
}) => {
    return request.get<UsageEventStats>('/usage-events/stats', { params }).then((res: any) => res as UsageEventStats)
}
