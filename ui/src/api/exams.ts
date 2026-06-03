import request from '@/utils/request'
import type { ExamAttemptSummary, ExamPaper, ExamStartResponse } from '@/types'

export function getExamPapers(params?: { published_only?: boolean }) {
  return request.get<ExamPaper[]>('/exams/papers', { params })
}

export function startExamPaper(paperId: number) {
  return request.post<ExamStartResponse>(`/exams/papers/${paperId}/start`)
}

export function submitExamPaper(
  attemptId: number,
  data: { answers: Array<{ question_id: number; answer: any }> }
) {
  return request.post<ExamAttemptSummary>(`/exams/attempts/${attemptId}/submit`, data)
}

export function getExamAttempts(params?: {
  paper_id?: number
  user_id?: number
  pending_grading?: boolean
}) {
  return request.get<ExamAttemptSummary[]>('/exams/attempts', { params })
}
