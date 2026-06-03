<template>
  <div class="page-container">
    <el-card class="header-card" shadow="never">
      <div class="header-row">
        <div>
          <div class="page-kicker">Billing</div>
          <div class="title">账单详情</div>
          <div class="page-subtitle">{{ pageSubtitle }}</div>
        </div>
        <div class="header-actions">
          <el-button @click="goBack">返回</el-button>
          <el-tag v-if="detail" :type="getStatusType(detail.status)">{{ getStatusLabel(detail.status) }}</el-tag>
        </div>
      </div>
    </el-card>

    <el-card class="content-card" shadow="never" v-loading="loading">
      <template v-if="detail">
        <el-row :gutter="16" class="summary-row">
          <el-col :xs="24" :sm="8">
            <el-card shadow="never" class="summary-card">
              <div class="summary-label">账单金额</div>
              <div class="summary-value">¥{{ Number(detail.total_amount).toFixed(2) }}</div>
            </el-card>
          </el-col>
          <el-col :xs="24" :sm="8">
            <el-card shadow="never" class="summary-card">
              <div class="summary-label">付款账户</div>
              <div class="summary-text">{{ detail.account_name || detail.username || '-' }}</div>
            </el-card>
          </el-col>
          <el-col :xs="24" :sm="8">
            <el-card shadow="never" class="summary-card">
              <div class="summary-label">费用明细条数</div>
              <div class="summary-value">{{ detail.usage_events.length }}</div>
            </el-card>
          </el-col>
        </el-row>

        <el-descriptions title="账单信息" :column="2" border>
          <el-descriptions-item label="账单号">{{ detail.reference_number }}</el-descriptions-item>
          <el-descriptions-item label="金额">¥{{ Number(detail.total_amount).toFixed(2) }}</el-descriptions-item>
          <el-descriptions-item label="付款账户">{{ detail.account_name || detail.username || '-' }}</el-descriptions-item>
          <el-descriptions-item label="生成时间">{{ formatDateTime(detail.issued_date) }}</el-descriptions-item>
          <el-descriptions-item label="到期时间">{{ formatDateTime(detail.due_date) }}</el-descriptions-item>
        </el-descriptions>

        <el-divider />

        <el-descriptions v-if="detail.user" title="账户归属用户" :column="2" border>
          <template v-if="detail.user">
            <el-descriptions-item label="用户ID">{{ detail.user.id }}</el-descriptions-item>
            <el-descriptions-item label="用户名">{{ detail.user.username }}</el-descriptions-item>
            <el-descriptions-item label="姓名">{{ detail.user.last_name }}{{ detail.user.first_name }}</el-descriptions-item>
            <el-descriptions-item label="邮箱">{{ detail.user.email }}</el-descriptions-item>
          </template>
        </el-descriptions>

        <el-alert
          v-else
          class="account-alert"
          type="info"
          :closable="false"
          show-icon
          title="这是一张共享所属账户账单，账单归属于账户本身，不绑定单一用户。"
        />

        <el-divider />

        <div class="section-title">{{ authStore.isStaff() ? '关联使用记录' : '费用明细' }}</div>
        <el-table v-if="authStore.isStaff()" :data="detail.usage_events" stripe border style="width: 100%">
          <el-table-column label="仪器" min-width="160">
            <template #default="{ row }">
              {{ row.tool?.name || `#${row.tool_id}` }}
            </template>
          </el-table-column>
          <el-table-column label="项目" min-width="160">
            <template #default="{ row }">
              {{ row.project?.name || `#${row.project_id}` }}
            </template>
          </el-table-column>
          <el-table-column label="开始时间" width="180">
            <template #default="{ row }">
              {{ formatDateTime(row.start) }}
            </template>
          </el-table-column>
          <el-table-column label="结束时间" width="180">
            <template #default="{ row }">
              {{ formatDateTime(row.end) }}
            </template>
          </el-table-column>
          <el-table-column label="时长" width="120">
            <template #default="{ row }">
              {{ getDurationLabel(row.start, row.end) }}
            </template>
          </el-table-column>
          <el-table-column prop="amount" label="费用" width="120">
            <template #default="{ row }">
              ¥{{ Number(row.amount || 0).toFixed(2) }}
            </template>
          </el-table-column>
          <el-table-column label="状态" width="90">
            <template #default="{ row }">
              <el-tag v-if="row.waived" type="info">已豁免</el-tag>
              <el-tag v-else :type="row.validated ? 'success' : 'warning'">
                {{ row.validated ? '已结算' : '待结算' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="note" label="备注" min-width="200" />
        </el-table>
        <div v-else-if="usageItems.length" class="fee-item-list">
          <div v-for="item in usageItems" :key="item.id" class="fee-item-card">
            <div class="fee-item-top">
              <div class="fee-item-main">
                <div class="fee-item-title">{{ item.toolName }}</div>
                <div class="fee-item-time">{{ item.timeRange }}</div>
              </div>
              <div class="fee-item-amount">¥{{ item.amount }}</div>
            </div>
            <div class="fee-item-meta">
              <el-tag size="small" effect="plain">{{ item.duration }}</el-tag>
              <el-tag v-if="item.projectName" size="small" type="info" effect="plain">
                {{ item.projectName }}
              </el-tag>
              <el-tag v-if="item.waived" size="small" type="info">已豁免</el-tag>
              <el-tag v-else size="small" :type="item.validated ? 'success' : 'warning'">
                {{ item.validated ? '已结算' : '待结算' }}
              </el-tag>
            </div>
            <div v-if="item.note" class="fee-item-note">{{ item.note }}</div>
          </div>
        </div>
        <el-empty v-else description="暂无费用明细" />
      </template>
      <template v-else>
        <div>暂无数据</div>
      </template>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

import { getBillDetail } from '@/api/billing'
import type { BillDetail } from '@/types'
import { formatDateTime } from '@/utils/date'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const loading = ref(false)
const detail = ref<BillDetail | null>(null)
const getErrorDetail = (error: any, fallback: string) =>
  error?.response?.data?.detail || fallback
const pageSubtitle = computed(() =>
  authStore.isStaff()
    ? '查看当前项目范围内账单及其关联使用记录。'
    : '查看你当前可访问账户下的账单明细与费用构成。'
)
const usageItems = computed(() =>
  (detail.value?.usage_events || []).map((row) => ({
    id: row.id,
    toolName: row.tool?.name || `仪器 #${row.tool_id}`,
    projectName: row.project?.name || '',
    timeRange: getTimeRangeLabel(row.start, row.end),
    duration: getDurationLabel(row.start, row.end),
    amount: Number(row.amount || 0).toFixed(2),
    validated: Boolean(row.validated),
    waived: Boolean(row.waived),
    note: row.note || '',
  }))
)

const getStatusType = (status: string) => {
  switch (status) {
    case 'PAID':
      return 'success'
    case 'ISSUED':
      return 'primary'
    case 'CANCELLED':
      return 'info'
    default:
      return 'warning'
  }
}

const getStatusLabel = (status: string) => {
  switch (status) {
    case 'DRAFT':
      return '草稿'
    case 'ISSUED':
      return '已开出'
    case 'PAID':
      return '已支付'
    case 'CANCELLED':
      return '已取消'
    default:
      return status
  }
}

const getTimeRangeLabel = (start?: string, end?: string) => {
  if (!start && !end) return '-'
  if (!end) return `${formatDateTime(start)} 开始`
  return `${formatDateTime(start)} - ${formatDateTime(end)}`
}

const getDurationLabel = (start?: string, end?: string) => {
  if (!start || !end) return '-'
  const startDate = new Date(start)
  const endDate = new Date(end)
  if (Number.isNaN(startDate.getTime()) || Number.isNaN(endDate.getTime())) return '-'
  const totalMinutes = Math.max(0, Math.round((endDate.getTime() - startDate.getTime()) / 60000))
  if (totalMinutes < 60) return `${totalMinutes} 分钟`
  const hours = Math.floor(totalMinutes / 60)
  const minutes = totalMinutes % 60
  return minutes ? `${hours} 小时 ${minutes} 分钟` : `${hours} 小时`
}

const loadDetail = async () => {
  const billId = Number(route.params.id)
  if (!billId) {
    ElMessage.error('账单ID无效')
    return
  }

  loading.value = true
  try {
    const res = await getBillDetail(billId)
    detail.value = ((res as any)?.data || res) || null
  } catch (e) {
    console.error(e)
    ElMessage.error(getErrorDetail(e, '加载账单详情失败'))
  } finally {
    loading.value = false
  }
}

const goBack = () => {
  router.push({ name: 'Billing' })
}

onMounted(() => {
  loadDetail()
})
</script>

<style scoped>
.page-container {
  padding: 20px;
}

.header-card,
.content-card {
  border-radius: 20px;
  border: none;
  box-shadow: 0 18px 40px rgba(15, 23, 42, 0.06);
}

.header-row {
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
  margin-bottom: 8px;
}

.title {
  font-size: 28px;
  font-weight: 700;
  color: #0f172a;
}

.page-subtitle {
  margin-top: 8px;
  font-size: 14px;
  color: #64748b;
  line-height: 1.7;
}

.section-title {
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 12px;
}

.content-card {
  margin-top: 16px;
}

.summary-row {
  margin: 0 0 16px;
}

.summary-card {
  border-radius: 18px;
  border: 1px solid #e2e8f0;
  box-shadow: none;
}

.summary-label {
  font-size: 12px;
  color: #64748b;
  margin-bottom: 10px;
}

.summary-value {
  font-size: 26px;
  font-weight: 700;
  color: #0f172a;
}

.summary-text {
  font-size: 16px;
  font-weight: 600;
  color: #0f172a;
  word-break: break-word;
}

.account-alert {
  border-radius: 16px;
}

.fee-item-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.fee-item-card {
  border: 1px solid #e2e8f0;
  border-radius: 18px;
  padding: 18px 20px;
  background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
}

.fee-item-top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.fee-item-main {
  min-width: 0;
}

.fee-item-title {
  font-size: 17px;
  font-weight: 700;
  color: #0f172a;
}

.fee-item-time {
  margin-top: 6px;
  font-size: 13px;
  color: #64748b;
  line-height: 1.6;
}

.fee-item-amount {
  flex: 0 0 auto;
  font-size: 22px;
  font-weight: 700;
  color: #0f172a;
}

.fee-item-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  margin-top: 14px;
}

.fee-item-note {
  margin-top: 12px;
  font-size: 13px;
  line-height: 1.6;
  color: #475569;
  padding-top: 12px;
  border-top: 1px solid #e2e8f0;
}

@media (max-width: 768px) {
  .header-row {
    align-items: stretch;
    flex-direction: column;
  }

  .header-actions {
    justify-content: flex-start;
  }

  .fee-item-top {
    flex-direction: column;
  }
}
</style>
