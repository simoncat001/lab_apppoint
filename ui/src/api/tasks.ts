import request from '@/utils/request'
import { TaskUrgency, type Task, type TaskCategory, type ApiResponse } from '@/types'

const urgencyToApiValue = (urgency: Task['urgency'] | number | undefined): number | undefined => {
    if (typeof urgency === 'number') return urgency
    if (urgency === TaskUrgency.LOW || urgency === 'low') return -1
    if (urgency === TaskUrgency.NORMAL || urgency === 'normal' || urgency === 'medium') return 0
    if (urgency === TaskUrgency.HIGH || urgency === 'high') return 1
    return undefined
}

const normalizeTaskPayload = (data: Partial<Task>) => {
    const payload: Record<string, unknown> = { ...data }
    const urgency = urgencyToApiValue(data.urgency)
    if (urgency !== undefined) payload.urgency = urgency
    if (data.category_id !== undefined && data.problem_category_id === undefined) {
        payload.problem_category_id = data.category_id
    }
    delete payload.category_id
    Object.keys(payload).forEach((key) => {
        if (payload[key] === undefined || payload[key] === '') delete payload[key]
    })
    return payload
}

// ==================== 任务分类管理 ====================

/**
 * 获取任务分类列表
 */
export const getTaskCategories = () => {
    return request.get<ApiResponse<TaskCategory[]>>('/tasks/task-categories')
}

/**
 * 创建任务分类
 */
export const createTaskCategory = (data: Partial<TaskCategory>) => {
    return request.post<ApiResponse<TaskCategory>>('/tasks/task-categories', data)
}

/**
 * 获取任务分类详情
 */
export const getTaskCategory = (categoryId: number) => {
    return request.get<ApiResponse<TaskCategory>>(`/tasks/task-categories/${categoryId}`)
}

/**
 * 更新任务分类
 */
export const updateTaskCategory = (categoryId: number, data: Partial<TaskCategory>) => {
    return request.put<ApiResponse<TaskCategory>>(`/tasks/task-categories/${categoryId}`, data)
}

/**
 * 删除任务分类
 */
export const deleteTaskCategory = (categoryId: number) => {
    return request.delete(`/tasks/task-categories/${categoryId}`)
}

// ==================== 任务管理 ====================

/**
 * 获取任务列表
 */
export const getTasks = (params?: {
    resolved?: boolean
    cancelled?: boolean
    urgency?: string | number
    category_id?: number
    tool_id?: number
    creator_id?: number
    skip?: number
    limit?: number
}) => {
    const normalizedParams = {
        ...params,
        urgency: urgencyToApiValue(params?.urgency),
        resolved_only: params?.resolved,
    }
    delete (normalizedParams as any).resolved
    delete (normalizedParams as any).cancelled
    delete (normalizedParams as any).category_id
    return request.get<ApiResponse<Task[]>>('/tasks/', { params: normalizedParams })
}

/**
 * 创建任务
 */
export const createTask = (data: Partial<Task>) => {
    return request.post<ApiResponse<Task>>('/tasks/', normalizeTaskPayload(data))
}

/**
 * 获取任务详情
 */
export const getTask = (taskId: number) => {
    return request.get<ApiResponse<Task>>(`/tasks/${taskId}`)
}

/**
 * 更新任务
 */
export const updateTask = (taskId: number, data: Partial<Task>) => {
    return request.put<ApiResponse<Task>>(`/tasks/${taskId}`, normalizeTaskPayload(data))
}

/**
 * 解决任务
 */
export const resolveTask = (taskId: number, data: { resolution_description: string }) => {
    return request.post<ApiResponse<Task>>(`/tasks/${taskId}/resolve`, data)
}

/**
 * 取消任务
 */
export const cancelTask = (taskId: number, data: { resolution_description?: string }) => {
    return request.post<ApiResponse<Task>>(`/tasks/${taskId}/cancel`, data)
}

/**
 * 删除任务
 */
export const deleteTask = (taskId: number) => {
    return request.delete(`/tasks/${taskId}`)
}

// ==================== 任务历史 ====================

/**
 * 获取任务历史
 */
export const getTaskHistory = (taskId: number) => {
    return request.get<ApiResponse<any[]>>(`/tasks/${taskId}/history`)
}

// ==================== 特殊查询 ====================

/**
 * 获取紧急任务列表
 */
export const getUrgentTasks = () => {
    return request.get<ApiResponse<Task[]>>('/tasks/urgent')
}

/**
 * 获取任务统计
 */
export const getTaskStats = (params?: {
    tool_id?: number
    category_id?: number
    days?: number
}) => {
    return request.get<ApiResponse<{
        total_tasks: number
        resolved_tasks: number
        pending_tasks: number
        urgent_tasks: number
    }>>('/tasks/stats', { params })
}
