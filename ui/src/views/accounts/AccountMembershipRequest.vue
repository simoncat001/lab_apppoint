<template>
  <div class="page-container account-membership-page">
    <el-card class="header-card" shadow="never">
      <div class="header-row">
        <div>
          <div class="page-kicker">Account Membership</div>
          <div class="page-title">所属账户申请</div>
          <div class="page-subtitle">外部用户可以加入多个所属账户；审批通过后，预约时再选择本次使用哪个账户结算。</div>
        </div>
        <el-button :icon="Refresh" @click="loadPageData">刷新</el-button>
      </div>
    </el-card>

    <el-row :gutter="16">
      <el-col :xs="24" :lg="10">
        <el-card shadow="never" class="panel-card">
          <template #header>
            <div class="card-header">
              <span>当前状态</span>
              <el-tag v-if="pendingRequest" type="warning" effect="plain">待审批</el-tag>
              <el-tag v-else-if="currentOrgAccounts.length" type="success" effect="plain">已配置</el-tag>
              <el-tag v-else type="info" effect="plain">未配置</el-tag>
            </div>
          </template>

          <div class="status-list">
            <div class="status-item">
              <span class="status-label">当前可用账户</span>
              <span class="status-value">{{ currentOrgAccountNames || '未配置' }}</span>
            </div>
            <div class="status-item">
              <span class="status-label">待审批目标账户</span>
              <span class="status-value">{{ pendingRequest?.target_account?.name || '-' }}</span>
            </div>
            <div class="status-item">
              <span class="status-label">说明</span>
              <span class="status-value">管理员也可以在“账户管理”里直接把你加入某个共享所属账户。</span>
            </div>
          </div>

          <el-alert
            class="status-alert"
            :type="statusAlertType"
            :closable="false"
            show-icon
            :title="statusAlertTitle"
          />
        </el-card>
      </el-col>

      <el-col :xs="24" :lg="14">
        <el-card shadow="never" class="panel-card">
          <template #header>
            <div class="card-header">
              <span>提交申请</span>
              <el-button
                v-if="pendingRequest"
                type="danger"
                plain
                :loading="submitting"
                @click="handleCancel"
              >
                撤销待审批申请
              </el-button>
            </div>
          </template>

          <el-alert
            v-if="!pendingRequest && !selectableOrganizations.length"
            class="inline-alert"
            type="warning"
            :closable="false"
            show-icon
            title="当前没有可申请的所属账户。请联系管理员在账户管理中直接配置，或先创建可共享的所属账户。"
          />

          <el-form label-position="top">
            <el-form-item label="目标所属账户" required>
              <el-select
                v-model="form.target_account_id"
                style="width: 100%"
                filterable
                clearable
                :disabled="!!pendingRequest || submitting"
                placeholder="请选择要加入的所属账户"
              >
                <el-option
                  v-for="account in selectableOrganizations"
                  :key="account.id"
                  :label="account.name"
                  :value="account.id"
                />
              </el-select>
            </el-form-item>

            <el-form-item label="申请说明">
              <el-input
                v-model="form.reason"
                type="textarea"
                :rows="3"
                maxlength="200"
                show-word-limit
                :disabled="!!pendingRequest || submitting"
                placeholder="可选，说明你的所属单位或申请原因"
              />
            </el-form-item>

            <div class="form-actions">
              <el-button
                type="primary"
                :loading="submitting"
                :disabled="!!pendingRequest || !selectableOrganizations.length"
                @click="handleSubmit"
              >
                提交申请
              </el-button>
            </div>
          </el-form>
        </el-card>
      </el-col>
    </el-row>

    <el-card shadow="never" class="panel-card history-card">
      <template #header>
        <div class="card-header">
          <span>我的所属账户申请记录</span>
          <el-tag type="info" effect="plain">{{ myRequests.length }} 条</el-tag>
        </div>
      </template>

      <el-table :data="myRequests" stripe>
        <el-table-column label="来源账户" min-width="180">
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
        <el-table-column label="申请说明" min-width="220" show-overflow-tooltip>
          <template #default="{ row }">
            {{ row.reason || '-' }}
          </template>
        </el-table-column>
        <el-table-column label="提交时间" width="180">
          <template #default="{ row }">
            {{ formatDateTime(row.created_at) }}
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import dayjs from 'dayjs'
import { ElMessage } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import {
  cancelAccountMembershipChangeRequest,
  createAccountMembershipChangeRequest,
  getAccounts,
  getJoinableOrganizations,
  getMyAccountMembershipChangeRequests
} from '@/api/accounts'
import { useAuthStore } from '@/stores/auth'
import type { Account, AccountMembershipChangeRequest, AccountMembershipChangeRequestStatus } from '@/types'

const authStore = useAuthStore()

