<template>
  <div class="project-access-approval-page">
    <el-card class="approval-card" shadow="never">
      <template #header>
        <div class="card-header">
          <div class="title-wrap">
            <span class="title">项目预约权限审批（当前项目）</span>
            <el-tag size="small" effect="plain">
              待审批 {{ pendingRequests.length }} 条
            </el-tag>
          </div>
          <el-button :icon="Refresh" :loading="loading" @click="loadPendingRequests">刷新</el-button>
        </div>
      </template>

      <el-alert
        v-if="!canReview"
        title="仅内部管理员可审批项目预约权限申请"
        type="warning"
        show-icon
        :closable="false"
      />

      <template v-else>
        <el-alert
          :title="`当前项目：${currentProjectName}`"
          type="info"
          show-icon
          :closable="false"
          class="block-alert"
        />

        <el-alert
          v-if="!currentProjectId"
          title="请先切换并选择当前项目，再进行审批。"
          type="warning"
          show-icon
          :closable="false"
          class="block-alert"
        />

        <el-alert
          v-else-if="noPermissionForCurrentProject"
          title="你在当前项目没有审批权限。请切换到有管理权限的项目。"
          type="warning"
          show-icon
          :closable="false"
          class="block-alert"
        />

        <div class="toolbar">
          <el-button size="small" @click="goProjectSelector">切换当前项目</el-button>
        </div>

        <el-table
          :data="pendingRequests"
          stripe
          size="small"
          max-height="560"
          v-loading="loading"
        >
          <el-table-column label="申请人" min-width="120">
            <template #default="{ row }">
              {{ row.requester?.username || `#${row.requester_user_id}` }}
            </template>
          </el-table-column>
          <el-table-column label="目标项目" min-width="180">
            <template #default="{ row }">
              {{ row.target_project?.external_display_name || row.target_project?.name || `#${row.target_project_id}` }}
            </template>
          </el-table-column>
          <el-table-column label="申请说明" min-width="220" show-overflow-tooltip>
            <template #default="{ row }">
              {{ row.reason || '-' }}
            </template>
          </el-table-column>
          <el-table-column label="提交时间" width="170">
            <template #default="{ row }">
              {{ formatDateTime(row.created_at) }}
            </template>
          </el-table-column>
          <el-table-column label="操作" width="180" fixed="right">
            <template #default="{ row }">
              <el-space>
                <el-button
                  type="success"
                  size="small"
                  :loading="reviewingRequestId === row.id"
                  :disabled="!currentProjectId"
                  @click="handleApprove(row)"
                >
                  通过
                </el-button>
                <el-button
                  type="danger"
                  size="small"
                  :loading="reviewingRequestId === row.id"
                  :disabled="!currentProjectId"
                  @click="handleReject(row)"
                >
                  驳回
                </el-button>
              </el-space>
            </template>
          </el-table-column>
          <template #empty>
            <el-empty description="当前项目暂无待审批申请" :image-size="72" />
          </template>
        </el-table>
      </template>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import {
  approveProjectJoinRequest,
  getProjectJoinRequestsForApproval,
  rejectProjectJoinRequest
} from '@/api/projects'
import type { ProjectJoinRequest } from '@/types'
import { formatDateTime } from '@/utils/helpers'
import { useAuthStore } from '@/stores/auth'
import { useProjectContextStore } from '@/stores/project-context'

const router = useRouter()
const authStore = useAuthStore()
const projectContextStore = useProjectContextStore()

const loading = ref(false)
const reviewingRequestId = ref<number | null>(null)
const noPermissionForCurrentProject = ref(false)
const pendingRequests = ref<ProjectJoinRequest[]>([])

const canReview = computed(() => authStore.isStaff() || authStore.isInternalUser())
const currentProjectId = computed(() => projectContextStore.currentProjectId)
const currentProjectName = computed(() => projectContextStore.currentProjectName || '未选择项目')

const unwrapArray = <T = any>(response: any): T[] => {
  if (Array.isArray(response)) return response
  return response?.data || []
}

const loadPendingRequests = async () => {
  if (!canReview.value || !currentProjectId.value) {
    pendingRequests.value = []
    noPermissionForCurrentProject.value = false
    return
  }

  loading.value = true
  noPermissionForCurrentProject.value = false
  try {
    const response = await getProjectJoinRequestsForApproval({ status: 'PENDING', limit: 200 })
    pendingRequests.value = unwrapArray<ProjectJoinRequest>(response)
  } catch (error: any) {
    pendingRequests.value = []
    if (error?.response?.status === 403) {
      noPermissionForCurrentProject.value = true
      return
    }
    ElMessage.error(error?.response?.data?.detail || '加载审批列表失败')
    console.error(error)
  } finally {
    loading.value = false
  }
}

const handleApprove = async (row: ProjectJoinRequest) => {
  try {
    await ElMessageBox.confirm(
      `确认通过申请 #${row.id}？通过后该用户将获得当前项目预约权限。`,
      '审批确认',
      { type: 'warning' }
    )
  } catch {
    return
  }

  reviewingRequestId.value = row.id
  try {
    await approveProjectJoinRequest(row.id, {})
    ElMessage.success('审批通过')
    await loadPendingRequests()
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || '审批失败')
    console.error(error)
  } finally {
    reviewingRequestId.value = null
  }
}

const handleReject = async (row: ProjectJoinRequest) => {
  let comment = ''
  try {
    const result = await ElMessageBox.prompt('请输入驳回原因（可选）', `驳回申请 #${row.id}`, {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      inputType: 'textarea'
    })
    comment = result.value || ''
  } catch {
    return
  }

  reviewingRequestId.value = row.id
  try {
    await rejectProjectJoinRequest(row.id, { comment })
    ElMessage.success('已驳回申请')
    await loadPendingRequests()
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || '驳回失败')
    console.error(error)
  } finally {
    reviewingRequestId.value = null
  }
}

const goProjectSelector = () => {
  router.push('/project-context')
}

watch(
  () => currentProjectId.value,
  async () => {
    await loadPendingRequests()
  }
)

onMounted(async () => {
  await loadPendingRequests()
})
</script>

<style scoped>
.project-access-approval-page {
  padding: 20px;
}

.approval-card {
  border-radius: 14px;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.title-wrap {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.title {
  font-size: 16px;
  font-weight: 600;
  color: #1f2a37;
}

.block-alert {
  margin-bottom: 10px;
}

.toolbar {
  margin: 8px 0 12px;
  display: flex;
  justify-content: flex-end;
}
</style>
