import request from '@/utils/request'
import type { MaintenanceRecord } from '@/types'

export function getMaintenanceRecords(params?: { tool_id?: number }) {
  return request.get<MaintenanceRecord[]>('/maintenance/', { params })
}

export function createMaintenanceRecord(data: Partial<MaintenanceRecord>) {
  return request.post<MaintenanceRecord>('/maintenance/', data)
}

export function updateMaintenanceRecord(id: number, data: Partial<MaintenanceRecord>) {
  return request.put<MaintenanceRecord>(`/maintenance/${id}`, data)
}

export function deleteMaintenanceRecord(id: number) {
  return request.delete(`/maintenance/${id}`)
}
