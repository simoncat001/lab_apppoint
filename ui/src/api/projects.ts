import request from '@/utils/request'
import type { Project, ProjectJoinRequest } from '@/types'

/**
 * 获取项目列表
 */
export const getProjects = (params?: {
    active?: boolean
    account_id?: number
    skip?: number
    limit?: number
}) => {
    return request.get<Project[]>('/projects/mirror', { params })
}

/**
 * 获取项目详情
 */
export const getProject = (id: number) => {
    return request.get<Project>(`/projects/mirror/${id}`)
}

/**
 * 配置项目是否对外开放预约权限申请（本地镜像元数据）
 */
export const setProjectExternalBookingAccess = (id: number, allowExternalBookingRequest: boolean) => {
    return request.patch<Project>(`/projects/mirror/${id}/external-booking-access`, {
        allow_external_booking_request: allowExternalBookingRequest,
    })
}

/**
 * 获取权鉴服务原始项目列表响应（透传格式）
 */
export const getProjectsRaw = (params?: {
    active?: boolean
    account_id?: number
    skip?: number
    limit?: number
}) => {
    return request.get('/projects/', { params })
}

/**
 * 获取可申请加入的项目列表
 */
export const getJoinableProjects = () => {
    return request.get<Project[]>('/projects/joinable')
}

/**
 * 获取我的项目加入申请记录
 */
export const getMyProjectJoinRequests = (params?: {
    status?: string
    limit?: number
}) => {
    return request.get<ProjectJoinRequest[]>('/projects/join-requests/my', { params })
}

/**
 * 提交项目加入申请
 */
export const createProjectJoinRequest = (data: {
    target_project_id: number
    reason?: string
}) => {
    return request.post<ProjectJoinRequest>('/projects/join-requests', data)
}

/**
 * 撤销项目加入申请
 */
export const cancelProjectJoinRequest = (requestId: number) => {
    return request.post<ProjectJoinRequest>(`/projects/join-requests/${requestId}/cancel`)
}

/**
 * 获取当前项目下待审批的项目加入申请（需已选择当前项目）
 */
export const getProjectJoinRequestsForApproval = (params?: {
    status?: string
    skip?: number
    limit?: number
}) => {
    return request.get<ProjectJoinRequest[]>('/projects/join-requests/pending-for-approval', { params })
}

/**
 * 审批通过项目加入申请（当前项目管理员）
 */
export const approveProjectJoinRequest = (requestId: number, data?: { comment?: string }) => {
    return request.post<ProjectJoinRequest>(`/projects/join-requests/${requestId}/approve`, data || {})
}

/**
 * 驳回项目加入申请（当前项目管理员）
 */
export const rejectProjectJoinRequest = (requestId: number, data?: { comment?: string }) => {
    return request.post<ProjectJoinRequest>(`/projects/join-requests/${requestId}/reject`, data || {})
}

/**
 * 创建项目
 */
export const createProject = (data: Partial<Project>) => {
    return request.post<Project>('/projects/', data)
}

/**
 * 更新项目
 */
export const updateProject = (id: number, data: Partial<Project>) => {
    return request.put<Project>(`/projects/${id}`, data)
}

/**
 * 删除项目
 */
export const deleteProject = (id: number) => {
    return request.delete(`/projects/${id}`)
}
