import dayjs from 'dayjs'
import { TaskUrgency } from '@/types'

/**
 * 格式化日期时间
 */
export function formatDateTime(
    date: string | Date,
    format: string = 'YYYY-MM-DD HH:mm:ss'
): string {
    return dayjs(date).format(format)
}

/**
 * 格式化日期
 */
export function formatDate(date: string | Date): string {
    return dayjs(date).format('YYYY-MM-DD')
}

/**
 * 格式化时间
 */
export function formatTime(date: string | Date): string {
    return dayjs(date).format('HH:mm:ss')
}

/**
 * 计算时长（分钟）
 */
export function calcDuration(start: string | Date, end: string | Date): number {
    return dayjs(end).diff(dayjs(start), 'minute')
}

/**
 * 格式化时长显示
 */
export function formatDuration(minutes: number): string {
    if (minutes < 60) {
        return `${minutes} 分钟`
    }
    const hours = Math.floor(minutes / 60)
    const mins = minutes % 60
    return mins > 0 ? `${hours} 小时 ${mins} 分钟` : `${hours} 小时`
}

/**
 * 获取任务紧急程度的中文标签
 */
function normalizeTaskUrgency(
    urgency: TaskUrgency | number | string
): TaskUrgency | number | string {
    if (typeof urgency === 'number') {
        if (urgency <= -1) return TaskUrgency.LOW
        if (urgency === 0) return TaskUrgency.NORMAL
        if (urgency === 1) return TaskUrgency.HIGH
        return TaskUrgency.CRITICAL
    }
    return urgency
}

export function getTaskUrgencyLabel(urgency: TaskUrgency | number | string): string {
    const normalized = normalizeTaskUrgency(urgency)
    const labels: Record<string, string> = {
        [TaskUrgency.LOW]: '低',
        [TaskUrgency.NORMAL]: '正常',
        [TaskUrgency.HIGH]: '高',
        [TaskUrgency.CRITICAL]: '紧急',
    }
    return labels[String(normalized)] || '未知'
}

/**
 * 获取任务紧急程度的颜色类型
 */
export function getTaskUrgencyType(
    urgency: TaskUrgency | number | string
): 'success' | 'info' | 'warning' | 'danger' {
    const normalized = normalizeTaskUrgency(urgency)
    const types: Record<string, 'success' | 'info' | 'warning' | 'danger'> = {
        [TaskUrgency.LOW]: 'info',
        [TaskUrgency.NORMAL]: 'success',
        [TaskUrgency.HIGH]: 'warning',
        [TaskUrgency.CRITICAL]: 'danger',
    }
    return types[String(normalized)] || 'info'
}

/**
 * 下载文件
 */
export function downloadFile(data: Blob, filename: string) {
    const url = window.URL.createObjectURL(data)
    const link = document.createElement('a')
    link.href = url
    link.download = filename
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
}

/**
 * 防抖函数
 */
export function debounce<T extends (...args: any[]) => any>(
    func: T,
    wait: number
): (...args: Parameters<T>) => void {
    let timeout: ReturnType<typeof setTimeout> | null = null
    return function (this: any, ...args: Parameters<T>) {
        if (timeout) clearTimeout(timeout)
        timeout = setTimeout(() => func.apply(this, args), wait)
    }
}

/**
 * 节流函数
 */
export function throttle<T extends (...args: any[]) => any>(
    func: T,
    wait: number
): (...args: Parameters<T>) => void {
    let timeout: ReturnType<typeof setTimeout> | null = null
    return function (this: any, ...args: Parameters<T>) {
        if (!timeout) {
            timeout = setTimeout(() => {
                timeout = null
                func.apply(this, args)
            }, wait)
        }
    }
}

/**
 * 深拷贝
 */
export function deepClone<T>(obj: T): T {
    return JSON.parse(JSON.stringify(obj))
}

/**
 * 生成随机ID
 */
export function generateId(): string {
    return Math.random().toString(36).substring(2, 15)
}
