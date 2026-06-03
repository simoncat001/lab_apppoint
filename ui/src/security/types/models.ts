export interface User {
  id: number;
  username: string;
  name?: string;
  email?: string;
  phone?: string;
  status?: number;
  createdTime?: string;
  updatedTime?: string;
}

export interface Department {
  id: number;
  name: string;
  description?: string;
  createdTime?: string;
  updatedTime?: string;
}

export interface DepartmentDetail extends Department {
  memberCount?: number;
  projectCount?: number;
}

export interface Project {
  id: number;
  name: string;
  description?: string;
  departmentId: number;
  leaderId?: number;
  status?: number;
  externalVisible?: boolean;
  externalDisplayName?: string;
  createdTime?: string;
  updatedTime?: string;
}

export interface ProjectDetail extends Project {
  memberCount?: number;
  groupCount?: number;
}

export interface Group {
  id: number;
  name: string;
  description?: string;
  projectId: number;
  adminId?: number;
  createdTime?: string;
}

export interface GroupDetail extends Group {
  memberCount?: number;
}

export interface ApplicationRequest {
  id: number;
  userId: number;
  applicantName?: string;
  targetType: number;
  targetId: number;
  targetName?: string;
  status: number;
  reason?: string;
  approverId?: number;
  approveResult?: number;
  createdTime?: string;
}

export interface LoginPayload {
  username: string;
  password: string;
}

export interface RegisterPayload {
  username: string;
  password: string;
  name?: string;
  email?: string;
  phone?: string;
}

export interface LoginResponse {
  token: string;
  userInfo: User;
}

export interface PageResult<T> {
  records: T[];
  total: number;
  size: number;
  current: number;
  pages: number;
}
