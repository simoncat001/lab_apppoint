<template>
  <div class="project-access-page">
    <div class="page-shell">
      <el-card shadow="never" class="hero-card">
        <div class="hero">
          <div class="hero-main">
            <div class="hero-eyebrow">外部用户入口</div>
            <div class="hero-title">项目预约权限申请</div>
            <div class="hero-subtitle">
              选择目标项目并提交申请，审批通过后即可在该项目下进行仪器预约。仅展示权鉴系统已配置“对外展示”的项目。
            </div>
            <div class="hero-tags">
              <el-tag size="small" effect="plain" type="info">
                {{ authStore.isExternalUser() ? '当前身份：外部用户' : '当前身份：非外部用户' }}
              </el-tag>
              <el-tag
                size="small"
                effect="light"
                :type="pendingRequestCount > 0 ? 'warning' : 'success'"
              >
                {{ pendingRequestCount > 0 ? `待审批 ${pendingRequestCount} 条` : '可提交新申请' }}
              </el-tag>
            </div>
          </div>
          <div class="hero-actions">
            <el-button :icon="Refresh" @click="loadData" :loading="loading">刷新</el-button>
            <el-button text @click="goProfile">个人主页</el-button>
          </div>
        </div>

        <div class="hero-alerts">
          <el-alert
            v-if="!authStore.isExternalUser()"
            title="该页面主要面向外部用户申请项目预约权限。"
            type="info"
            show-icon
            :closable="false"
          />
          <el-alert
            title="如需先加入所属账户，请前往个人主页提交所属账户加入申请。项目预约权限申请由目标项目管理员审批。"
            type="info"
            show-icon
            :closable="false"
          />
        </div>
      </el-card>

      <div class="content-grid">
        <el-card shadow="never" class="panel-card form-panel">
          <template #header>
            <div class="panel-header">
              <div class="panel-title">提交申请</div>
              <el-tag v-if="pendingRequestCount > 0" type="warning" effect="light" size="small">
                待审批 {{ pendingRequestCount }} 条
              </el-tag>
            </div>
          </template>

          <div
            class="status-card"
            :class="{ 'is-pending': pendingRequestCount > 0, 'is-ready': pendingRequestCount === 0 }"
          >
            <div class="status-label">{{ pendingRequestCount > 0 ? '当前状态' : '当前状态' }}</div>
            <div class="status-value">
              {{
                pendingRequestCount > 0
                  ? `你有 ${pendingRequestCount} 条待审批申请，可继续申请其他项目或在右侧记录中取消。`
                  : '暂无待审批申请，可提交新的预约权限申请'
              }}
            </div>
          </div>

          <div class="list-block">
            <div class="list-block-header">
              <div class="list-block-title">可申请项目列表</div>
              <el-tag size="small" effect="plain">{{ filteredJoinableProjects.length }} / {{ joinableProjects.length }}</el-tag>
            </div>
            <div class="list-block-desc">列表由后端同步权鉴项目后提供，仅展示已配置“对外展示”的可申请项目，名称以对外展示名称为准。</div>
            <el-input
              v-model="projectKeyword"
              clearable
              placeholder="按对外展示名称 / 项目名称搜索"
              class="project-search"
            />
            <el-table
              :data="filteredJoinableProjects"
              size="small"
              height="220"
              stripe
              class="project-list-table"
              empty-text="暂无可申请项目"
            >
              <el-table-column label="项目名称" min-width="220">
                <template #default="{ row }">
                  <div class="project-name-cell">
                    <div class="project-name-stack">
                      <span>{{ getProjectDisplayName(row) }}</span>
                      <span
                        v-if="row.external_display_name && row.external_display_name !== row.name"
                        class="project-name-sub"
                      >
                        内部名称：{{ row.name }}
                      </span>
                    </div>
                    <el-tag v-if="form.target_project_id === row.id" size="small" type="success" effect="light">
                      已选择
                    </el-tag>
                  </div>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="86" align="right">
                <template #default="{ row }">
                  <el-button
                    text
                    type="primary"
                    @click="selectProject(row)"
                  >
                    选择
                  </el-button>
                </template>
              </el-table-column>
            </el-table>
          </div>

          <el-form label-position="top" class="request-form">
            <el-form-item label="目标项目">
              <el-input
                :model-value="selectedProjectLabel"
                readonly
                placeholder="请先从上方项目列表选择"
              />
            </el-form-item>

            <el-form-item label="申请说明（选填）">
              <el-input
                v-model="form.reason"
                type="textarea"
                :rows="5"
                maxlength="2000"
                show-word-limit
                placeholder="例如：计划在本月开展该项目相关实验，需要预约 XX 仪器"
              />
            </el-form-item>

            <div class="form-actions">
              <el-button
                type="primary"
                :loading="submitting"
                @click="handleSubmit"
              >
                提交申请
              </el-button>
            </div>
          </el-form>

          <div v-if="!loading && joinableProjects.length === 0" class="empty-box">
            <el-empty description="暂无可申请项目（可能尚未配置对外展示）" :image-size="72" />
          </div>
        </el-card>

        <el-card shadow="never" class="panel-card history-panel">
          <template #header>
            <div class="panel-header">
              <div class="panel-title">我的申请记录</div>
              <el-tag size="small" effect="plain">{{ myRequests.length }} 条</el-tag>
            </div>
          </template>

          <el-table
            :data="myRequests"
            stripe
            size="small"
            max-height="520"
            v-loading="loading"
            class="history-table"
          >
            <el-table-column label="目标项目" min-width="160">
              <template #default="{ row }">
                {{ getProjectLabel(row.target_project, row.target_project_id) }}
              </template>
            </el-table-column>
            <el-table-column label="状态" width="110">
              <template #default="{ row }">
                <el-tag :type="getStatusTagType(row.status)">
                  {{ getStatusLabel(row.status) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="提交时间" width="170">
              <template #default="{ row }">
                {{ formatDateTime(row.created_at) }}
              </template>
            </el-table-column>
            <el-table-column label="审批备注" min-width="220" show-overflow-tooltip>
              <template #default="{ row }">
                {{ row.review_comment || '-' }}
              </template>
            </el-table-column>
            <el-table-column label="操作" width="110" align="center">
              <template #default="{ row }">
                <el-button
                  v-if="row.status === 'PENDING'"
                  text
                  type="danger"
                  :loading="cancelingRequestId === row.id"
                  @click="handleCancelRequest(row.id)"
                >
                  取消申请
                </el-button>
                <span v-else>-</span>
              </template>
            </el-table-column>
            <template #empty>
              <el-empty description="暂无申请记录" :image-size="72" />
            </template>
          </el-table>
        </el-card>
      </div>

      <el-card v-if="authStore.isStaff()" shadow="never" class="panel-card admin-config-card">
        <template #header>
          <div class="panel-header">
            <div class="panel-title">管理员配置：对外开放项目</div>
            <el-space>
              <el-tag size="small" effect="plain">
                已开放 {{ openExternalProjectCount }} / {{ adminProjects.length }}
              </el-tag>
              <el-button size="small" @click="loadAdminProjects" :loading="adminProjectsLoading">
                刷新项目配置
              </el-button>
            </el-space>
          </div>
        </template>

        <div class="list-block-desc admin-desc">
          这里配置的是本地镜像元数据。外部用户“项目预约权限申请”列表只会显示被开启“对外开放”的项目。
        </div>

        <div class="admin-toolbar">
          <el-input
            v-model="adminProjectKeyword"
            clearable
            placeholder="搜索项目名称"
            class="admin-search"
          />
          <el-switch
            v-model="adminOnlyShowOpen"
            inline-prompt
            active-text="仅看已开放"
            inactive-text="全部"
          />
        </div>

        <el-table
          :data="filteredAdminProjects"
          stripe
          size="small"
          max-height="420"
          v-loading="adminProjectsLoading"
        >
          <el-table-column label="项目名称" min-width="220">
            <template #default="{ row }">
              <div class="project-name-cell">
                <span>{{ row.name }}</span>
                <el-tag v-if="row.account_id" size="small" effect="plain">已绑定账户</el-tag>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="状态" width="88">
            <template #default="{ row }">
              <el-tag :type="row.active ? 'success' : 'info'" effect="light">
                {{ row.active ? '启用' : '停用' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="对外开放申请" width="140" align="center">
            <template #default="{ row }">
              <el-switch
                :model-value="!!row.allow_external_booking_request"
                :loading="updatingAdminProjectId === row.id"
                @change="(value) => handleToggleExternalOpen(row, !!value)"
              />
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import {
  cancelProjectJoinRequest,
  createProjectJoinRequest,
  getProjects,
  getJoinableProjects,
  getMyProjectJoinRequests,
  setProjectExternalBookingAccess
} from '@/api/projects'
import type { Project, ProjectJoinRequest, ProjectJoinRequestStatus } from '@/types'
import { formatDateTime } from '@/utils/helpers'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()

const loading = ref(false)
const submitting = ref(false)
const cancelingRequestId = ref<number | null>(null)
const joinableProjects = ref<Project[]>([])
const myRequests = ref<ProjectJoinRequest[]>([])
const projectKeyword = ref('')
const adminProjects = ref<Project[]>([])
const adminProjectsLoading = ref(false)
const updatingAdminProjectId = ref<number | null>(null)
const adminProjectKeyword = ref('')
const adminOnlyShowOpen = ref(false)

const form = reactive({
  target_project_id: undefined as number | undefined,
  reason: ''
})

const pendingRequests = computed(() =>
  myRequests.value.filter((item) => item.status === 'PENDING')
)
const pendingRequestCount = computed(() => pendingRequests.value.length)
const getProjectDisplayName = (project?: Project | null) => {
  const externalName = (project?.external_display_name || '').trim()
  if (externalName) return externalName
  return project?.name || ''
}
const getProjectLabel = (project?: Project | null, fallbackId?: number) => {
  const label = getProjectDisplayName(project)
  if (label) return label
  return fallbackId ? `#${fallbackId}` : ''
}
const filteredJoinableProjects = computed(() => {
  const keyword = projectKeyword.value.trim().toLowerCase()
  if (!keyword) return joinableProjects.value
  return joinableProjects.value.filter((item) => {
    const internalName = (item.name || '').toLowerCase()
    const externalName = (item.external_display_name || '').toLowerCase()
    return internalName.includes(keyword) || externalName.includes(keyword)
  })
})
const openExternalProjectCount = computed(
  () => adminProjects.value.filter((item) => !!item.allow_external_booking_request).length
)
const filteredAdminProjects = computed(() => {
  const keyword = adminProjectKeyword.value.trim().toLowerCase()
  return adminProjects.value.filter((item) => {
    if (adminOnlyShowOpen.value && !item.allow_external_booking_request) return false
    if (!keyword) return true
    return (item.name || '').toLowerCase().includes(keyword)
  })
})
const selectedProject = computed(() =>
  joinableProjects.value.find((item) => item.id === form.target_project_id) || null
)
const selectedProjectLabel = computed(() =>
  getProjectDisplayName(selectedProject.value)
)
const unwrapArray = <T = any>(response: any): T[] => {
  if (Array.isArray(response)) return response
  return response?.data || []
}

const getStatusLabel = (status: ProjectJoinRequestStatus) => {
  if (status === 'PENDING') return '待审批'
  if (status === 'APPROVED') return '已通过'
  if (status === 'REJECTED') return '已驳回'
  if (status === 'CANCELLED') return '已撤销'
  return status
}

const getStatusTagType = (status: ProjectJoinRequestStatus) => {
  if (status === 'PENDING') return 'warning'
  if (status === 'APPROVED') return 'success'
  if (status === 'REJECTED') return 'danger'
  return 'info'
}

const syncFormState = () => {
  if (
    form.target_project_id &&
    !joinableProjects.value.some((item) => item.id === form.target_project_id)
  ) {
    form.target_project_id = undefined
  }
}

const loadData = async () => {
  loading.value = true
  try {
    const [joinableRes, requestsRes] = await Promise.all([
      getJoinableProjects(),
      getMyProjectJoinRequests({ limit: 50 })
    ])
    joinableProjects.value = unwrapArray<Project>(joinableRes)
    myRequests.value = unwrapArray<ProjectJoinRequest>(requestsRes)
    syncFormState()
  } catch (error: any) {
    console.error('加载项目预约权限申请页面数据失败:', error)
    ElMessage.error(error?.response?.data?.detail || '加载项目列表失败')
  } finally {
    loading.value = false
  }

  if (authStore.isStaff()) {
    await loadAdminProjects()
  }
}

const loadAdminProjects = async () => {
  if (!authStore.isStaff()) return
  adminProjectsLoading.value = true
  try {
    const response = await getProjects({ active: true, limit: 2000 })
    const rows = unwrapArray<Project>(response)
    adminProjects.value = rows.sort((a, b) => (a.name || '').localeCompare(b.name || ''))
  } catch (error: any) {
    console.error('加载管理员项目开放配置失败:', error)
    ElMessage.error(error?.response?.data?.detail || '加载项目配置失败')
  } finally {
    adminProjectsLoading.value = false
  }
}

const handleToggleExternalOpen = async (project: Project, value: boolean) => {
  if (!authStore.isStaff()) return
  const previous = !!project.allow_external_booking_request
  if (previous === value) return
  updatingAdminProjectId.value = project.id
  project.allow_external_booking_request = value
  try {
    const updated = await setProjectExternalBookingAccess(project.id, value)
    const idx = adminProjects.value.findIndex((item) => item.id === project.id)
    if (idx >= 0) {
      adminProjects.value[idx] = { ...adminProjects.value[idx], ...updated }
    }
    if (!authStore.isExternalUser()) {
      await loadDataForJoinableRefreshOnly()
    }
    ElMessage.success(value ? '已开放项目预约权限申请' : '已关闭项目预约权限申请')
  } catch (error: any) {
    project.allow_external_booking_request = previous
    console.error(error)
    ElMessage.error(error?.response?.data?.detail || '更新项目开放配置失败')
  } finally {
    updatingAdminProjectId.value = null
  }
}

const loadDataForJoinableRefreshOnly = async () => {
  try {
    const response = await getJoinableProjects()
    joinableProjects.value = unwrapArray<Project>(response)
    syncFormState()
  } catch {
    // ignore; admin config should not fail because external list refresh fails
  }
}

const selectProject = (project: Project) => {
  form.target_project_id = project.id
}

const handleSubmit = async () => {
  if (!form.target_project_id) {
    ElMessage.warning('请选择目标项目')
    return
  }
  submitting.value = true
  try {
    await createProjectJoinRequest({
      target_project_id: form.target_project_id,
      reason: form.reason?.trim() || undefined
    })
    ElMessage.success('项目预约权限申请已提交，等待项目管理员审批')
    form.reason = ''
    await loadData()
  } catch (error: any) {
    console.error(error)
    ElMessage.error(error?.response?.data?.detail || '提交项目预约权限申请失败')
  } finally {
    submitting.value = false
  }
}

const handleCancelRequest = async (requestId: number) => {
  cancelingRequestId.value = requestId
  try {
    await cancelProjectJoinRequest(requestId)
    ElMessage.success('已撤销项目预约权限申请')
    await loadData()
  } catch (error: any) {
    console.error(error)
    ElMessage.error(error?.response?.data?.detail || '撤销项目预约权限申请失败')
  } finally {
    cancelingRequestId.value = null
  }
}

const goProfile = () => {
  router.push('/profile')
}

onMounted(async () => {
  await loadData()
})
</script>

<style scoped>
.project-access-page {
  padding: 20px;
  background:
    radial-gradient(circle at 12% 10%, rgba(64, 158, 255, 0.08), transparent 46%),
    radial-gradient(circle at 92% 14%, rgba(103, 194, 58, 0.07), transparent 42%);
}

.page-shell {
  width: min(1240px, 100%);
  margin: 0 auto;
  display: grid;
  gap: 16px;
}

.hero-card,
.panel-card {
  border-radius: 14px;
}

.hero {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.hero-main {
  min-width: 0;
}

.hero-eyebrow {
  display: inline-flex;
  align-items: center;
  padding: 2px 8px;
  border-radius: 999px;
  background: #eef5ff;
  color: #3a7bd5;
  font-size: 12px;
  line-height: 1.6;
}

.hero-title {
  margin-top: 10px;
  font-size: 22px;
  font-weight: 700;
  color: #1f2a37;
  line-height: 1.3;
}

.hero-subtitle {
  margin-top: 8px;
  color: #5f6b7a;
  line-height: 1.7;
  max-width: 760px;
}

.hero-tags {
  margin-top: 12px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.hero-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.hero-alerts {
  margin-top: 14px;
  display: grid;
  gap: 10px;
}

.content-grid {
  display: grid;
  grid-template-columns: minmax(340px, 420px) minmax(0, 1fr);
  gap: 16px;
  align-items: start;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.panel-title {
  font-size: 15px;
  font-weight: 600;
  color: #303133;
}

.status-card {
  border-radius: 12px;
  padding: 12px 14px;
  margin-bottom: 12px;
  border: 1px solid #e4e7ed;
  background: #fafafa;
}

.status-card.is-pending {
  border-color: #f3d19e;
  background: #fff8eb;
}

.status-card.is-ready {
  border-color: #b3e19d;
  background: #f3fbee;
}

.status-label {
  font-size: 12px;
  color: #909399;
  margin-bottom: 6px;
}

.status-value {
  color: #303133;
  line-height: 1.5;
  font-weight: 500;
}

.request-form {
  margin-top: 4px;
}

.list-block {
  margin-bottom: 14px;
  padding: 12px;
  border: 1px solid #ebeef5;
  border-radius: 12px;
  background: #fcfdff;
}

.list-block-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.list-block-title {
  font-size: 13px;
  font-weight: 600;
  color: #303133;
}

.list-block-desc {
  margin-top: 4px;
  margin-bottom: 10px;
  color: #909399;
  font-size: 12px;
  line-height: 1.5;
}

.project-search {
  margin-bottom: 10px;
}

.project-list-table {
  width: 100%;
}

.project-name-cell {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.project-name-stack {
  min-width: 0;
  display: grid;
  gap: 2px;
}

.project-name-sub {
  font-size: 12px;
  color: #909399;
  line-height: 1.3;
}

.form-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 4px;
}

.empty-box {
  margin-top: 8px;
  padding-top: 4px;
  border-top: 1px dashed #ebeef5;
}

.history-panel :deep(.el-card__body) {
  padding-top: 8px;
}

.admin-config-card :deep(.el-card__body) {
  padding-top: 10px;
}

.history-table {
  width: 100%;
}

.admin-desc {
  margin-bottom: 10px;
}

.admin-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.admin-search {
  width: min(420px, 100%);
}

@media (max-width: 1024px) {
  .content-grid {
    grid-template-columns: 1fr;
  }

  .hero {
    flex-direction: column;
  }

  .hero-actions {
    width: 100%;
    justify-content: flex-end;
  }

  .admin-toolbar {
    flex-direction: column;
    align-items: stretch;
  }

  .admin-search {
    width: 100%;
  }
}

@media (max-width: 640px) {
  .project-access-page {
    padding: 12px;
  }

  .hero-title {
    font-size: 18px;
  }

  .hero-actions {
    justify-content: flex-start;
  }

  .form-actions {
    display: grid;
    grid-template-columns: 1fr;
  }

  .project-name-cell {
    align-items: flex-start;
    flex-direction: column;
  }

  .form-actions :deep(.el-button) {
    width: 100%;
    margin-left: 0;
  }
}
</style>
