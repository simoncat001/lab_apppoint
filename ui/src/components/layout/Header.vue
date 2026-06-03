<template>
  <div class="header">
    <div class="left">
      <el-icon class="menu-icon" @click="toggleSidebar">
        <Fold v-if="!appStore.sidebarCollapsed" />
        <Expand v-else />
      </el-icon>
    </div>

    <div class="center" v-if="authStore.isAuthenticated">
      <div class="project-title-wrap">
        <div class="project-title-label">当前项目</div>
        <div class="project-main-row">
          <span class="project-switch-spacer" aria-hidden="true">切换</span>
          <div class="project-title-text" :title="projectDisplayName">
            {{ projectDisplayName }}
          </div>
          <el-button
            text
            size="small"
            class="project-switch-link"
            @click="openProjectDialog"
          >
            切换
          </el-button>
        </div>
      </div>
    </div>

    <div class="right">
      <el-dropdown @command="handleCommand">
        <span class="user-info">
          <el-avatar :size="32">{{ userInitial }}</el-avatar>
          <el-tag
            v-if="authStore.user"
            :type="loginTypeTagType"
            effect="plain"
            size="small"
            class="login-type-tag"
          >
            {{ loginTypeLabel }}
          </el-tag>
          <span class="username">{{ userDisplayName }}</span>
          <el-icon><CaretBottom /></el-icon>
        </span>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item disabled>
              <el-tag
                v-if="authStore.user"
                :type="loginTypeTagType"
                effect="light"
                size="small"
              >
                {{ loginTypeLabel }}
              </el-tag>
            </el-dropdown-item>
            <el-dropdown-item command="profile">
              <el-icon><User /></el-icon>
              个人资料
            </el-dropdown-item>
            <el-dropdown-item divided command="logout">
              <el-icon><SwitchButton /></el-icon>
              退出登录
            </el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>
  </div>

  <el-dialog
    v-model="projectDialogVisible"
    title="切换当前项目"
    width="520px"
    destroy-on-close
  >
    <el-form label-width="70px">
      <el-form-item label="项目">
        <el-select
          v-model="dialogProjectId"
          placeholder="请选择项目"
          filterable
          clearable
          style="width: 100%"
          :loading="projectStore.loading"
        >
          <el-option
            v-for="p in projectStore.projects"
            :key="p.id"
            :label="getProjectDisplayName(p)"
            :value="p.id"
          />
        </el-select>
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="projectDialogVisible = false">取消</el-button>
      <el-button text @click="handleProjectDialogClear">清空项目</el-button>
      <el-button type="primary" @click="confirmProjectDialog">
        确认切换
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useAppStore } from '@/stores/app'
import { useAuthStore } from '@/stores/auth'
import { useProjectContextStore } from '@/stores/project-context'
import { getProjectDisplayName } from '@/utils/project'
import { getUserDisplayName, getUserInitial } from '@/utils/user'

const route = useRoute()
const router = useRouter()
const appStore = useAppStore()
const authStore = useAuthStore()
const projectStore = useProjectContextStore()
const selectedProjectId = ref<number | null>(null)
const projectDialogVisible = ref(false)
const dialogProjectId = ref<number | null>(null)

const userDisplayName = computed(() => getUserDisplayName(authStore.user, '未登录'))
const userInitial = computed(() => getUserInitial(authStore.user))

const loginTypeLabel = computed(() => {
  if (authStore.isInternalUser()) return '员工登录'
  if (authStore.isExternalUser()) return '外部用户登录'
  if (authStore.isSuperuser()) return '管理员登录'
  return '已登录'
})

const loginTypeTagType = computed(() => {
  if (authStore.isInternalUser()) return 'success'
  if (authStore.isExternalUser()) return 'warning'
  if (authStore.isSuperuser()) return 'danger'
  return 'info'
})

const projectDisplayName = computed(() => {
  return projectStore.currentProjectName || '未选择项目'
})

const toggleSidebar = () => {
  appStore.toggleSidebar()
}

const syncSelectedProject = () => {
  selectedProjectId.value = projectStore.currentProjectId
}

const ensureProjectsLoaded = async (force = false) => {
  if (!authStore.isAuthenticated) return
  try {
    await projectStore.loadProjects(force)
    syncSelectedProject()
  } catch (error) {
    console.error(error)
  }
}

