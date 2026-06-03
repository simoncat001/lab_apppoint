import { api } from './http';
import type {
  ApplicationRequest,
  Department,
  DepartmentDetail,
  Group,
  GroupDetail,
  LoginPayload,
  LoginResponse,
  RegisterPayload,
  Project,
  ProjectDetail,
  User
} from '@/security/types/models';

export const login = (payload: LoginPayload) => api.post<LoginResponse>('/api/login', payload);
export const register = (payload: RegisterPayload) => api.post('/api/register', payload);
export const logout = () => api.post('/api/logout');

export const fetchDepartments = () => api.post<Department[]>('/api/departments/list', {});
export const fetchDepartmentDetail = (id: number) => api.get<DepartmentDetail>(`/api/departments/${id}`);
export const createDepartment = (payload: { name: string; description?: string }) =>
  api.post('/api/departments', payload);
export const updateDepartment = (id: number, payload: { name: string; description?: string }) =>
  api.put(`/api/departments/${id}`, payload);
export const deleteDepartment = (id: number) => api.delete(`/api/departments/${id}`);
export const applyDepartment = (id: number, payload: { reason?: string }) =>
  api.post(`/api/departments/${id}/apply`, payload);
export const addDepartmentMembers = (id: number, userIds: number[]) =>
  api.post(`/api/departments/${id}/members`, userIds);
export const setDepartmentAdmin = (id: number, userId: number) =>
  api.post(`/api/departments/${id}/admin`, null, { params: { userId } });
export const removeDepartmentAdmin = (id: number, userId: number) =>
  api.post(`/api/departments/${id}/admin/cancel`, null, { params: { userId } });

export const fetchProjects = (departmentId?: number) =>
  api.post<Project[]>('/api/projects/list', departmentId ? { departmentId } : {});
export const fetchProjectDetail = (id: number) => api.get<ProjectDetail>(`/api/projects/${id}`);
export const createProject = (payload: {
  name: string;
  description?: string;
  departmentId: number;
  externalVisible?: boolean;
  externalDisplayName?: string;
}) =>
  api.post('/api/projects', payload);
export const updateProject = (id: number, payload: {
  name: string;
  description?: string;
  departmentId?: number;
  externalVisible?: boolean;
  externalDisplayName?: string;
}) =>
  api.put(`/api/projects/${id}`, payload);
export const deleteProject = (id: number) => api.delete(`/api/projects/${id}`);
export const applyProject = (id: number, payload: { reason?: string }) =>
  api.post(`/api/projects/${id}/apply`, payload);
export const addProjectMembers = (id: number, userIds: number[]) =>
  api.post(`/api/projects/${id}/members`, userIds);
export const setProjectAdmin = (id: number, userId: number) =>
  api.post(`/api/projects/${id}/admin`, null, { params: { userId } });
export const removeProjectAdmin = (id: number, userId: number) =>
  api.post(`/api/projects/${id}/admin/cancel`, null, { params: { userId } });

export const fetchGroups = (projectId: number) =>
  api.post<Group[]>('/api/groups/list', { projectId });
export const fetchGroupDetail = (id: number) => api.get<GroupDetail>(`/api/groups/${id}`);
export const createGroup = (payload: { name: string; description?: string; projectId: number }) =>
  api.post('/api/groups', payload);
export const updateGroup = (id: number, payload: { name: string; description?: string; projectId?: number }) =>
  api.put(`/api/groups/${id}`, payload);
export const deleteGroup = (id: number) => api.delete(`/api/groups/${id}`);
export const applyGroup = (id: number, payload: { reason?: string }) =>
  api.post(`/api/groups/${id}/apply`, payload);
export const addGroupMembers = (id: number, userIds: number[]) =>
  api.post(`/api/groups/${id}/members`, userIds);
export const setGroupAdmin = (id: number, userId: number) =>
  api.post(`/api/groups/${id}/admin`, null, { params: { userId } });
export const removeGroupAdmin = (id: number, userId: number) =>
  api.post(`/api/groups/${id}/admin/cancel`, null, { params: { userId } });

export const fetchApplications = (params: { status?: number; targetType?: number; targetId?: number; auditOnly?: boolean } = {}) =>
  api.post<ApplicationRequest[]>('/api/applications/list', params);
export const createApplication = (payload: { targetType: number; targetId: number; reason?: string }) =>
  api.post('/api/applications', payload);
export const approveApplication = (id: number) => api.post(`/api/applications/${id}/approve`);
export const rejectApplication = (id: number, payload: { rejectReason?: string }) =>
  api.post(`/api/applications/${id}/reject`, payload);

export const fetchUsers = (params: { pageNum?: number; size?: number; username?: string } = {}) =>
  api.post<User[]>('/api/users/list', {
    keyword: params.username,
    pageParam: {
      current: params.pageNum,
      size: params.size
    }
  });
export const createUser = (payload: Partial<User> & { password?: string }) => api.post('/api/users', payload);
export const updateUser = (payload: Partial<User> & { id: number; password?: string }) => api.put('/api/users', payload);
export const deleteUser = (id: number) => api.delete(`/api/users/${id}`);
