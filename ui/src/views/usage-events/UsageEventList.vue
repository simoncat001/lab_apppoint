<template>
  <div class="page-container">
    <!-- 顶部操作栏 -->
    <el-card class="header-card" shadow="never">
      <el-row :gutter="16" align="middle">
        <el-col :span="12">
          <el-space>
            <el-button :icon="Refresh" @click="loadUsageEvents">
              刷新
            </el-button>
            <el-button :icon="Histogram" @click="showStats = !showStats">
              {{ showStats ? '隐藏' : '显示' }}统计
            </el-button>
          </el-space>
        </el-col>
        <el-col :span="12" style="text-align: right">
          <el-space>
            <el-select
              v-if="authStore.isStaff()"
              v-model="filterUserId"
              placeholder="预约用户"
              clearable
              filterable
              style="width: 140px"
              @change="handleFilterChange"
            >
              <el-option
                v-for="u in users"
                :key="u.id"
                :label="u.username"
                :value="u.id"
              />
            </el-select>

            <el-select
              v-model="filterCategoryId"
              placeholder="分类"
              clearable
              style="width: 140px"
              @change="handleFilterChange"
            >
              <el-option
                v-for="c in categories"
                :key="c.id"
                :label="c.name"
                :value="c.id"
              />
            </el-select>

            <el-select
              v-model="filterToolId"
              placeholder="仪器"
              clearable
              filterable
              style="width: 160px"
              @change="handleFilterChange"
            >
              <el-option
                v-for="tool in filteredTools"
                :key="tool.id"
                :label="tool.name"
                :value="tool.id"
              />
            </el-select>

            <el-date-picker
              v-model="dateRange"
              type="daterange"
              range-separator="至"
              start-placeholder="开始日期"
              end-placeholder="结束日期"
              value-format="YYYY-MM-DD"
              @change="handleFilterChange"
            />

            <el-select
              v-model="filterStatus"
              placeholder="状态"
              clearable
              style="width: 140px"
              @change="handleFilterChange"
            >
              <el-option
                v-for="option in statusOptions"
                :key="option.value"
                :label="option.label"
                :value="option.value"
              />
            </el-select>
          </el-space>
        </el-col>
      </el-row>
    </el-card>

    <!-- 统计卡片 -->
    <el-row v-if="showStats" :gutter="16" class="stats-row">
      <el-col :xs="24" :sm="12" :lg="6">
        <el-card shadow="hover">
          <div class="stat-card">
            <div class="stat-icon" style="background: #409eff">
              <el-icon :size="32"><Document /></el-icon>
            </div>
            <div class="stat-content">
              <div class="stat-value">{{ stats.total_count }}</div>
              <div class="stat-label">总记录数</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :xs="24" :sm="12" :lg="6">
        <el-card shadow="hover">
          <div class="stat-card">
            <div class="stat-icon" style="background: #67c23a">
              <el-icon :size="32"><Check /></el-icon>
            </div>
            <div class="stat-content">
              <div class="stat-value">{{ stats.validated_count }}</div>
              <div class="stat-label">已确认</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :xs="24" :sm="12" :lg="6">
        <el-card shadow="hover">
          <div class="stat-card">
            <div class="stat-icon" style="background: #e6a23c">
              <el-icon :size="32"><Clock /></el-icon>
            </div>
            <div class="stat-content">
              <div class="stat-value">{{ stats.pending_count }}</div>
              <div class="stat-label">待确认</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :xs="24" :sm="12" :lg="6">
        <el-card shadow="hover">
          <div class="stat-card">
            <div class="stat-icon" style="background: #f56c6c">
              <el-icon :size="32"><Coin /></el-icon>
            </div>
            <div class="stat-content">
              <div class="stat-value">{{ formatCurrency(stats.charged_total_amount) }}</div>
              <div class="stat-label">收费总额</div>
              <div class="stat-sub">已扣费记录：{{ stats.charged_count }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :xs="24" :sm="12" :lg="6">
        <el-card shadow="hover">
          <div class="stat-card">
            <div class="stat-icon" style="background: #909399">
              <el-icon :size="32"><Timer /></el-icon>
            </div>
            <div class="stat-content">
              <div class="stat-value">{{ formatDuration(stats.total_duration_minutes) }}</div>
              <div class="stat-label">总使用时长</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 数据表格 -->
    <el-card class="table-card" shadow="never">
      <el-table
        v-loading="loading"
        :data="tableData"
        stripe
        border
        style="width: 100%"
      >
        <el-table-column label="仪器" min-width="150">
          <template #default="{ row }">
            {{ row.tool?.name || '-' }}
          </template>
        </el-table-column>
        <el-table-column label="预约用户" width="120">
          <template #default="{ row }">
            {{ row.user?.username || '-' }}
          </template>
        </el-table-column>
        <el-table-column label="项目" min-width="150">
          <template #default="{ row }">
            {{ row.project?.name || '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="start" label="开始时间" width="180">
          <template #default="{ row }">
            {{ formatDateTime(row.start) }}
          </template>
        </el-table-column>
        <el-table-column prop="end" label="结束时间" width="180">
          <template #default="{ row }">
            {{ row.end ? formatDateTime(row.end) : '使用中' }}
          </template>
        </el-table-column>
        <el-table-column label="时长" width="120">
          <template #default="{ row }">
            <span v-if="row.end">
              {{ formatDuration(calcDuration(row.start, row.end)) }}
            </span>
            <el-tag v-else type="success" effect="dark">使用中</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="费用" width="100">
          <template #default="{ row }">
            <span v-if="row.amount !== undefined">¥{{ Number(row.amount).toFixed(2) }}</span>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="120">
          <template #default="{ row }">
            <el-tag :type="getStatusTagType(row)">{{ getStatusLabel(row) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="320" fixed="right">
          <template #default="{ row }">
            <el-space>
              <el-button
                v-if="!row.end"
                type="warning"
                size="small"
                :icon="Close"
                @click="handleEnd(row)"
              >
                结束
              </el-button>
              <el-button
                v-if="canValidate(row)"
                type="success"
                size="small"
                :icon="Check"
                @click="handleValidate(row)"
              >
                确认扣费
              </el-button>
              <el-button
                v-if="canWaive(row)"
                type="info"
                size="small"
                @click="handleWaive(row)"
              >
                豁免
              </el-button>
              <el-button
                v-else-if="canReactivate(row)"
                type="success"
                size="small"
                @click="handleReactivate(row)"
              >
                激活
              </el-button>
              <el-button
                type="primary"
                size="small"
                :icon="Edit"
                @click="handleEdit(row)"
              >
                编辑
              </el-button>
              <el-button
                type="danger"
                size="small"
                :icon="Delete"
                @click="handleDelete(row)"
              >
                删除
              </el-button>
            </el-space>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination-container">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :total="total"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="loadUsageEvents"
          @current-change="loadUsageEvents"
        />
      </div>
    </el-card>

    <!-- 创建/编辑对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogTitle"
      width="600px"
      @close="resetForm"
    >
        <el-form
          ref="formRef"
          :model="formData"
          :rules="formRules"
          label-width="100px"
        >
          <el-form-item label="仪器" prop="tool_id">
          <el-input :model-value="selectedToolLabel" readonly />
          </el-form-item>
          <el-form-item label="用户" prop="user_id">
          <el-input :model-value="selectedUserLabel" readonly />
          </el-form-item>
          <el-form-item label="开始时间" prop="start">
          <el-input :model-value="formatDateTime(formData.start as string)" readonly />
          </el-form-item>
        <el-form-item label="实际时长" prop="actual_duration_minutes">
          <el-input-number
            v-model="formData.actual_duration_minutes"
            :min="1"
            :step="5"
            controls-position="right"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="自动结束时间">
          <el-input :model-value="calculatedEndLabel" readonly />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">
          确定
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import {
  Refresh,
  Edit,
  Delete,
  Check,
  Close,
  Histogram,
  Document,
  Clock,
  Timer,
  Coin
} from '@element-plus/icons-vue'
import {
  getUsageEvents,
  updateUsageEvent,
  deleteUsageEvent,
  endUsageEvent,
  validateUsageEvent,
  waiveUsageEvent,
  reactivateUsageEvent,
  getUsageEventStats
} from '@/api/usage-events'
import { getTools, getToolCategories } from '@/api/tools'
import { getUsers } from '@/api/users'
import type { UsageEvent, UsageEventStats, Tool, User, ToolCategory } from '@/types'
import { formatDateTime, calcDuration, formatDuration } from '@/utils/helpers'
import { useAuthStore } from '@/stores/auth'

// 数据列表
const loading = ref(false)
const tableData = ref<UsageEvent[]>([])

const authStore = useAuthStore()
type UsageEventFilterStatus = 'pending' | 'charged' | 'waived' | 'in_progress'

// 筛选选项
const tools = ref<Tool[]>([])
const users = ref<User[]>([])
const categories = ref<ToolCategory[]>([])

// 统计数据
const showStats = ref(true)
const stats = ref<UsageEventStats>({
  total_count: 0,
  total_duration_minutes: 0,
  average_duration_minutes: 0,
  validated_count: 0,
  pending_count: 0,
  charged_count: 0,
  charged_total_amount: 0,
  by_tool: {},
  by_user: {}
})

// 过滤器
const filterStatus = ref<UsageEventFilterStatus>()
const filterUserId = ref<number>()
const filterToolId = ref<number>()
const filterCategoryId = ref<number>()
const dateRange = ref<[string, string]>()
const statusOptions: Array<{ label: string; value: UsageEventFilterStatus }> = [
  { label: '使用中', value: 'in_progress' },
  { label: '待确认', value: 'pending' },
  { label: '已确认扣费', value: 'charged' },
  { label: '已豁免', value: 'waived' },
]

const filteredTools = computed(() => {
  if (!filterCategoryId.value) return tools.value
  return tools.value.filter(
    (tool) => (tool.category?.id ?? tool.category_id) === filterCategoryId.value
  )
})

// 分页
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)

// 对话框
const dialogVisible = ref(false)
const dialogMode = ref<'create' | 'edit'>('edit')
const dialogTitle = computed(() => (dialogMode.value === 'create' ? '创建使用记录' : '编辑使用记录'))
const submitting = ref(false)

// 表单
const formRef = ref<FormInstance>()
const formData = reactive<Partial<UsageEvent>>({
  tool_id: undefined,
  user_id: undefined,
  start: undefined,
  end: undefined,
  actual_duration_minutes: undefined
})

const formRules: FormRules = {
  tool_id: [{ required: true, message: '缺少仪器信息', trigger: 'change' }],
  user_id: [{ required: true, message: '缺少用户信息', trigger: 'change' }],
  start: [{ required: true, message: '缺少开始时间', trigger: 'change' }],
  actual_duration_minutes: [{ required: true, message: '请输入实际时长', trigger: 'change' }]
}

const selectedToolLabel = computed(() => {
  const tool = tools.value.find((item) => item.id === formData.tool_id)
  return tool?.name || (formData.tool_id ? `仪器 #${formData.tool_id}` : '')
})

const selectedUserLabel = computed(() => {
  const user = users.value.find((item) => item.id === formData.user_id)
  return user?.username || (formData.user_id ? `用户 #${formData.user_id}` : '')
})

const calculatedEndLabel = computed(() => {
  if (!formData.start || !formData.actual_duration_minutes) return '-'
  const end = new Date(new Date(formData.start).getTime() + Number(formData.actual_duration_minutes) * 60 * 1000)
  return formatDateTime(end.toISOString())
})

const formatCurrency = (value: number) => `¥${Number(value || 0).toFixed(2)}`

const buildDateRangeParams = () => {
  if (!dateRange.value?.length) {
    return {}
  }
  return {
    start_date: `${dateRange.value[0]} 00:00:00`,
    end_date: `${dateRange.value[1]} 23:59:59`,
  }
}

const getStatusKey = (row: UsageEvent): UsageEventFilterStatus => {
  if (!row.end) return 'in_progress'
  if (row.waived) return 'waived'
  if (row.validated) return 'charged'
  return 'pending'
}

const getStatusLabel = (row: UsageEvent) => {
  const status = getStatusKey(row)
  if (status === 'in_progress') return '使用中'
  if (status === 'waived') return '已豁免'
  if (status === 'charged') return '已确认扣费'
  return '待确认'
}

const getStatusTagType = (row: UsageEvent) => {
  const status = getStatusKey(row)
  if (status === 'in_progress') return 'info'
  if (status === 'waived') return 'info'
  if (status === 'charged') return 'success'
  return 'warning'
}

const canValidate = (row: UsageEvent) => Boolean(row.end && !row.validated && !row.waived)
const canWaive = (row: UsageEvent) => Boolean(row.end && !row.waived)
const canReactivate = (row: UsageEvent) => Boolean(row.end && row.waived)

// 加载统计数据
const loadStats = async (params?: {
  tool_id?: number
  user_id?: number
  category_id?: number
  status?: UsageEventFilterStatus
  start_date?: string
  end_date?: string
}) => {
  try {
    const response = await getUsageEventStats(params)
    stats.value = response || stats.value
  } catch (error) {
    console.error('加载统计数据失败:', error)
  }
}

const loadTools = async () => {
  try {
    const response = await getTools({ skip: 0, limit: 1000 })
    tools.value = Array.isArray(response) ? response : (response as any).data || []
  } catch (error) {
    console.error('加载仪器列表失败:', error)
  }
}

const loadCategories = async () => {
  try {
    categories.value = await getToolCategories()
  } catch (error) {
    console.error('加载仪器分类失败:', error)
  }
}

const loadUsers = async () => {
  if (!authStore.isStaff()) return
  try {
    const response = await getUsers({ skip: 0, limit: 1000 })
    users.value = (response as any) || []
  } catch (error) {
    console.error('加载用户列表失败:', error)
  }
}

const handleFilterChange = async () => {
  currentPage.value = 1
  await loadUsageEvents()
}

// 加载使用记录列表
const loadUsageEvents = async () => {
  loading.value = true
  try {
    const params: any = {
      skip: (currentPage.value - 1) * pageSize.value,
      limit: pageSize.value,
      ...(filterStatus.value !== undefined && { status: filterStatus.value }),
      ...(filterToolId.value !== undefined && { tool_id: filterToolId.value }),
      ...(filterCategoryId.value !== undefined && { category_id: filterCategoryId.value }),
      ...(authStore.isStaff() && filterUserId.value !== undefined && { user_id: filterUserId.value }),
      ...buildDateRangeParams(),
    }

    const response = await getUsageEvents(params)
    tableData.value = Array.isArray(response) ? response : (response as any).data || []
    const serverTotal = (response as any)?._total
    total.value = typeof serverTotal === 'number' ? serverTotal : tableData.value.length

    const statsParams: any = {
      ...(filterStatus.value !== undefined && { status: filterStatus.value }),
      ...(filterToolId.value !== undefined && { tool_id: filterToolId.value }),
      ...(filterCategoryId.value !== undefined && { category_id: filterCategoryId.value }),
      ...(authStore.isStaff() && filterUserId.value !== undefined && { user_id: filterUserId.value }),
      ...buildDateRangeParams(),
    }
    await loadStats(statsParams)
  } catch (error) {
    ElMessage.error('加载使用记录失败')
    console.error(error)
  } finally {
    loading.value = false
  }
}

// 打开编辑对话框
const handleEdit = (row: UsageEvent) => {
  dialogMode.value = 'edit'
  const durationMinutes = row.end ? calcDuration(row.start, row.end) : undefined
  Object.assign(formData, {
    id: row.id,
    tool_id: row.tool_id,
    user_id: row.user_id,
    start: row.start,
    end: row.end,
    actual_duration_minutes: durationMinutes
  })
  dialogVisible.value = true
}

// 结束使用
const handleEnd = async (row: UsageEvent) => {
  try {
    await ElMessageBox.confirm('确定要结束该使用记录吗？', '提示', {
      type: 'warning'
    })
    await endUsageEvent(row.id)
    ElMessage.success('结束成功')
    await loadUsageEvents()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('结束失败')
      console.error(error)
    }
  }
}

// 验证使用记录
const handleValidate = async (row: UsageEvent) => {
  try {
    await ElMessageBox.confirm('确定要确认该使用记录并自动扣费吗？', '提示', {
      type: 'info'
    })
    await validateUsageEvent(row.id)
    ElMessage.success('确认成功，已自动扣费')
    await loadUsageEvents()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('确认失败')
      console.error(error)
    }
  }
}

// 豁免使用记录
const handleWaive = async (row: UsageEvent) => {
  try {
    await ElMessageBox.confirm('确定要豁免该使用记录吗？', '提示', {
      type: 'warning'
    })
    await waiveUsageEvent(row.id)
    ElMessage.success('豁免成功')
    await loadUsageEvents()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('豁免失败')
      console.error(error)
    }
  }
}

// 重新激活（取消豁免）
const handleReactivate = async (row: UsageEvent) => {
  try {
    await ElMessageBox.confirm('确定要重新激活该使用记录吗？激活后将恢复为已确认状态并重新扣费。', '提示', {
      type: 'warning'
    })
    await reactivateUsageEvent(row.id)
    ElMessage.success('激活成功，已重新扣费')
    await loadUsageEvents()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('激活失败')
      console.error(error)
    }
  }
}

