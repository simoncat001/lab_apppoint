/**
 * 预约管理 API
 */

import request from '@/utils/request'
import type { Reservation, ReservationOccupiedSlot } from '@/types'

/**
 * 获取预约列表
 */
export const getReservations = (params?: {
    skip?: number
    limit?: number
    user_id?: number
    tool_id?: number
    category_id?: number
    start_date?: string
    end_date?: string
    include_all?: boolean
    cancelled?: boolean
}) => {
    return request.get<Reservation[]>('/reservations/', { params })
}

export const getOccupiedReservationSlots = (params: {
    tool_id: number
    start_date: string
    end_date: string
}): Promise<ReservationOccupiedSlot[]> => {
    return request.get<ReservationOccupiedSlot[]>('/reservations/occupied', { params }) as unknown as Promise<ReservationOccupiedSlot[]>
}

/**
 * 获取单个预约详情
 */
export const getReservation = (id: number) => {
    return request.get<Reservation>(`/reservations/${id}`)
}

/**
 * 创建新预约
 */
export const createReservation = (data: Partial<Reservation>) => {
    return request.post<Reservation>('/reservations/', data)
}

/**
 * 更新预约
 */
export const updateReservation = (id: number, data: Partial<Reservation>) => {
    return request.put<Reservation>(`/reservations/${id}`, data)
}

/**
 * 取消预约
 */
export const cancelReservation = (id: number) => {
    return request.delete(`/reservations/${id}`)
}

/**
 * 预约支付
 */
export const payReservation = (id: number, data?: { amount?: number; method?: string }) => {
    return request.post<Reservation>(`/reservations/${id}/pay`, data)
}

/**
 * 实验完成填报
 */
export const completeReservation = (
    id: number,
    data: { actual_start?: string; actual_end?: string; completion_note?: string }
) => {
    return request.post<Reservation>(`/reservations/${id}/complete`, data)
}

/**
 * 导出预约 CSV（浏览器下载）
 */
export const exportReservationsCsv = () => {
    return request.get(`/reservations/export`, { responseType: 'blob' }).then((res: any) => {
        const blob = new Blob([res], { type: 'text/csv;charset=utf-8;' })
        const url = window.URL.createObjectURL(blob)
        const link = document.createElement('a')
        link.href = url
        link.setAttribute('download', `reservations_${Date.now()}.csv`)
        document.body.appendChild(link)
        link.click()
        document.body.removeChild(link)
        window.URL.revokeObjectURL(url)
    })
}

/**
 * 获取工具的预约列表
 */
export const getToolReservations = (toolId: number, params?: {
    start_date?: string
    end_date?: string
}) => {
    return request.get<Reservation[]>('/reservations/', {
        params: {
            tool_id: toolId,
            ...params
        }
    })
}

/**
 * 获取用户的预约列表
 */
export const getUserReservations = (userId: number, params?: {
    start_date?: string
    end_date?: string
}) => {
    return request.get<Reservation[]>('/reservations/', {
        params: {
            user_id: userId,
            ...params
        }
    })
}

/**
 * 获取指定日期范围的预约
 */
export const getReservationsByDateRange = (startDate: string, endDate: string, params?: {
    tool_id?: number
    user_id?: number
}) => {
    return request.get<Reservation[]>('/reservations/', {
        params: {
            start_date: startDate,
            end_date: endDate,
            ...params
        }
    })
}

/**
 * 获取预约统计信息
 */
export const getReservationStats = () => {
    // 如果后端没有提供统计端点，前端可以通过获取数据后自行统计
    return request.get<Reservation[]>('/reservations/', { params: { limit: 1000 } })
}

/**
 * 获取今日预约（管理员）
 */
export const getTodayReservations = () => {
    return request.get<Reservation[]>('/reservations/today')
}
