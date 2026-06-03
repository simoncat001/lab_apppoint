import request from '@/utils/request'
import type { ProjectReportSummary, ReservationReport, ToolReport, UserReport } from '@/types'

export function getUserReport(params?: { start_date?: string; end_date?: string }) {
  return request.get<UserReport>('/reports/users', { params })
}

export function getReservationReport(params?: { start_date?: string; end_date?: string }) {
  return request.get<ReservationReport>('/reports/reservations', { params })
}

export function getToolReport(params?: { start_date?: string; end_date?: string }) {
  return request.get<ToolReport>('/reports/tools', { params })
}

export function getProjectReport(params?: { start_date?: string; end_date?: string }) {
  return request.get<ProjectReportSummary>('/reports/projects', { params })
}