// 删除使用记录
const handleDelete = async (row: UsageEvent) => {
  try {
    await ElMessageBox.confirm('确定要删除该使用记录吗？此操作不可恢复！', '警告', {
      type: 'error',
      confirmButtonText: '确定删除'
    })
    await deleteUsageEvent(row.id)
    ElMessage.success('删除成功')
    await loadUsageEvents()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
      console.error(error)
    }
  }
}

// 提交表单
const handleSubmit = async () => {
  if (!formRef.value) return

  await formRef.value.validate(async (valid) => {
    if (!valid) return

    submitting.value = true
    try {
      const submitData = {
        actual_duration_minutes: formData.actual_duration_minutes
      }

      if (dialogMode.value === 'create') {
        // Obsolete
        // await createUsageEvent(submitData)
        // ElMessage.success('创建成功')
      } else {
        await updateUsageEvent(formData.id!, submitData)
        ElMessage.success('更新成功')
      }
      dialogVisible.value = false
      await loadUsageEvents()
    } catch (error) {
      ElMessage.error('更新失败')
      console.error(error)
    } finally {
      submitting.value = false
    }
  })
}

// 重置表单
const resetForm = () => {
  formRef.value?.resetFields()
  Object.assign(formData, {
    tool_id: undefined,
    user_id: undefined,
    start: undefined,
    end: undefined,
    actual_duration_minutes: undefined
  })
}

// 初始化
onMounted(() => {
  loadTools()
  loadCategories()
  loadUsers()
  loadUsageEvents()
})
</script>

<style scoped>
.page-container {
  padding: 20px;
}

.header-card {
  margin-bottom: 16px;
}

.stats-row {
  margin-bottom: 16px;
}

.stat-card {
  display: flex;
  align-items: center;
  gap: 16px;
}

.stat-icon {
  width: 60px;
  height: 60px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
}

.stat-content {
  flex: 1;
}

.stat-value {
  font-size: 24px;
  font-weight: bold;
  color: #303133;
}

.stat-label {
  font-size: 14px;
  color: #909399;
  margin-top: 4px;
}

.stat-sub {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}

.table-card {
  margin-top: 16px;
}

.pagination-container {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}
</style>
