<template>
  <div class="page-container">
    <el-card class="header-card" shadow="never">
      <div class="header-row">
        <div>
          <div class="page-kicker">Billing</div>
          <div class="page-title">{{ pageTitle }}</div>
          <div class="page-subtitle">{{ pageSubtitle }}</div>
        </div>
        <div class="header-actions">
          <el-button 
            v-if="authStore.isStaff()"
            type="primary" 
            :icon="DocumentAdd" 
            @click="handleOpenGenerate"
          >
            生成账单
          </el-button>
          <el-button :icon="Refresh" @click="loadBills">
            刷新
          </el-button>
        </div>
      </div>
    </el-card>

    <el-alert
      class="page-alert"
      :title="pageAlert"
      type="info"
      :closable="false"
      show-icon
    />

    <el-card class="filter-card" shadow="never">
      <div class="filter-row">
        <div class="filter-meta">
          <span class="filter-title">状态筛选</span>
          <span class="filter-count">当前展示 {{ filteredBills.length }} / {{ tableData.length }} 张账单</span>
        </div>
        <el-select
          v-model="statusFilter"
          clearable
          placeholder="全部状态"
          class="status-select"
        >
          <el-option label="全部状态" value="" />
          <el-option
            v-for="option in statusOptions"
            :key="option.value"
            :label="option.label"
            :value="option.value"
          />
        </el-select>
      </div>
    </el-card>

    <el-row :gutter="16" class="summary-row">
      <el-col :xs="24" :sm="8">
        <el-card shadow="never" class="summary-card">
          <div class="summary-label">账单数量</div>
          <div class="summary-value">{{ filteredBills.length }}</div>
        </el-card>
      </el-col>
      <el-col :xs="24" :sm="8">
        <el-card shadow="never" class="summary-card">
          <div class="summary-label">账单总额</div>
          <div class="summary-value">¥{{ totalAmount }}</div>
        </el-card>
      </el-col>
      <el-col :xs="24" :sm="8">
        <el-card shadow="never" class="summary-card">
          <div class="summary-label">{{ authStore.isStaff() ? '已开出账单' : '已支付账单' }}</div>
          <div class="summary-value">{{ authStore.isStaff() ? issuedCount : paidCount }}</div>
        </el-card>
      </el-col>
    </el-row>

    <el-card class="table-card" shadow="never">
      <el-table
        v-if="authStore.isStaff()"
        v-loading="loading"
        :data="filteredBills"
        stripe
        border
        :empty-text="emptyText"
        style="width: 100%"
      >
        <el-table-column prop="reference_number" label="账单号" min-width="180">
          <template #default="{ row }">
            <el-button link type="primary" @click="goDetail(row)">
              {{ row.reference_number }}
            </el-button>
          </template>
        </el-table-column>
        <el-table-column :label="accountColumnLabel" min-width="180">
          <template #default="{ row }">
            {{ getAccountDisplayName(row) }}
          </template>
        </el-table-column>
        <el-table-column prop="total_amount" label="金额" width="120">
          <template #default="{ row }">
            ¥{{ Number(row.total_amount).toFixed(2) }}
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)">{{ getStatusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="生成时间" width="180">
          <template #default="{ row }">
            {{ formatDateTime(row.issued_date) }}
          </template>
        </el-table-column>

        <el-table-column v-if="authStore.isStaff()" label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="goDetail(row)">详情</el-button>
            <el-button size="small" @click="handleOpenEdit(row)">编辑</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div v-else v-loading="loading" class="bill-card-list">
        <template v-if="filteredBills.length">
          <div
            v-for="bill in filteredBills"
            :key="bill.id"
            :class="['bill-list-card', `bill-list-card--${bill.status.toLowerCase()}`]"
            role="button"
            tabindex="0"
            @click="goDetail(bill)"
            @keydown.enter.prevent="goDetail(bill)"
            @keydown.space.prevent="goDetail(bill)"
          >
            <div class="bill-list-card__header">
              <div>
                <div class="bill-list-card__ref">{{ bill.reference_number }}</div>
                <div class="bill-list-card__account">{{ getAccountDisplayName(bill) }}</div>
              </div>
              <el-tag :type="getStatusType(bill.status)">{{ getStatusLabel(bill.status) }}</el-tag>
            </div>
            <div class="bill-list-card__body">
              <div class="bill-list-card__amount">¥{{ Number(bill.total_amount).toFixed(2) }}</div>
              <div class="bill-list-card__period">{{ getPeriodLabel(bill) }}</div>
            </div>
            <div class="bill-list-card__meta">
              <span>生成于 {{ formatDateTime(bill.issued_date) }}</span>
              <span>到期 {{ bill.due_date ? formatDateTime(bill.due_date) : '未设置' }}</span>
            </div>
            <div class="bill-list-card__footer">
              <span class="bill-list-card__hint">查看费用明细</span>
              <el-button link type="primary" @click.stop="goDetail(bill)">查看详情</el-button>
            </div>
          </div>
        </template>
        <el-empty v-else :description="emptyText" />
      </div>
    </el-card>

    <!-- 生成账单对话框 -->
    <el-dialog
      v-model="dialogVisible"
      title="生成账单"
      width="500px"
      @close="resetForm"
    >
      <div>将历史所有未结算账单按用户合并，并把已验证但未出账的使用记录金额加入账单。</div>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" :loading="submitting" @click="handleSubmit">
            生成
          </el-button>
        </span>
      </template>
    </el-dialog>

    <!-- 编辑账单对话框 (管理员) -->
    <el-dialog
      v-model="editDialogVisible"
      title="编辑账单"
      width="500px"
      @close="resetEditForm"
    >
      <el-form
        ref="editFormRef"
        :model="editFormData"
        label-width="100px"
      >
        <el-form-item label="状态">
          <el-select v-model="editFormData.status" placeholder="选择状态" style="width: 100%">
            <el-option label="DRAFT" value="DRAFT" />
            <el-option label="ISSUED" value="ISSUED" />
            <el-option label="PAID" value="PAID" />
            <el-option label="CANCELLED" value="CANCELLED" />
          </el-select>
        </el-form-item>

        <el-form-item label="到期时间">
          <el-date-picker
            v-model="editFormData.due_date"
            type="datetime"
            placeholder="选择到期时间"
            value-format="YYYY-MM-DD HH:mm:ss"
            style="width: 100%"
            clearable
          />
        </el-form-item>
      </el-form>

      <template #footer>
        <span class="dialog-footer">
          <el-button @click="editDialogVisible = false">取消</el-button>
          <el-button type="primary" :loading="editSubmitting" @click="handleEditSubmit">保存</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { DocumentAdd, Refresh } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import type { FormInstance } from 'element-plus'