const currentOrgAccounts = ref<Account[]>([])
const joinableOrganizations = ref<Account[]>([])
const myRequests = ref<AccountMembershipChangeRequest[]>([])
const submitting = ref(false)

const form = reactive({
  target_account_id: undefined as number | undefined,
  reason: ''
})

const pendingRequest = computed(() => myRequests.value.find((item) => item.status === 'PENDING'))

const currentOrgAccountIds = computed(() => new Set(currentOrgAccounts.value.map((account) => account.id)))
const currentOrgAccountNames = computed(() =>
  currentOrgAccounts.value.length ? currentOrgAccounts.value.map((account) => account.name).join('、') : ''
)
const selectableOrganizations = computed(() =>
  joinableOrganizations.value.filter((account) => !currentOrgAccountIds.value.has(account.id))
)
const statusAlertTitle = computed(() => {
  if (pendingRequest.value) {
    return '当前有一条待审批的所属账户加入申请。审批完成前，已生效账户仍可继续使用。'
  }
  if (currentOrgAccounts.value.length) {
    return `你当前已加入 ${currentOrgAccounts.value.length} 个所属账户。预约时可以按项目选择结算账户。`
  }
  return '所属账户审批通过后才会生效。生效前，外部用户不能使用个人账户创建预约。'
})
const statusAlertType = computed(() => {
  if (pendingRequest.value) return 'warning'
  if (currentOrgAccounts.value.length) return 'success'
  return 'info'
})

const unwrapArray = <T,>(response: any): T[] => {
  if (Array.isArray(response)) return response
  return response?.data || []
}

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

const formatDateTime = (value?: string | null) => {
  if (!value) return '-'
  return dayjs(value).format('YYYY-MM-DD HH:mm')
}

const loadPageData = async () => {
  const userId = authStore.user?.id
  if (!userId) return

  try {
    const [accountsRes, orgsRes, myRequestsRes] = await Promise.all([
      getAccounts(),
      getJoinableOrganizations(),
      getMyAccountMembershipChangeRequests({ limit: 50 })
    ])

    const relatedAccounts = unwrapArray<Account>(accountsRes)
    joinableOrganizations.value = unwrapArray<Account>(orgsRes)
    myRequests.value = unwrapArray<AccountMembershipChangeRequest>(myRequestsRes)

    currentOrgAccounts.value = relatedAccounts.filter(
        (account) =>
          account.user_id == null &&
          ((account.members || []).some((member) => member.id === userId) ||
            (account.member_ids || []).includes(Number(userId)))
      )

    if (pendingRequest.value) {
      form.target_account_id = pendingRequest.value.target_account_id || undefined
    } else if (
      form.target_account_id &&
      !selectableOrganizations.value.some((item) => item.id === form.target_account_id)
    ) {
      form.target_account_id = undefined
    }
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || '加载所属账户申请数据失败')
    console.error(error)
  }
}

const handleSubmit = async () => {
  if (!form.target_account_id) {
    ElMessage.warning('请选择目标所属账户')
    return
  }

  submitting.value = true
  try {
    await createAccountMembershipChangeRequest({
      target_account_id: form.target_account_id,
      reason: form.reason.trim() || undefined
    })
    ElMessage.success('申请已提交，等待管理员审批')
    form.reason = ''
    await loadPageData()
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || '提交申请失败')
    console.error(error)
  } finally {
    submitting.value = false
  }
}

const handleCancel = async () => {
  if (!pendingRequest.value) return

  submitting.value = true
  try {
    await cancelAccountMembershipChangeRequest(pendingRequest.value.id)
    ElMessage.success('已撤销待审批申请')
    await loadPageData()
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || '撤销申请失败')
    console.error(error)
  } finally {
    submitting.value = false
  }
}

onMounted(() => {
  loadPageData()
})
</script>

<style scoped>
.account-membership-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.header-card,
.panel-card {
  border-radius: 20px;
  border: 1px solid #dfe7f3;
  box-shadow: 0 12px 30px rgba(15, 23, 42, 0.05);
}

.header-row,
.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.page-kicker {
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: #2563eb;
}

.page-title {
  margin-top: 6px;
  font-size: 26px;
  font-weight: 700;
  color: #0f172a;
}

.page-subtitle {
  margin-top: 6px;
  font-size: 14px;
  color: #64748b;
}

.status-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.status-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding-bottom: 12px;
  border-bottom: 1px solid #e8eef6;
}

.status-item:last-child {
  border-bottom: none;
  padding-bottom: 0;
}

.status-label {
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #64748b;
}

.status-value {
  font-size: 14px;
  font-weight: 600;
  color: #111827;
}

.status-alert,
.history-card {
  margin-top: 16px;
}

.inline-alert {
  margin-bottom: 16px;
  border-radius: 16px;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
}

@media (max-width: 900px) {
  .header-row,
  .card-header {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
