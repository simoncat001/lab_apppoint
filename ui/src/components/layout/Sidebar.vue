<template>
  <div class="sidebar">
    <div class="logo">
      <span class="logo-mark" v-if="!appStore.sidebarCollapsed" aria-label="NEMO logo">
        <svg viewBox="0 0 64 64" width="32" height="32" role="img" focusable="false">
          <defs>
            <linearGradient id="nemoGrad" x1="0" y1="0" x2="1" y2="1">
              <stop offset="0" stop-color="#46a0ff" />
              <stop offset="1" stop-color="#7c4dff" />
            </linearGradient>
          </defs>
          <rect x="6" y="6" width="52" height="52" rx="14" fill="url(#nemoGrad)" />
          <text x="32" y="41" font-size="28" font-weight="bold" fill="#ffffff" text-anchor="middle">预</text>
        </svg>
      </span>
      <span v-if="!appStore.sidebarCollapsed">预约系统</span>
    </div>
    
    <el-menu
      :default-active="activeMenu"
      :collapse="appStore.sidebarCollapsed"
      :unique-opened="true"
      background-color="#304156"
      text-color="#bfcbd9"
      active-text-color="#409EFF"
      router
    >
      <!-- 外部用户：公告置顶为默认界面 -->
      <el-menu-item index="/announcements" v-if="isExternalUser">
        <el-icon><Bell /></el-icon>
        <template #title>公告</template>
      </el-menu-item>

      <el-menu-item index="/dashboard" v-if="!isExternalUser">
        <el-icon><HomeFilled /></el-icon>
        <template #title>仪表盘</template>
      </el-menu-item>

      <el-menu-item index="/tools" v-if="showToolsMenu">
        <el-icon><Tools /></el-icon>
        <template #title>{{ authStore.isStaff() ? '仪器管理' : '仪器列表' }}</template>
      </el-menu-item>

      <el-menu-item index="/tool-control" v-if="authStore.isStaff()">
        <el-icon><Monitor /></el-icon>
        <template #title>仪器控制</template>
      </el-menu-item>

      <el-sub-menu index="reservations" v-if="authStore.canAccessReservations()">
        <template #title>
          <el-icon><Calendar /></el-icon>
          <span>预约系统</span>
        </template>
        <el-menu-item index="/reservations">预约列表</el-menu-item>
        <el-menu-item index="/calendar">预约日历</el-menu-item>
      </el-sub-menu>

      <!-- 非管理员账单查看 -->
      <el-menu-item index="/billing" v-if="!authStore.isStaff() && authStore.canAccessReservations()">
        <el-icon><CreditCard /></el-icon>
        <template #title>我的账单</template>
      </el-menu-item>

      <el-menu-item index="/usage-events" v-if="!isExternalUser">
        <el-icon><Clock /></el-icon>
        <template #title>使用记录</template>
      </el-menu-item>

      <el-menu-item index="/collaboration-records">
        <el-icon><Document /></el-icon>
        <template #title>科研协作</template>
      </el-menu-item>

      <!-- 非外部用户：公告位于其它功能之间（外部用户的公告在最上方已渲染过） -->
      <el-menu-item index="/announcements" v-if="!isExternalUser">
        <el-icon><Bell /></el-icon>
        <template #title>公告</template>
      </el-menu-item>

      <el-menu-item index="/training">
        <el-icon><Reading /></el-icon>
        <template #title>培训与考试</template>
      </el-menu-item>

      <el-menu-item index="/project-access-request" v-if="isExternalUser">
        <el-icon><UserFilled /></el-icon>
        <template #title>项目预约权限申请</template>
      </el-menu-item>

      <el-menu-item index="/account-membership-request" v-if="isExternalUser">
        <el-icon><CreditCard /></el-icon>
        <template #title>所属账户申请</template>
      </el-menu-item>

      <el-menu-item index="/profile" v-if="!isExternalUser">
        <el-icon><UserFilled /></el-icon>
        <template #title>个人主页</template>
      </el-menu-item>

      <el-menu-item index="/project-access-approval" v-if="showProjectAccessApprovalMenu">
        <el-icon><Setting /></el-icon>
        <template #title>项目预约权限审批</template>
      </el-menu-item>

      <el-menu-item index="/account-membership-approval" v-if="showAccountMembershipApprovalMenu">
        <el-icon><CreditCard /></el-icon>
        <template #title>所属账户审批</template>
      </el-menu-item>

      <el-menu-item index="/tasks" v-if="authStore.isStaff()">
        <el-icon><List /></el-icon>
        <template #title>任务管理</template>
      </el-menu-item>

      <el-sub-menu index="admin" v-if="authStore.isStaff()">
        <template #title>
          <el-icon><Setting /></el-icon>
          <span>系统管理</span>
        </template>
        <el-menu-item index="/users">用户管理</el-menu-item>
        <el-menu-item index="/accounts">账户管理</el-menu-item>
        <el-menu-item index="/billing">账单管理</el-menu-item>
        <el-menu-item index="/staff-charges">员工收费</el-menu-item>
        <el-menu-item index="/project-access-request">项目开放配置</el-menu-item>
        <el-menu-item index="/configurations">配置管理</el-menu-item>
        <el-menu-item index="/maintenance">维保记录</el-menu-item>
        <el-menu-item index="/reports" v-if="authStore.isSuperuser()">数据报表</el-menu-item>
      </el-sub-menu>
    </el-menu>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useAppStore } from '@/stores/app'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const appStore = useAppStore()
const authStore = useAuthStore()
const isExternalUser = computed(() => authStore.isExternalUser())
const showToolsMenu = computed(() => authStore.isStaff() || authStore.isInternalUser() || authStore.isExternalUser())
const showProjectAccessApprovalMenu = computed(() => authStore.isStaff() || authStore.isInternalUser())
const showAccountMembershipApprovalMenu = computed(() => authStore.isStaff())

const activeMenu = computed(() => {
  if (route.path.startsWith('/tools/')) return '/tools'
  if (route.path.startsWith('/accounts/')) return '/accounts'
  if (route.path.startsWith('/billing/')) return '/billing'
  if (route.path.startsWith('/announcements/')) return '/announcements'
  if (route.path.startsWith('/collaboration-records/')) return '/collaboration-records'
  if (route.path.startsWith('/training/')) return '/training'
  return route.path
})
</script>

<style scoped>
.sidebar {
  height: 100vh;
  height: 100dvh;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background-color: #304156;
}

.logo {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 20px;
  font-weight: bold;
  background-color: #2b3a4a;
}

.logo-mark {
  display: inline-flex;
  align-items: center;
  margin-right: 10px;
}

.el-menu {
  border-right: none;
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
}
</style>