import { getBills, generateBills, updateBill } from '@/api/billing'
import type { Bill } from '@/types'
import { formatDateTime } from '@/utils/date'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()
const router = useRouter()
const loading = ref(false)
const submitting = ref(false)
const tableData = ref<Bill[]>([])
const statusFilter = ref('')
const pageTitle = computed(() => (authStore.isStaff() ? '账单管理' : '我的账单'))
const pageSubtitle = computed(() =>
  authStore.isStaff()
    ? '仅展示当前项目范围内的账单，支持统一生成与编辑。'
    : '展示你个人账户和已生效所属账户下可访问的账单。'
)
const pageAlert = computed(() =>
  authStore.isStaff()
    ? '管理员视角下，账单仍按当前项目范围管理。'
    : '所属账户审批通过后，该账户对应的账单会出现在这里。'
)
const accountColumnLabel = computed(() => (authStore.isStaff() ? '付款账户' : '我的账户'))
const emptyText = computed(() =>
  authStore.isStaff() ? '当前项目下暂无账单' : '当前没有可查看的账单'
)
const statusOptions = [
  { label: '草稿', value: 'DRAFT' },
  { label: '已开出', value: 'ISSUED' },
  { label: '已支付', value: 'PAID' },
  { label: '已取消', value: 'CANCELLED' },
]
const filteredBills = computed(() =>
  statusFilter.value
    ? tableData.value.filter((item) => item.status === statusFilter.value)
    : tableData.value
)
const totalAmount = computed(() =>
  filteredBills.value.reduce((sum, item) => sum + Number(item.total_amount || 0), 0).toFixed(2)
)
const issuedCount = computed(() =>
  filteredBills.value.filter((item) => ['ISSUED', 'PAID'].includes(item.status)).length
)
const paidCount = computed(() =>
  filteredBills.value.filter((item) => item.status === 'PAID').length
)

const dialogVisible = ref(false)
const formRef = ref<FormInstance>()

const editDialogVisible = ref(false)
const editSubmitting = ref(false)
const editFormRef = ref<FormInstance>()
const editFormData = reactive({
  id: 0,
  status: '' as string,
  due_date: null as string | null
})

const unwrapArray = <T,>(response: any): T[] => {
  if (Array.isArray(response)) return response
  return response?.data || []
}

const getErrorDetail = (error: any, fallback: string) =>
  error?.response?.data?.detail || fallback

// 加载账单
const loadBills = async () => {
  loading.value = true
  try {
    const res = await getBills({
      skip: 0,
      limit: 100
    })
    tableData.value = unwrapArray<Bill>(res)
  } catch (error) {
    console.error(error)
    ElMessage.error(getErrorDetail(error, '加载账单失败'))
  } finally {
    loading.value = false
  }
}

const getStatusType = (status: string) => {
  switch (status) {
    case 'PAID': return 'success'
    case 'ISSUED': return 'primary'
    case 'CANCELLED': return 'info'
    default: return 'warning'
  }
}

const getStatusLabel = (status: string) => {
  switch (status) {
    case 'DRAFT': return '草稿'
    case 'ISSUED': return '已开出'
    case 'PAID': return '已支付'
    case 'CANCELLED': return '已取消'
    default: return status
  }
}

const getAccountDisplayName = (bill: Bill) =>
  bill.account_name || bill.username || (bill.user_id ? `#${bill.user_id}` : '-')

