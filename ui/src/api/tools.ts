import request from '@/utils/request'
import type {
    Tool,
    ToolImage,
    PaginationParams,
    ToolEnableRequest,
    ToolDisableRequest,
    UsageEvent,
    ToolCategory,
    ToolTag,
    ToolProjectSuggestRequest,
    ToolProjectSuggestResponse,
    ToolUserAccess,
    ToolAdmin,
} from '@/types'

export interface ToolQuery extends PaginationParams {
    name?: string
    category_id?: number
    tag_ids?: string
    visible_only?: boolean
    operational_only?: boolean
}

// 获取工具列表
export function getTools(params?: ToolQuery): Promise<Tool[]> {
    return request({
        url: '/tools/',
        method: 'get',
        params,
    })
}

// ==================== 分类与标签 ====================
export function getToolCategories(): Promise<ToolCategory[]> {
    return request({
        url: '/tools/categories',
        method: 'get',
    })
}

export function createToolCategory(data: Partial<ToolCategory>): Promise<ToolCategory> {
    return request({
        url: '/tools/categories',
        method: 'post',
        data,
    })
}

export function updateToolCategory(id: number, data: Partial<ToolCategory>): Promise<ToolCategory> {
    return request({
        url: `/tools/categories/${id}`,
        method: 'put',
        data,
    })
}

export function deleteToolCategory(id: number): Promise<void> {
    return request({
        url: `/tools/categories/${id}`,
        method: 'delete',
    })
}

export function getToolTags(): Promise<ToolTag[]> {
    return request({
        url: '/tools/tags',
        method: 'get',
    })
}

export function createToolTag(data: Partial<ToolTag>): Promise<ToolTag> {
    return request({
        url: '/tools/tags',
        method: 'post',
        data,
    })
}

export function updateToolTag(id: number, data: Partial<ToolTag>): Promise<ToolTag> {
    return request({
        url: `/tools/tags/${id}`,
        method: 'put',
        data,
    })
}

export function deleteToolTag(id: number): Promise<void> {
    return request({
        url: `/tools/tags/${id}`,
        method: 'delete',
    })
}

// 获取工具详情
export function getTool(id: number): Promise<Tool> {
    return request({
        url: `/tools/${id}`,
        method: 'get',
    })
}

// 创建工具
export function createTool(data: Partial<Tool>): Promise<Tool> {
    return request({
        url: '/tools/',
        method: 'post',
        data,
    })
}

// 更新工具
export function updateTool(id: number, data: Partial<Tool>): Promise<Tool> {
    return request({
        url: `/tools/${id}`,
        method: 'put',
        data,
    })
}

// 智能建议仪器所属项目
export function suggestToolProject(data: ToolProjectSuggestRequest): Promise<ToolProjectSuggestResponse> {
    return request({
        url: '/tools/project-suggestion',
        method: 'post',
        data,
    })
}

// 删除工具
export function deleteTool(id: number): Promise<void> {
    return request({
        url: `/tools/${id}`,
        method: 'delete',
    })
}

// 获取工具状态
export function getToolStatus(id: number): Promise<boolean> {
    return request({
        url: `/tools/${id}/status`,
        method: 'get',
    })
}

// ==================== 费率管理 ====================

export interface ToolRate {
    id?: number
    tool_id: number
    start_time: string // HH:MM:SS
    end_time: string   // HH:MM:SS
    price: number
}

// 获取工具费率
export function getToolRates(toolId: number): Promise<ToolRate[]> {
    return request({
        url: `/tools/${toolId}/rates`,
        method: 'get',
    })
}

// 创建工具费率
export function createToolRate(toolId: number, data: ToolRate): Promise<ToolRate> {
    return request({
        url: `/tools/${toolId}/rates`,
        method: 'post',
        data,
    })
}

// 删除工具费率
export function deleteToolRate(toolId: number, rateId: number): Promise<void> {
    return request({
        url: `/tools/${toolId}/rates/${rateId}`,
        method: 'delete',
    })
}

// ==================== 图片管理 ====================

// 上传仪器图片
export function uploadToolImage(toolId: number, file: File): Promise<Tool> {
    const formData = new FormData()
    formData.append('file', file)
    return request({
        url: `/tools/${toolId}/image`,
        method: 'post',
        data: formData,
        headers: { 'Content-Type': 'multipart/form-data' },
        skipGlobalErrorHandler: true,
    } as any)
}

// 删除仪器图片
export function deleteToolImage(toolId: number): Promise<Tool> {
    return request({
        url: `/tools/${toolId}/image`,
        method: 'delete',
    })
}

export function deleteToolImageById(toolId: number, imageId: number): Promise<Tool> {
    return request({
        url: `/tools/${toolId}/image`,
        method: 'delete',
        params: { image_id: imageId },
    })
}

// 获取仪器图片 URL
export function getToolImageUrl(image: string | undefined): string | null {
    if (!image) return null
    // 新版：DB 存的是 "tools/{id}/{file}" 或完整 "/media/..." 路径
    if (image.startsWith('/media/')) return image
    if (image.includes('/')) return `/media/${image}`
    // 旧版兼容：只有文件名，回退到历史目录
    return `/media/tool_images/${image}`
}

export function getToolImages(tool?: Partial<Tool> | null): ToolImage[] {
    const images = Array.isArray(tool?.images)
        ? tool.images.filter((item): item is ToolImage => !!item?.path)
        : []
    if (images.length) return images
    if (tool?.image) {
        return [
            {
                id: 0,
                tool_id: tool.id || 0,
                path: tool.image,
                sort_order: 0,
            },
        ]
    }
    return []
}

export function getToolCoverImageUrl(tool?: Partial<Tool> | null): string | null {
    const coverPath = tool?.image || getToolImages(tool)[0]?.path
    return getToolImageUrl(coverPath)
}

export function getToolImagePreviewUrls(tool?: Partial<Tool> | null): string[] {
    return getToolImages(tool)
        .map((item) => getToolImageUrl(item.path))
        .filter((item): item is string => !!item)
}

// 启用工具
export function enableTool(id: number, data: ToolEnableRequest): Promise<UsageEvent> {
    return request({
        url: `/tools/${id}/enable`,
        method: 'post',
        data,
    })
}

// 禁用工具
export function disableTool(id: number, data: ToolDisableRequest): Promise<UsageEvent> {
    return request({
        url: `/tools/${id}/disable`,
        method: 'post',
        data,
    })
}

// ==================== 设备级用户权限管理 ====================

// 查询仪器已授权用户
export function getToolAccess(toolId: number): Promise<ToolUserAccess[]> {
    return request({
        url: `/tools/${toolId}/access`,
        method: 'get',
    })
}

// 授权用户使用仪器
export function grantToolAccess(toolId: number, userId: number): Promise<ToolUserAccess> {
    return request({
        url: `/tools/${toolId}/access`,
        method: 'post',
        data: { user_id: userId },
    })
}

// 撤销用户仪器使用权限
export function revokeToolAccess(toolId: number, userId: number): Promise<void> {
    return request({
        url: `/tools/${toolId}/access/${userId}`,
        method: 'delete',
    })
}

// 查询仪器管理员
export function getToolAdmins(toolId: number): Promise<ToolAdmin[]> {
    return request({
        url: `/tools/${toolId}/admins`,
        method: 'get',
    })
}

// 设置仪器管理员
export function updateToolAdmins(toolId: number, userIds: number[]): Promise<ToolAdmin[]> {
    return request({
        url: `/tools/${toolId}/admins`,
        method: 'put',
        data: { user_ids: userIds },
    })
}
