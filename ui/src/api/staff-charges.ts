import request from '@/utils/request'
import type { StaffCharge, ApiResponse } from '@/types'

// ==================== 员工收费管理 ====================

/**
 * 获取员工收费列表
 */
export const getStaffCharges = (params?: {
    staff_member_id?: number
    customer_id?: number
    validated?: boolean
    start_date?: string
    end_date?: string
    skip?: number
    limit?: number
}) => {
    return request.get<ApiResponse<StaffCharge[]>>('/staff-charges/', { params })
}

/**
 * 创建员工收费记录
 */
export const createStaffCharge = (data: Partial<StaffCharge>) => {
    return request.post<ApiResponse<StaffCharge>>('/staff-charges/', data)
}

/**
 * 获取员工收费详情
 */
export const getStaffCharge = (chargeId: number) => {
    return request.get<ApiResponse<StaffCharge>>(`/staff-charges/${chargeId}`)
}

/**
 * 结束服务
 */
export const endStaffCharge = (chargeId: number, data?: { end?: string }) => {
    return request.post<ApiResponse<StaffCharge>>(`/staff-charges/${chargeId}/end`, data)
}

/**
 * 更新员工收费记录
 */
export const updateStaffCharge = (chargeId: number, data: Partial<StaffCharge>) => {
    return request.put<ApiResponse<StaffCharge>>(`/staff-charges/${chargeId}`, data)
}

/**
 * 删除员工收费记录
 */
export const deleteStaffCharge = (chargeId: number) => {
    return request.delete(`/staff-charges/${chargeId}`)
}

// ==================== 活动查询 ====================

/**
 * 获取员工的活动收费记录
 */
export const getStaffMemberActiveCharges = (staffMemberId: number) => {
    return request.get<ApiResponse<StaffCharge[]>>(`/staff-charges/staff/${staffMemberId}/active`)
}

/**
 * 获取客户的活动收费记录
 */
export const getCustomerActiveCharges = (customerId: number) => {
    return request.get<ApiResponse<StaffCharge[]>>(`/staff-charges/customer/${customerId}/active`)
}

// ==================== 验证与豁免 ====================

/**
 * 验证员工收费记录
 */
export const validateStaffCharge = (chargeId: number) => {
    return request.post<ApiResponse<StaffCharge>>(`/staff-charges/${chargeId}/validate`)
}

/**
 * 豁免员工收费记录
 */
export const waiveStaffCharge = (chargeId: number) => {
    return request.post<ApiResponse<StaffCharge>>(`/staff-charges/${chargeId}/waive`)
}

// ==================== 统计 ====================

/**
 * 获取员工收费统计
 */
export const getStaffChargeStats = (params?: {
    staff_member_id?: number
    customer_id?: number
    start_date?: string
    end_date?: string
}) => {
    return request.get<ApiResponse<{
        total_charges: number
        total_cost: number
        validated_charges: number
        pending_charges: number
    }>>('/staff-charges/stats', { params })
}
