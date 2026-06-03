<template>
  <aside class="sidebar">
    <div class="sidebar-header">
      <span class="icon">🔐</span>
      <span class="title">安全组织管理</span>
    </div>
    <nav class="sidebar-nav">
      <div v-for="group in navGroups" :key="group.label" class="nav-group">
        <div class="nav-group-label">{{ group.label }}</div>
        <RouterLink
          v-for="item in group.items"
          :key="item.to"
          :to="item.to"
          class="nav-item"
          active-class="active"
        >
          <span class="nav-text">{{ item.label }}</span>
        </RouterLink>
      </div>
    </nav>
    <div class="sidebar-footer">
      <div>当前 API：{{ baseUrl }}</div>
    </div>
  </aside>
</template>

<script setup lang="ts">
const navGroups = [
  {
    label: '概览',
    items: [{ label: '控制台', to: '/security/dashboard' }]
  },
  {
    label: '组织管理',
    items: [
      { label: '部门', to: '/security/departments' },
      { label: '项目', to: '/security/projects' },
      { label: '小组', to: '/security/groups' }
    ]
  },
  {
    label: '业务运营',
    items: [
      { label: '申请审批', to: '/security/applications' },
      { label: '快捷申请', to: '/security/applications/quick' },
      { label: '用户管理', to: '/security/users' }
    ]
  }
];

const baseUrl = import.meta.env.VITE_API_BASE || 'http://localhost:8299';
</script>
