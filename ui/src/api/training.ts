import request from '@/utils/request'
import type {
  TrainingCategory,
  TrainingChapter,
  TrainingContent,
  TrainingCourse,
  TrainingOverview,
  TrainingRecord,
} from '@/types'

export function getTrainingOverview(params?: { include_unpublished?: boolean }) {
  return request.get<TrainingOverview>('/training/overview', { params })
}

export function getTrainingCategories() {
  return request.get<TrainingCategory[]>('/training/categories')
}

export function createTrainingCategory(data: Partial<TrainingCategory>) {
  return request.post<TrainingCategory>('/training/categories', data)
}

export function updateTrainingCategory(id: number, data: Partial<TrainingCategory>) {
  return request.put<TrainingCategory>(`/training/categories/${id}`, data)
}

export function deleteTrainingCategory(id: number) {
  return request.delete(`/training/categories/${id}`)
}

export function getTrainingCourses(params?: { include_unpublished?: boolean }) {
  return request.get<TrainingCourse[]>('/training/courses', { params })
}

export function createTrainingCourse(data: Partial<TrainingCourse>) {
  return request.post<TrainingCourse>('/training/courses', data)
}

export function updateTrainingCourse(id: number, data: Partial<TrainingCourse>) {
  return request.put<TrainingCourse>(`/training/courses/${id}`, data)
}

export function deleteTrainingCourse(id: number) {
  return request.delete(`/training/courses/${id}`)
}

export function getTrainingChapters(params?: {
  course_id?: number
  include_unpublished?: boolean
}) {
  return request.get<TrainingChapter[]>('/training/chapters', { params })
}

export function createTrainingChapter(data: Partial<TrainingChapter>) {
  return request.post<TrainingChapter>('/training/chapters', data)
}

export function updateTrainingChapter(id: number, data: Partial<TrainingChapter>) {
  return request.put<TrainingChapter>(`/training/chapters/${id}`, data)
}

export function deleteTrainingChapter(id: number) {
  return request.delete(`/training/chapters/${id}`)
}

export function getTrainingContents(params?: { include_unpublished?: boolean }) {
  return request.get<TrainingContent[]>('/training/contents', { params })
}

export function getTrainingContent(id: number) {
  return request.get<TrainingContent>(`/training/contents/${id}`)
}

export function createTrainingContent(data: Partial<TrainingContent>) {
  return request.post<TrainingContent>('/training/contents', data)
}

export function updateTrainingContent(id: number, data: Partial<TrainingContent>) {
  return request.put<TrainingContent>(`/training/contents/${id}`, data)
}

export function uploadTrainingContentFile(id: number, file: File) {
  const formData = new FormData()
  formData.append('file', file)
  return request.post<TrainingContent>(`/training/contents/${id}/file`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

export function deleteTrainingContent(id: number) {
  return request.delete(`/training/contents/${id}`)
}

export function getTrainingRecords(params?: { user_id?: number }) {
  return request.get<TrainingRecord[]>('/training/records', { params })
}

export function markTrainingRecord(data: { content_id: number }) {
  return request.post<TrainingRecord>('/training/records', data)
}
