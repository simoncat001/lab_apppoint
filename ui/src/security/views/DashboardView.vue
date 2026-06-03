<template>
  <div class="grid cols-3 stagger">
    <div class="card">
      <span class="badge">部门</span>
      <h2 style="margin-top: 10px;">{{ departments.length }}</h2>
      <p>当前可见部门数量</p>
    </div>
    <div class="card">
      <span class="badge cool">项目</span>
      <h2 style="margin-top: 10px;">{{ projects.length }}</h2>
      <p>当前可见项目数量</p>
    </div>
    <div class="card">
      <span class="badge ink">待审批</span>
      <h2 style="margin-top: 10px;">{{ pendingCount }}</h2>
      <p>待处理申请数量</p>
    </div>
  </div>

  <div class="grid cols-2">
    <div class="card">
      <h3>账号速览</h3>
      <p style="margin-top: 6px;">当前登录账号的基础信息。</p>
      <div style="margin-top: 16px; display: grid; gap: 8px;">
        <div class="pill">用户名：{{ auth.user?.username || '-' }}</div>
        <div class="pill">姓名：{{ auth.user?.name || '-' }}</div>
        <div class="pill">邮箱：{{ auth.user?.email || '-' }}</div>
      </div>
    </div>
    <div class="card">
      <h3>快速入口</h3>
      <p style="margin-top: 6px;">跳转到核心管理模块。</p>
      <div style="margin-top: 16px; display: flex; flex-wrap: wrap; gap: 10px;">
        <RouterLink class="button" to="/departments">管理部门</RouterLink>
        <RouterLink class="button secondary" to="/projects">管理项目</RouterLink>
        <RouterLink class="button ghost" to="/applications">审批申请</RouterLink>
      </div>
    </div>
  </div>

  <div class="card">
    <h3>操作提示</h3>
    <p style="margin-top: 10px;">
      部门与项目的创建权限由后端超级管理员策略控制。若提示无权限，请联系管理员授权。
    </p>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { fetchApplications, fetchDepartments, fetchProjects } from '@/security/api/endpoints';
import type { ApplicationRequest, Department, Project } from '@/security/types/models';
import { useStaffAuthStore } from '@/security/stores/auth';
import { useNotifyStore } from '@/security/stores/notify';

const auth = useStaffAuthStore();
const notify = useNotifyStore();

const departments = ref<Department[]>([]);
const projects = ref<Project[]>([]);
const pendingCount = ref(0);

const load = async () => {
  try {
    const [deptData, projData, appData] = await Promise.all([
      fetchDepartments(),
      fetchProjects(),
      fetchApplications({ status: 0, auditOnly: true })
    ]);
    departments.value = (deptData as Department[]) || [];
    projects.value = (projData as Project[]) || [];
    pendingCount.value = (appData as ApplicationRequest[])?.length || 0;
  } catch (error: any) {
    notify.push(error?.message || '概览加载失败', 'error');
  }
};

onMounted(load);
</script>
