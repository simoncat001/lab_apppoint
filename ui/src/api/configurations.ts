import request from '@/utils/request'
import type { Configuration, ConfigurationOption, ApiResponse } from '@/types'

// ==================== 配置管理 ====================

/**
 * 获取配置列表
 */
export const getConfigurations = (params?: {
    tool_id?: number
    enabled?: boolean
    exclude_from_agenda?: boolean
    name?: string
    skip?: number
    limit?: number
}) => {
    return request.get<ApiResponse<Configuration[]>>('/configurations/', { params })
}

/**
 * 创建配置
 */
export const createConfiguration = (data: Partial<Configuration>) => {
    return request.post<ApiResponse<Configuration>>('/configurations/', data)
}

/**
 * 获取配置详情
 */
export const getConfiguration = (configurationId: number) => {
    return request.get<ApiResponse<Configuration>>(`/configurations/${configurationId}`)
}

/**
 * 更新配置
 */
export const updateConfiguration = (configurationId: number, data: Partial<Configuration>) => {
    return request.put<ApiResponse<Configuration>>(`/configurations/${configurationId}`, data)
}

/**
 * 删除配置
 */
export const deleteConfiguration = (configurationId: number) => {
    return request.delete(`/configurations/${configurationId}`)
}

/**
 * 修改配置项
 */
export const changeConfigurationSetting = (
    configurationId: number,
    data: {
        slot: number
        choice: number
    }
) => {
    return request.post<ApiResponse<Configuration>>(
        `/configurations/${configurationId}/change-setting`,
        data
    )
}

/**
 * 获取工具的配置列表
 */
export const getToolConfigurations = (toolId: number) => {
    return request.get<ApiResponse<Configuration[]>>(`/configurations/tool/${toolId}/list`)
}

/**
 * 获取配置统计
 */
export const getConfigurationStats = (params?: { tool_id?: number }) => {
    return request.get<ApiResponse<{
        total_configurations: number
        enabled_configurations: number
        total_settings: number
    }>>('/configurations/stats', { params })
}

// ==================== 配置选项管理 ====================

/**
 * 获取配置选项列表
 */
export const getConfigurationOptions = (params?: {
    configuration_id?: number
    reservation_id?: number
    skip?: number
    limit?: number
}) => {
    return request.get<ApiResponse<ConfigurationOption[]>>('/configurations/configuration-options', { params })
}

/**
 * 创建配置选项
 */
export const createConfigurationOption = (data: Partial<ConfigurationOption>) => {
    return request.post<ApiResponse<ConfigurationOption>>('/configurations/configuration-options', data)
}

/**
 * 获取配置选项详情
 */
export const getConfigurationOption = (optionId: number) => {
    return request.get<ApiResponse<ConfigurationOption>>(`/configurations/configuration-options/${optionId}`)
}

/**
 * 更新配置选项
 */
export const updateConfigurationOption = (optionId: number, data: Partial<ConfigurationOption>) => {
    return request.put<ApiResponse<ConfigurationOption>>(`/configurations/configuration-options/${optionId}`, data)
}

/**
 * 删除配置选项
 */
export const deleteConfigurationOption = (optionId: number) => {
    return request.delete(`/configurations/configuration-options/${optionId}`)
}

// ==================== 配置历史管理 ====================

/**
 * 获取配置历史列表
 */
export const getConfigurationHistory = (params?: {
    configuration_id?: number
    user_id?: number
    start_date?: string
    end_date?: string
    skip?: number
    limit?: number
}) => {
    return request.get<ApiResponse<any[]>>('/configurations/configuration-history', { params })
}

/**
 * 获取配置历史详情
 */
export const getConfigurationHistoryDetail = (historyId: number) => {
    return request.get<ApiResponse<any>>(`/configurations/configuration-history/${historyId}`)
}

/**
 * 创建配置历史记录
 */
export const createConfigurationHistory = (data: any) => {
    return request.post<ApiResponse<any>>('/configurations/configuration-history', data)
}