const getPeriodLabel = (bill: Bill) => {
  if (bill.period_start && bill.period_end) {
    return `${formatDateTime(bill.period_start)} 至 ${formatDateTime(bill.period_end)}`
  }
  if (bill.period_start) return `${formatDateTime(bill.period_start)} 开始`
  return '未设置计费周期'
}

const handleOpenGenerate = () => {
  dialogVisible.value = true
}

const handleOpenEdit = (bill: Bill) => {
  editFormData.id = bill.id
  editFormData.status = bill.status
  editFormData.due_date = bill.due_date || null
  editDialogVisible.value = true
}

const goDetail = (bill: Bill) => {
  router.push({ name: 'BillDetail', params: { id: bill.id } })
}

const resetForm = () => {
  if (formRef.value) formRef.value.resetFields()
}

const resetEditForm = () => {
  editFormData.id = 0
  editFormData.status = ''
  editFormData.due_date = null
}

const handleSubmit = async () => {
  submitting.value = true
  try {
    await generateBills({})
    ElMessage.success('账单生成成功')
    dialogVisible.value = false
    loadBills()
  } catch (error) {
    console.error(error)
    ElMessage.error(getErrorDetail(error, '账单生成失败'))
  } finally {
    submitting.value = false
  }
}

const handleEditSubmit = async () => {
  if (!authStore.isStaff()) {
    ElMessage.error('仅管理员可编辑账单')
    return
  }
  if (!editFormData.id) return

  editSubmitting.value = true
  try {
    await updateBill(editFormData.id, {
      status: editFormData.status,
      due_date: editFormData.due_date
    })
    ElMessage.success('账单更新成功')
    editDialogVisible.value = false
    loadBills()
  } catch (error) {
    console.error(error)
    ElMessage.error(getErrorDetail(error, '账单更新失败'))
  } finally {
    editSubmitting.value = false
  }
}

onMounted(() => {
  loadBills()
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
  margin-bottom: 10px;
}

.page-title {
  font-size: 28px;
  font-weight: 700;
  color: #0f172a;
  margin-bottom: 8px;
}

.page-subtitle {
  font-size: 14px;
  color: #64748b;
  line-height: 1.7;
}

.page-alert {
  margin-bottom: 16px;
  border-radius: 18px;
}

.filter-card,
.summary-card,
.table-card {
  border-radius: 20px;
  border: none;
  box-shadow: 0 18px 40px rgba(15, 23, 42, 0.06);
}

.filter-card {
  margin-bottom: 16px;
}

.filter-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
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

.status-select {
  width: 180px;
}

.summary-row {
  margin: 0 0 16px;
}

.table-card {
  overflow: hidden;
}

.summary-label {
  font-size: 13px;
  color: #64748b;
  margin-bottom: 14px;
}

.summary-value {
  font-size: 28px;
  font-weight: 700;
  color: #0f172a;
}

.bill-card-list {
  display: grid;
  gap: 14px;
}

.bill-list-card {
  width: 100%;
  border: 1px solid rgba(148, 163, 184, 0.18);
  border-radius: 20px;
  background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
  padding: 18px 20px;
  text-align: left;
  cursor: pointer;
  transition: transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease;
}

.bill-list-card:hover {
  transform: translateY(-1px);
  box-shadow: 0 18px 34px rgba(15, 23, 42, 0.08);
}

.bill-list-card--draft {
  border-left: 5px solid #f59e0b;
}

.bill-list-card--issued {
  border-left: 5px solid #2563eb;
}

.bill-list-card--paid {
  border-left: 5px solid #16a34a;
}

.bill-list-card--cancelled {
  border-left: 5px solid #94a3b8;
}

.bill-list-card__header,
.bill-list-card__footer,
.bill-list-card__meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.bill-list-card__header {
  margin-bottom: 16px;
}

.bill-list-card__ref {
  font-size: 16px;
  font-weight: 700;
  color: #0f172a;
}

.bill-list-card__account {
  margin-top: 6px;
  font-size: 13px;
  color: #64748b;
}

.bill-list-card__body {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 12px;
}

.bill-list-card__amount {
  font-size: 30px;
  font-weight: 800;
  color: #0f172a;
  line-height: 1;
}

.bill-list-card__period {
  max-width: 340px;
  font-size: 13px;
  text-align: right;
  line-height: 1.6;
  color: #475569;
}

.bill-list-card__meta {
  padding-top: 12px;
  border-top: 1px solid rgba(226, 232, 240, 0.9);
  font-size: 12px;
  color: #64748b;
}

.bill-list-card__footer {
  margin-top: 10px;
}

.bill-list-card__hint {
  font-size: 12px;
  font-weight: 600;
  color: #94a3b8;
}

@media (max-width: 768px) {
  .header-row,
  .filter-row {
    align-items: stretch;
    flex-direction: column;
  }

  .header-actions {
    justify-content: flex-start;
    flex-wrap: wrap;
  }

  .bill-list-card {
    padding: 16px;
  }

  .bill-list-card__body,
  .bill-list-card__meta,
  .bill-list-card__footer {
    align-items: flex-start;
    flex-direction: column;
  }

  .bill-list-card__period {
    max-width: none;
    text-align: left;
  }

  .status-select {
    width: 100%;
  }
}
</style>
