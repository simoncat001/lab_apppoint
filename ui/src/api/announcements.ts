import request from '@/utils/request'
import type { Announcement } from '@/types'

export function getAnnouncements(params?: { skip?: number; limit?: number; include_unpublished?: boolean }) {
  return request.get<Announcement[]>('/announcements/', { params })
}

export function getAnnouncement(id: number) {
  return request.get<Announcement>(`/announcements/${id}`)
}

export function createAnnouncement(data: Partial<Announcement>) {
  return request.post<Announcement>('/announcements/', data)
}

export function updateAnnouncement(id: number, data: Partial<Announcement>) {
  return request.put<Announcement>(`/announcements/${id}`, data)
}

export function deleteAnnouncement(id: number) {
  return request.delete(`/announcements/${id}`)
}
