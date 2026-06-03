import request from '@/utils/request'
import type {
    CollaborationRecord,
    CollaborationRecordPayload,
    CollaborationRecordQuery,
} from '@/types'

export const getCollaborationRecords = (params?: CollaborationRecordQuery) => {
    return request.get<CollaborationRecord[]>('/collaboration-records/', { params })
}

export const getCollaborationRecord = (id: number) => {
    return request.get<CollaborationRecord>(`/collaboration-records/${id}`)
}

export const createCollaborationRecord = (data: CollaborationRecordPayload) => {
    return request.post<CollaborationRecord>('/collaboration-records/', data)
}

export const updateCollaborationRecord = (id: number, data: Partial<CollaborationRecordPayload> & { pinned?: boolean }) => {
    return request.put<CollaborationRecord>(`/collaboration-records/${id}`, data)
}

export const deleteCollaborationRecord = (id: number) => {
    return request.delete<boolean>(`/collaboration-records/${id}`)
}

export const publishCollaborationRecord = (id: number) => {
    return request.post<CollaborationRecord>(`/collaboration-records/${id}/publish`)
}

export const archiveCollaborationRecord = (id: number) => {
    return request.post<CollaborationRecord>(`/collaboration-records/${id}/archive`)
}
