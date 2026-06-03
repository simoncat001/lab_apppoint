<template>
  <div class="page-container account-membership-approval-page">
    <el-card class="header-card" shadow="never">
      <div class="header-row">
        <div>
          <div class="page-kicker">Account Membership</div>
          <div class="page-title">所属账户审批</div>
          <div class="page-subtitle">审批外部用户的所属账户加入申请。审批通过后，目标账户会加入该用户可选的预约结算账户列表。</div>
        </div>
        <div class="header-actions">
          <el-select v-model="statusFilter" class="status-select" placeholder="筛选状态" @change="loadRequests">
            <el-option label="全部" value="" />
            <el-option label="待审批" value="PENDING" />
            <el-option label="已通过" value="APPROVED" />
            <el-option label="已驳回" value="REJECTED" />
            <el-option label="已撤销" value="CANCELLED" />
          </el-select>
          <el-button :icon="Refresh" @click="loadRequests">刷新</el-button>
        </div>
      </div>
    </el-card>

    <el-row :gutter="16" class="summary-row">
      <el-col :xs="24" :sm="8">
        <el-card shadow="never" class="summary-card">
          <div class="summary-label">当前筛选结果</div>
          <div class="summary-value">{{ requests.length }}</div>
        </el-card>
      </el-col>
      <el-col :xs="24" :sm="8">
        <el-card shadow="never" class="summary-card">
          <div class="summary-label">待审批</div>
          <div class="summary-value">{{ pendingCount }}</div>
        </el-card>
      </el-col>
      <el-col :xs="24" :sm="8">
        <el-card shadow="never" class="summary-card">
          <div class="summary-label">已处理</div>
          <div class="summary-value">{{ processedCount }}</div>
        </el-card>
      </el-col>
    </el-row>

    <el-card shadow="never" class="table-card">
      <template #header>
        <div class="card-header">
          <span>所属账户申请列表</span>
          <el-tag type="info" effect="plain">{{ requests.length }} 条</el-tag>
        </div>
      </template>

      <el-alert
        class="approval-alert"
        type="info"
        :closable="false"
        show-icon
        title="管理员也可以在“账户管理”中直接把外部用户加入共享所属账户；通过这里审批后，目标账户也会加入该用户的可选结算账户。"
      />

      <el-table v-loading="loading" :data="requests" stripe empty-text="当前筛选条件下没有所属账户申请">
        <el-table-column label="申请用户" min-width="160">
          <template #default="{ row }">
            <div class="user-cell">
              <div class="user-primary">
                {{ getRequesterDisplayName(row) }}
              </div>
              <div class="user-secondary">
                {{ row.requester?.username || '-' }}
              </div>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="来源账户" min-width="160">
          <template #default="{ row }">
            {{ row.source_account?.name || '-' }}
          </template>
        </el-table-column>
        <el-table-column label="目标账户" min-width="180">
          <template #default="{ row }">
            {{ row.target_account?.name || '-' }}
          </template>
        </el-table-column>
        <el-table-column label="状态" width="110">
          <template #default="{ row }">
            <el-tag :type="getStatusTagType(row.status)">
              {{ getStatusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="申请说明" min-width="240" show-overflow-tooltip>
          <template #default="{ row }">
            {{ row.reason || '-' }}
          </template>
        </el-table-column>
        <el-table-column label="审批备注" min-width="220" show-overflow-tooltip>
          <template #default="{ row }">
            {{ row.review_comment || '-' }}
          </template>
        </el-table-column>
        <el-table-column label="提交时间" width="170">
          <template #default="{ row }">
            {{ formatDateTime(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="审批时间" width="170">
          <template #default="{ row }">
            {{ formatDateTime(row.reviewed_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <div v-if="row.status === 'PENDING'" class="action-group">
              <el-button
                type="primary"
                link
                :loading="reviewingRequestId === row.id && reviewingAction === 'approve'"
                @click="handleApprove(row)"
              >
                通过
              </el-button>
              <el-button
                type="danger"
                link
                :loading="reviewingRequestId === row.id && reviewingAction === 'reject'"
                @click="handleReject(row)"
              >
                驳回
              </el-button>
            </div>
            <span v-else class="muted-text">已处理</span>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import dayjs from 'dayjs'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import {
  approveAccountMembershipChangeRequest,
  getAccountMembershipChangeRequests,
  rejectAccountMembershipChangeRequest
} from '@/api/accounts'
import type { AccountMembershipChangeRequest, AccountMembershipChangeRequestStatus } from '@/types'

const loading = ref(false)
const requests = ref<AccountMembershipChangeRequest[]>([])
const statusFilter = ref<AccountMembershipChangeRequestStatus | ''>('PENDING')
const reviewingRequestId = ref<number | null>(null)
const reviewingAction = ref<'approve' | 'reject' | null>(null)

const unwrapArray = <T,>(response: any): T[] => {
  if (Array.isArray(response)) return response
  return response?.data || []
}

const pendingCount = computed(() => requests.value.filter((item) => item.status === 'PENDING').length)
const processedCount = computed(() => requests.value.filter((item) => item.status !== 'PENDING').length)

const getStatusLabel = (status: AccountMembershipChangeRequestStatus) => {
  if (status === 'PENDING') return '待审批'
  if (status === 'APPROVED') return '已通过'
  if (status === 'REJECTED') return '已驳回'
  if (status === 'CANCELLED') return '已撤销'
  return status
}

const getStatusTagType = (status: AccountMembershipChangeRequestStatus) => {
  if (status === 'PENDING') return 'warning'
  if (status === 'APPROVED') return 'success'
  if (status === 'REJECTED') return 'danger'
  return 'info'
}

const getRequesterDisplayName = (row: AccountMembershipChangeRequest) => {
  const firstName = row.requester?.first_name?.trim() || ''
  const lastName = row.requester?.last_name?.trim() || ''
  const fullName = `${lastName}${firstName}`.trim()
  return fullName || row.requester?.username || `用户 #${row.requester_user_id}`
}

const formatDateTime = (value?: string | null) => {
  if (!value) return '-'
  return dayjs(value).format('YYYY-MM-DD HH:mm')
}

const loadRequests = async () => {
  loading.value = true
  try {
    const response = await getAccountMembershipChangeRequests({
      status: statusFilter.value || undefined,
      limit: 100
    })
    requests.value = unwrapArray<AccountMembershipChangeRequest>(response)
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || '加载所属账户审批列表失败')
    console.error(error)
  } finally {
    loading.value = false
  }
}

const handleApprove = async (row: AccountMembershipChangeRequest) => {
  try {
    await ElMessageBox.confirm(
      `确认通过 ${row.requester?.username || `用户 #${row.requester_user_id}`} 的所属账户加入申请？`,
      '审批确认',
      { type: 'warning' }
    )
  } catch {
    return
  }

  reviewingRequestId.value = row.id
  reviewingAction.value = 'approve'
  try {
    await approveAccountMembershipChangeRequest(row.id, {})
    ElMessage.success('审批通过，目标账户已加入该用户可选结算账户')
    await loadRequests()
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || '审批失败')
    console.error(error)
  } finally {
    reviewingRequestId.value = null
    reviewingAction.value = null
  }
}

const handleReject = async (row: AccountMembershipChangeRequest) => {
  let comment = ''
  try {
    const result = await ElMessageBox.prompt('请输入驳回原因（可选）', '驳回申请', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      inputType: 'textarea',
      inputPlaceholder: '例如：所属单位信息不完整'
    })
    comment = result.value || ''
  } catch {
    return
  }

  reviewingRequestId.value = row.id
  reviewingAction.value = 'reject'
  try {
    await rejectAccountMembershipChangeRequest(row.id, { comment })
    ElMessage.success('已驳回申请')
    await loadRequests()
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || '驳回失败')
    console.error(error)
  } finally {
    reviewingRequestId.value = null
    reviewingAction.value = null
  }
}

onMounted(() => {
  loadRequests()
})
</script>

<style scoped>
.account-membership-approval-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.header-card,
.summary-card,
.table-card {
  border: none;
  border-radius: 20px;
  box-shadow: 0 18px 40px rgba(15, 23, 42, 0.06);
}

.header-row,
.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.status-select {
  width: 160px;
}

.page-kicker {
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: #16a34a;
  margin-bottom: 10px;
}

.page-title {
  font-size: 28px;
  font-weight: 700;
  color: #0f172a;
  margin-bottom: 8px;
}

.page-subtitle {
  max-width: 760px;
  font-size: 14px;
  line-height: 1.7;
  color: #64748b;
}

.summary-row {
  margin: 0;
}

.approval-alert {
  margin-bottom: 16px;
  border-radius: 16px;
}

.summary-card {
  min-height: 112px;
}

.summary-label {
  font-size: 13px;
  color: #64748b;
  margin-bottom: 14px;
}

.summary-value {
  font-size: 32px;
  font-weight: 700;
  color: #0f172a;
}

.user-cell {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.user-primary {
  font-weight: 600;
  color: #0f172a;
}

.user-secondary,
.muted-text {
  font-size: 12px;
  color: #94a3b8;
}

.action-group {
  display: flex;
  align-items: center;
  gap: 4px;
}

@media (max-width: 768px) {
  .header-row,
  .header-actions,
  .card-header {
    flex-direction: column;
    align-items: stretch;
  }

  .status-select {
    width: 100%;
  }
}
</style>
