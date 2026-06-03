import request from '@/utils/request'

export interface DashboardStats {
  total_tools: number
  active_users: number
  report_users: number
  total_reservations: number
  total_hours: number
  active_tasks: number
  distinct_tools: number
  distinct_projects: number
  ongoing_reservations: number
  upcoming_reservations: number
  completed_reservations: number
  cancelled_reservations: number
  missed_reservations: number
}

export interface DashboardStatusBreakdown {
  key: string
  label: string
  count: number
}

export interface DashboardTrendPoint {
  date: string
  total: number
  ongoing: number
  completed: number
  upcoming: number
  cancelled: number
  missed: number
}

export interface DashboardRankingItem {
  name: string
  reservation_count: number
  total_hours: number
}

export interface DashboardUserReport {
  user_id: number
  username: string
  full_name: string
  is_active: boolean
  is_staff: boolean
  is_verified: boolean
  total_reservations: number
  ongoing_reservations: number
  completed_reservations: number
  upcoming_reservations: number
  cancelled_reservations: number
  missed_reservations: number
  total_hours: number
  distinct_tools: number
  distinct_projects: number
  favorite_tool_name?: string | null
  latest_reservation_at?: string | null
  next_reservation_at?: string | null
}

export interface DashboardRecentReservation {
  user_name?: string | null
  tool_name?: string | null
  project_name?: string | null
  start: string
  end: string
  status: string
}

export interface DashboardPendingTask {
  creator_name?: string | null
  tool_name?: string | null
  problem_description?: string | null
  urgency: number
  creation_time: string
}

export interface DashboardResponse {
  scope: 'global' | 'personal' | string
  period_start: string
  period_end: string
  stats: DashboardStats
  status_breakdown: DashboardStatusBreakdown[]
  trend: DashboardTrendPoint[]
  tool_rankings: DashboardRankingItem[]
  project_rankings: DashboardRankingItem[]
  user_reports: DashboardUserReport[]
  current_user_report: DashboardUserReport
  recent_reservations: DashboardRecentReservation[]
  pending_tasks: DashboardPendingTask[]
}

export const getDashboard = (params?: {
  days?: number
  start_date?: string
  end_date?: string
}) => {
  return request.get<DashboardResponse>('/dashboard/', { params })
}
