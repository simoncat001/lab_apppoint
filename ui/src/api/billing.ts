import request from '@/utils/request'
import type { Bill, BillDetail, BillGenerationRequest, BillUpdateRequest, PaginationParams } from '@/types'

// ==================== 账单管理 ====================

/**
 * 获取账单列表
 */
export const getBills = (params: PaginationParams & { account_id?: number }) => {
    return request.get<Bill[]>('/billing/', { params })
}

/**
 * 生成账单
 */
export const generateBills = (data: BillGenerationRequest) => {
    return request.post<Bill[]>('/billing/generate', data)
}

/**
 * 更新账单（管理员）
 */
export const updateBill = (billId: number, data: BillUpdateRequest) => {
    return request.put<Bill>(`/billing/${billId}`, data)
}

/**
 * 获取账单详情
 */
export const getBillDetail = (billId: number) => {
    return request.get<BillDetail>(`/billing/${billId}`)
}

/**
 * 获取账单支付二维码
 */