const applyProjectChange = async (value: number | null) => {
  if (!value) {
    projectStore.clearCurrentProject()
    ElMessage.warning('已清空当前项目，请重新选择')
    if (route.name !== 'Profile' && route.name !== 'ProjectWorkspaceSelect') {
      router.push({ name: 'ProjectWorkspaceSelect', query: { redirect: route.fullPath } })
    }
    return
  }

  const project = projectStore.projects.find((item) => item.id === value)
  if (!project) {
    ElMessage.error('项目不存在或无权限访问')
    selectedProjectId.value = projectStore.currentProjectId
    return
  }

  projectStore.setCurrentProject(project)
  selectedProjectId.value = project.id
  ElMessage.success(`已切换到项目：${getProjectDisplayName(project)}`)

  if (route.name === 'ProjectWorkspaceSelect') {
    const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : '/dashboard'
    router.push(redirect)
    return
  }

  if (route.name === 'Dashboard') {
    window.location.reload()
    return
  }
  router.push({ name: 'Dashboard' })
}

const openProjectDialog = async () => {
  await ensureProjectsLoaded(true)
  dialogProjectId.value = projectStore.currentProjectId
  projectDialogVisible.value = true
}

const confirmProjectDialog = async () => {
  const beforeId = projectStore.currentProjectId
  if (dialogProjectId.value === beforeId) {
    projectDialogVisible.value = false
    return
  }
  await applyProjectChange(dialogProjectId.value)
  if (dialogProjectId.value === null || dialogProjectId.value !== beforeId) {
    projectDialogVisible.value = false
  }
}

const handleProjectDialogClear = async () => {
  dialogProjectId.value = null
  await applyProjectChange(null)
  projectDialogVisible.value = false
}

const handleCommand = async (command: string) => {
  if (command === 'profile') {
    router.push('/profile')
  } else if (command === 'logout') {
    try {
      await ElMessageBox.confirm('确定要退出登录吗？', '提示', {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning',
      })
      await authStore.logout()
      projectStore.clearCurrentProject()
      router.push('/login')
      ElMessage.success('退出成功')
    } catch (error) {
      // 用户取消
    }
  }
}

onMounted(async () => {
  syncSelectedProject()
  await ensureProjectsLoaded()
})

watch(
  () => projectStore.currentProjectId,
  () => {
    syncSelectedProject()
  }
)
</script>

<style scoped>
.header {
  width: 100%;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.menu-icon {
  font-size: 20px;
  cursor: pointer;
  transition: color 0.3s;
}

.menu-icon:hover {
  color: #409eff;
}

.center {
  flex: 1;
  display: flex;
  justify-content: center;
  min-width: 0;
}

.project-title-wrap {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-width: 240px;
  max-width: 520px;
  width: min(520px, 100%);
  line-height: 1.2;
}

.project-title-label {
  color: #606266;
  font-size: 12px;
  white-space: nowrap;
}

.project-main-row {
  display: flex;
  align-items: flex-end;
  justify-content: center;
  gap: 8px;
  width: 100%;
  min-height: 24px;
}

.project-switch-spacer {
  visibility: hidden;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  font-size: 12px;
  line-height: 1;
  flex-shrink: 0;
}

.project-switch-link {
  padding: 0;
  height: auto;
  min-height: auto;
  line-height: 1;
  font-size: 12px;
  font-weight: 400;
  color: #409eff;
  flex-shrink: 0;
  width: 24px;
  align-self: flex-end;
}

.project-switch-link:hover,
.project-switch-link:focus-visible {
  color: #66b1ff;
}

.project-title-text {
  max-width: min(360px, 100%);
  font-size: 16px;
  font-weight: 600;
  color: #303133;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  text-align: center;
}

.right {
  display: flex;
  align-items: center;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}

.username {
  margin-left: 8px;
  font-size: 14px;
}

.login-type-tag {
  margin-left: 8px;
}

@media (max-width: 900px) {
  .project-title-wrap {
    min-width: 140px;
    max-width: 260px;
  }

  .project-title-text {
    font-size: 14px;
  }

  .project-main-row {
    min-height: 22px;
  }

  .project-title-text {
    max-width: min(180px, 100%);
  }

  .username {
    display: none;
  }
}
</style>
