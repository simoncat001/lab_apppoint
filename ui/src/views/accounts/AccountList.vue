<template>
  <div class="page-container">
    <el-card class="header-card" shadow="never">
      <div class="header-row">
        <div>
          <div class="page-kicker">Accounts</div>
          <div class="page-title">所属账户管理</div>
          <div class="page-subtitle">维护共享所属账户和默认项目账户。外部用户审批生效后，将直接以所属账户进行预约和结算。</div>
        </div>
        <div class="header-actions">
          <el-button type="primary" :icon="Plus" @click="handleCreate">
            创建所属账户
          </el-button>
          <el-button :icon="Refresh" @click="handleRefresh">
            刷新
          </el-button>
        </div>
      </div>
    </el-card>

    <el-alert
      class="page-alert"
      type="info"
      :closable="false"
      show-icon
      title="标记为“固定”的默认项目账户由对外开放项目自动绑定，只能维护余额，不能停用、删除或改关联项目。"
    />

    <el-card class="filter-card" shadow="never">
      <div class="filter-row">
        <div class="filter-meta">
          <span class="filter-title">筛选条件</span>
          <span class="filter-count">{{ filterCountText }}</span>
        </div>
        <el-space wrap>
          <el-select
            v-model="filterTypeId"
            placeholder="账户类型"
            clearable
            style="width: 180px"
            @change="loadAccounts"
          >
            <el-option
              v-for="type in accountTypes"
              :key="type.id"
              :label="type.name"
              :value="type.id"
            />
          </el-select>
          <el-select
            v-model="filterActive"
            placeholder="状态"
            clearable
            style="width: 120px"
            @change="loadAccounts"
          >
            <el-option label="已激活" :value="true" />
            <el-option label="已停用" :value="false" />
          </el-select>
        </el-space>
      </div>
    </el-card>

    <template v-if="accountSections.length">
      <el-card
        v-for="section in accountSections"
        :key="section.key"
        :class="['section-card', `section-card--${section.key}`]"
        shadow="never"
      >
        <template #header>
          <div class="section-header">
            <div class="section-header__main">
              <div class="section-chip">{{ section.badge }}</div>
              <div class="section-title">{{ section.title }}</div>
              <div class="section-subtitle">{{ section.subtitle }}</div>
            </div>
            <div class="section-metrics">
              <div class="section-metric">
                <span class="section-metric__label">账户数</span>
                <span class="section-metric__value">{{ section.metrics.total }}</span>
              </div>
              <div class="section-metric">
                <span class="section-metric__label">已激活</span>
                <span class="section-metric__value">{{ section.metrics.active }}</span>
              </div>
              <div class="section-metric">
                <span class="section-metric__label">余额合计</span>
                <span class="section-metric__value">¥{{ section.metrics.balance }}</span>
              </div>
              <div class="section-metric">
                <span class="section-metric__label">信用额度</span>
                <span class="section-metric__value">¥{{ section.metrics.credit }}</span>
              </div>
              <div v-if="section.metrics.recentApproved !== undefined" class="section-metric">
                <span class="section-metric__label">近30天审批成员</span>
                <span class="section-metric__value">{{ section.metrics.recentApproved }}</span>
              </div>
            </div>
            <div class="section-actions">
              <el-button link type="primary" @click="toggleSection(section.key)">
                {{ isSectionCollapsed(section.key) ? '展开列表' : '收起列表' }}
              </el-button>
            </div>
          </div>
        </template>

        <el-table
          v-if="!isSectionCollapsed(section.key)"
          v-loading="loading"
          :data="section.data"
          stripe
          border
          style="width: 100%"
        >
          <el-table-column prop="name" label="账户名称" min-width="200" />
          <el-table-column label="类型" width="140">
            <template #default="{ row }">
              <el-tag effect="plain">{{ row.type?.name || getTypeName(row.type_id) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="成员数" width="100">
            <template #default="{ row }">
              {{ (row.member_ids || row.members || []).length }}
            </template>
          </el-table-column>
          <el-table-column label="余额" width="120">
            <template #default="{ row }">
              ¥{{ Number(row.balance || 0).toFixed(2) }}
            </template>
          </el-table-column>
          <el-table-column label="默认预约项目" min-width="180">
            <template #default="{ row }">
              <span>{{ row.default_project_name || '-' }}</span>
              <el-tag v-if="row.project_binding_locked" size="small" type="info" style="margin-left: 8px">
                固定
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="信用额度" width="120">
            <template #default="{ row }">
              ¥{{ Number(row.credit_limit || 0).toFixed(2) }}
            </template>
          </el-table-column>
          <el-table-column label="状态" width="100">
            <template #default="{ row }">
              <el-tag :type="row.active ? 'success' : 'danger'">
                {{ row.active ? '已激活' : '已停用' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="note" label="备注" min-width="220" />

          <el-table-column label="操作" width="320" fixed="right">
            <template #default="{ row }">
              <el-space>
                <el-button size="small" :icon="Edit" @click="handleEdit(row)">账户配置</el-button>
                <el-button
                  v-if="row.active"
                  type="warning"
                  size="small"
                  :icon="Close"
                  :disabled="Boolean(row.project_binding_locked)"
                  @click="handleDeactivate(row)"
                >
                  停用
                </el-button>
                <el-button
                  v-else
                  type="success"
                  size="small"
                  :icon="Check"
                  @click="handleActivate(row)"
                >
                  激活
                </el-button>
                <el-button
                  type="danger"
                  size="small"
                  :icon="Delete"
                  :disabled="Boolean(row.project_binding_locked)"
                  @click="handleDelete(row)"
                >
                  删除
                </el-button>
              </el-space>
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </template>

    <el-card v-else class="empty-card" shadow="never">
      <el-empty description="当前筛选条件下没有账户" />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Refresh, Edit, Delete, Check, Close } from '@element-plus/icons-vue'

import {
  activateAccount,
  deactivateAccount,
  deleteAccount,
  getAccounts,
  getAccountMembershipChangeRequests,
  getAccountTypes,
} from '@/api/accounts'
import type { Account, AccountMembershipChangeRequest, AccountType } from '@/types'

const router = useRouter()

const loading = ref(false)

const tableData = ref<Account[]>([])
const accountTypes = ref<AccountType[]>([])
const approvedMembershipRequests = ref<AccountMembershipChangeRequest[]>([])
const collapsedSections = ref<Record<string, boolean>>({})

const filterTypeId = ref<number>()
const filterActive = ref<boolean>()
const fixedAccounts = computed(() => tableData.value.filter((account) => Boolean(account.project_binding_locked)))
const sharedAccounts = computed(() =>
  tableData.value.filter((account) => !account.project_binding_locked)
)
const recentApprovedCountMap = computed(() => {
  const since = Date.now() - 30 * 24 * 60 * 60 * 1000
  return approvedMembershipRequests.value.reduce<Record<number, number>>((acc, request) => {
    const targetAccountId = request.target_account_id || request.target_account?.id
    const reviewedAt = request.reviewed_at || request.updated_at
    if (!targetAccountId || !reviewedAt) return acc
    const reviewedTime = new Date(reviewedAt).getTime()
    if (Number.isNaN(reviewedTime) || reviewedTime < since) return acc
    acc[targetAccountId] = (acc[targetAccountId] || 0) + 1
    return acc
  }, {})
})
const getSectionMetrics = (accounts: Account[], options?: { includeRecentApproved?: boolean }) => ({
  total: accounts.length,
  active: accounts.filter((account) => Boolean(account.active)).length,
  balance: accounts
    .reduce((sum, account) => sum + Number(account.balance || 0), 0)
    .toFixed(2),
  credit: accounts
    .reduce((sum, account) => sum + Number(account.credit_limit || 0), 0)
    .toFixed(2),
  recentApproved: options?.includeRecentApproved
    ? accounts.reduce((sum, account) => sum + Number(recentApprovedCountMap.value[account.id] || 0), 0)
    : undefined,
})
const accountSections = computed(() => {
  const sections: Array<{
    key: string
    badge: string
    title: string
    subtitle: string
    data: Account[]
    metrics: ReturnType<typeof getSectionMetrics>
  }> = []
  if (fixedAccounts.value.length) {
    sections.push({
      key: 'fixed',
      badge: '默认项目账户',
      title: '固定默认项目账户',
      subtitle: '这类账户由对外开放项目自动绑定，用于承接该项目的默认付款账户。',
      data: fixedAccounts.value,
      metrics: getSectionMetrics(fixedAccounts.value),
    })
  }
  if (sharedAccounts.value.length) {
    sections.push({
      key: 'shared',
      badge: '共享所属账户',
      title: '共享所属账户',
      subtitle: '外部用户审批通过后，可把这里的共享所属账户作为预约结算账户；同一用户可加入多个共享账户。',
      data: sharedAccounts.value,
      metrics: getSectionMetrics(sharedAccounts.value, { includeRecentApproved: true }),
    })
  }
  return sections
})
const filterCountText = computed(() =>
  [`当前 ${tableData.value.length} 个账户`, `固定 ${fixedAccounts.value.length}`, `共享 ${sharedAccounts.value.length}`].join(' / ')
)
const isSectionCollapsed = (key: string) => Boolean(collapsedSections.value[key])
const toggleSection = (key: string) => {
  collapsedSections.value = {
    ...collapsedSections.value,
    [key]: !collapsedSections.value[key]
  }
}

const getErrorDetail = (error: any, fallback: string) =>
  error?.response?.data?.detail || fallback

const loadAccountTypes = async () => {
  try {
    const res = await getAccountTypes()
    accountTypes.value = Array.isArray(res) ? res : (res as any).data || []
  } catch (e) {
    console.error(e)
    ElMessage.error(getErrorDetail(e, '加载账户类型失败'))
  }
}

const loadApprovedMembershipRequests = async () => {
  try {
    const response = await getAccountMembershipChangeRequests({
      status: 'APPROVED',
      limit: 500
    })
    approvedMembershipRequests.value = Array.isArray(response) ? response : (response as any).data || []
  } catch (e) {
    console.error(e)
    ElMessage.error(getErrorDetail(e, '加载所属账户审批统计失败'))
  }
}

const loadAccounts = async () => {
  loading.value = true
  try {
    const params: any = { skip: 0, limit: 1000 }
    if (filterTypeId.value) params.type_id = filterTypeId.value
    if (filterActive.value !== undefined) params.active = filterActive.value
    const res = await getAccounts(params)
    const list = Array.isArray(res) ? res : (res as any).data || []
    tableData.value = list.filter((a: Account) => !a.user_id)
  } catch (e) {
    console.error(e)
    ElMessage.error(getErrorDetail(e, '加载账户列表失败'))
  } finally {
    loading.value = false
  }
}

const handleRefresh = async () => {
  await Promise.all([loadAccounts(), loadApprovedMembershipRequests()])
}

const getTypeName = (typeId?: number | null) => {
  if (!typeId) return '-'
  return accountTypes.value.find((t) => t.id === typeId)?.name || `#${typeId}`
}

const handleCreate = () => {
  router.push({ name: 'AccountCreate' })
}

const handleEdit = (row: Account) => {
  router.push({ name: 'AccountEdit', params: { id: row.id } })
}

const handleActivate = async (row: Account) => {
  try {
    await ElMessageBox.confirm(`确定激活账户 "${row.name}" 吗？`, '提示', { type: 'warning' })
    await activateAccount(row.id)
    ElMessage.success('激活成功')
    await loadAccounts()
  } catch (e) {
    if (e !== 'cancel') {
      console.error(e)
      ElMessage.error(getErrorDetail(e, '激活失败'))
    }
  }
}

const handleDeactivate = async (row: Account) => {
  if (row.project_binding_locked) {
    ElMessage.warning('固定默认项目账户不能停用')
    return
  }
  try {
    await ElMessageBox.confirm(`确定停用账户 "${row.name}" 吗？`, '提示', { type: 'warning' })
    await deactivateAccount(row.id)
    ElMessage.success('停用成功')
    await loadAccounts()
  } catch (e) {
    if (e !== 'cancel') {
      console.error(e)
      ElMessage.error(getErrorDetail(e, '停用失败'))
    }
  }
}

const handleDelete = async (row: Account) => {
  if (row.project_binding_locked) {
    ElMessage.warning('固定默认项目账户不能删除')
    return
  }
  try {
    await ElMessageBox.confirm(`确定删除账户 "${row.name}" 吗？此操作不可恢复。`, '警告', {
      type: 'warning',
      confirmButtonText: '确定删除',
    })
    await deleteAccount(row.id)
    ElMessage.success('删除成功')
    await loadAccounts()
  } catch (e) {
    if (e !== 'cancel') {
      console.error(e)
      ElMessage.error(getErrorDetail(e, '删除失败'))
    }
  }
}

onMounted(async () => {
  await loadAccountTypes()
  await handleRefresh()
})
</script>

<style scoped>
.page-container {
  padding: 20px;
}

.header-card {
  margin-bottom: 16px;
  border-radius: 20px;
  border: none;
  box-shadow: 0 18px 40px rgba(15, 23, 42, 0.06);
}

.header-row,
.filter-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.page-kicker {
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: #2563eb;
  margin-bottom: 10px;
}

.page-title {
  font-size: 28px;
  font-weight: 700;
  color: #0f172a;
  margin-bottom: 8px;
}

.page-subtitle {
  max-width: 820px;
  font-size: 14px;
  line-height: 1.7;
  color: #64748b;
}

.page-alert {
  margin-bottom: 16px;
  border-radius: 18px;
}

.filter-card,
.section-card,
.empty-card {
  border-radius: 20px;
  border: none;
  box-shadow: 0 18px 40px rgba(15, 23, 42, 0.06);
}

.filter-card {
  margin-bottom: 16px;
}

.section-card {
  margin-bottom: 16px;
  overflow: hidden;
  position: relative;
}

.section-card::before {
  content: '';
  position: absolute;
  inset: 0 auto 0 0;
  width: 7px;
}

.section-card--fixed::before {
  background: linear-gradient(180deg, #334155 0%, #1d4ed8 100%);
}

.section-card--shared::before {
  background: linear-gradient(180deg, #16a34a 0%, #0f766e 100%);
}

.section-card--personal::before {
  background: linear-gradient(180deg, #d97706 0%, #ea580c 100%);
}

.filter-meta {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.filter-title {
  font-size: 14px;
  font-weight: 600;
  color: #0f172a;
}

.filter-count {
  font-size: 12px;
  color: #64748b;
}

.section-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
}

.section-header__main {
  max-width: 620px;
}

.section-chip {
  display: inline-flex;
  align-items: center;
  margin-bottom: 10px;
  padding: 6px 10px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #0f172a;
  background: rgba(148, 163, 184, 0.14);
}

.section-card--fixed .section-chip {
  color: #1d4ed8;
  background: rgba(37, 99, 235, 0.12);
}

.section-card--shared .section-chip {
  color: #047857;
  background: rgba(16, 185, 129, 0.14);
}

.section-card--personal .section-chip {
  color: #b45309;
  background: rgba(251, 191, 36, 0.18);
}

.section-title {
  font-size: 16px;
  font-weight: 700;
  color: #0f172a;
}

.section-subtitle {
  margin-top: 6px;
  font-size: 13px;
  line-height: 1.6;
  color: #64748b;
}

.section-metrics {
  display: grid;
  grid-template-columns: repeat(4, minmax(104px, 1fr));
  gap: 10px;
  width: min(100%, 520px);
}

.section-actions {
  display: flex;
  align-items: flex-start;
  justify-content: flex-end;
  min-width: 88px;
}

.section-metric {
  padding: 12px 14px;
  border-radius: 16px;
  background: rgba(248, 250, 252, 0.96);
  border: 1px solid rgba(226, 232, 240, 0.9);
}

.section-card--fixed .section-metric {
  background: rgba(239, 246, 255, 0.86);
  border-color: rgba(147, 197, 253, 0.58);
}

.section-card--shared .section-metric {
  background: rgba(236, 253, 245, 0.92);
  border-color: rgba(110, 231, 183, 0.68);
}

.section-card--personal .section-metric {
  background: rgba(255, 251, 235, 0.95);
  border-color: rgba(253, 186, 116, 0.7);
}

.section-metric__label {
  display: block;
  margin-bottom: 8px;
  font-size: 11px;
  font-weight: 600;
  color: #64748b;
}

.section-metric__value {
  font-size: 18px;
  font-weight: 700;
  color: #0f172a;
}

@media (max-width: 900px) {
  .header-row,
  .filter-row,
  .section-header {
    align-items: stretch;
    flex-direction: column;
  }

  .header-actions {
    justify-content: flex-start;
    flex-wrap: wrap;
  }

  .section-metrics {
    grid-template-columns: repeat(2, minmax(120px, 1fr));
    width: 100%;
  }

  .section-actions {
    justify-content: flex-start;
  }
}

@media (max-width: 640px) {
  .section-metrics {
    grid-template-columns: 1fr;
  }
}
</style>
