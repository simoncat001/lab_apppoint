<template>
  <div class="page-container">
    <!-- 顶部操作栏 -->
    <el-card class="header-card" shadow="never">
      <el-row :gutter="16" align="middle">
        <el-col :span="12">
          <el-space>
            <el-button type="primary" :icon="Plus" @click="handleCreate">
              创建收费记录
            </el-button>
            <el-button :icon="Refresh" @click="loadStaffCharges">
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
              v-model="filterValidated"
              placeholder="验证状态"
              clearable
              style="width: 120px"
              @change="loadStaffCharges"
            >
              <el-option label="已验证" :value="true" />
              <el-option label="待验证" :value="false" />
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
              <div class="stat-value">{{ stats.total_charges }}</div>
              <div class="stat-label">总收费记录</div>
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
              <div class="stat-value">{{ stats.validated_charges }}</div>
              <div class="stat-label">已验证</div>
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
              <div class="stat-value">{{ stats.pending_charges }}</div>
              <div class="stat-label">待验证</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :xs="24" :sm="12" :lg="6">
        <el-card shadow="hover">
          <div class="stat-card">
            <div class="stat-icon" style="background: #f56c6c">
              <el-icon :size="32"><Money /></el-icon>
            </div>
            <div class="stat-content">
              <div class="stat-value">¥{{ stats.total_cost.toFixed(2) }}</div>
              <div class="stat-label">总费用</div>
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
        <el-table-column label="员工" width="120">
          <template #default="{ row }">
            {{ row.staff_member?.username || '-' }}
          </template>
        </el-table-column>
        <el-table-column label="客户" width="120">
          <template #default="{ row }">
            {{ row.customer?.username || '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="start" label="开始时间" width="180">
          <template #default="{ row }">
            {{ formatDateTime(row.start) }}
          </template>
        </el-table-column>
        <el-table-column prop="end" label="结束时间" width="180">
          <template #default="{ row }">
            {{ row.end ? formatDateTime(row.end) : '服务中' }}
          </template>
        </el-table-column>
        <el-table-column label="时长" width="120">
          <template #default="{ row }">
            <span v-if="row.end">
              {{ formatDuration(calcDuration(row.start, row.end)) }}
            </span>
            <el-tag v-else type="success" effect="dark">服务中</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="费用" width="100">
          <template #default="{ row }">
            <span v-if="row.end" style="color: #f56c6c; font-weight: bold">
              ¥{{ calculateCost(row).toFixed(2) }}
            </span>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column label="验证状态" width="100">
          <template #default="{ row }">
            <el-tag v-if="row.validated" type="success">已验证</el-tag>
            <el-tag v-else-if="row.waived" type="info">已豁免</el-tag>
            <el-tag v-else type="warning">待验证</el-tag>
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
                v-if="!row.validated && !row.waived"
                type="success"
                size="small"
                :icon="Check"
                @click="handleValidate(row)"
              >
                验证
              </el-button>
              <el-button
                v-if="!row.validated && !row.waived"
                type="info"
                size="small"
                @click="handleWaive(row)"
              >
                豁免
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
          @size-change="loadStaffCharges"
          @current-change="loadStaffCharges"
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
        <el-form-item label="员工ID" prop="staff_member_id">
          <el-input v-model.number="formData.staff_member_id" placeholder="请输入员工ID" />
        </el-form-item>
        <el-form-item label="客户ID" prop="customer_id">
          <el-input v-model.number="formData.customer_id" placeholder="请输入客户ID" />
        </el-form-item>
        <el-form-item label="开始时间" prop="start">
          <el-date-picker
            v-model="formData.start"
            type="datetime"
            placeholder="选择开始时间"
            style="width: 100%"
            format="YYYY-MM-DD HH:mm:ss"
          />
        </el-form-item>
        <el-form-item label="结束时间">
          <el-date-picker
            v-model="formData.end"
            type="datetime"
            placeholder="选择结束时间（可选）"
            style="width: 100%"
            format="YYYY-MM-DD HH:mm:ss"
          />
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
  Plus,
  Refresh,
  Edit,
  Delete,
  Check,
  Close,
  Histogram,
  Document,
  Clock,
  Money
} from '@element-plus/icons-vue'
import {
  getStaffCharges,
  createStaffCharge,
  updateStaffCharge,
  deleteStaffCharge,
  endStaffCharge,
  validateStaffCharge,
  waiveStaffCharge,
  getStaffChargeStats
} from '@/api/staff-charges'
import type { StaffCharge } from '@/types'
import { formatDateTime, calcDuration, formatDuration } from '@/utils/helpers'

// 数据列表
const loading = ref(false)
const tableData = ref<StaffCharge[]>([])

// 统计数据
type StaffChargeStats = {
  total_charges: number
  total_cost: number
  validated_charges: number
  pending_charges: number
}

const showStats = ref(true)
const stats = ref<StaffChargeStats>({
  total_charges: 0,
  total_cost: 0,
  validated_charges: 0,
  pending_charges: 0
})

const normalizeStats = (payload?: Partial<StaffChargeStats> | null): StaffChargeStats => ({
  total_charges: Number(payload?.total_charges ?? 0),
  total_cost: Number(payload?.total_cost ?? 0),
  validated_charges: Number(payload?.validated_charges ?? 0),
  pending_charges: Number(payload?.pending_charges ?? 0)
})

// 过滤器
const filterValidated = ref<boolean>()

// 分页
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)

// 对话框
const dialogVisible = ref(false)
const dialogMode = ref<'create' | 'edit'>('create')
const dialogTitle = computed(() => (dialogMode.value === 'create' ? '创建收费记录' : '编辑收费记录'))
const submitting = ref(false)

// 表单
const formRef = ref<FormInstance>()
const formData = reactive<Partial<StaffCharge>>({
  staff_member_id: undefined,
  customer_id: undefined,
  start: undefined,
  end: undefined
})

const formRules: FormRules = {
  staff_member_id: [{ required: true, message: '请输入员工ID', trigger: 'blur' }],
  customer_id: [{ required: true, message: '请输入客户ID', trigger: 'blur' }],
  start: [{ required: true, message: '请选择开始时间', trigger: 'change' }]
}

// 计算费用（简单示例，假设每小时100元）
const calculateCost = (charge: StaffCharge) => {
  if (!charge.end) return 0
  const hours = calcDuration(charge.start, charge.end) / 3600
  return hours * 100 // 假设费率为100元/小时
}

// 加载统计数据
const loadStats = async () => {
  try {
    const response = await getStaffChargeStats()
    const payload = (response as { data?: StaffChargeStats })?.data ?? response
    stats.value = normalizeStats(payload as Partial<StaffChargeStats>)
  } catch (error) {
    console.error('加载统计数据失败:', error)
  }
}

// 加载员工收费列表
const loadStaffCharges = async () => {
  loading.value = true
  try {
    const params = {
      skip: (currentPage.value - 1) * pageSize.value,
      limit: pageSize.value,
      ...(filterValidated.value !== undefined && { validated: filterValidated.value })
    }
    const response = await getStaffCharges(params)
    tableData.value = Array.isArray(response) ? response : (response as any).data || []
    const serverTotal = (response as any)?._total
    total.value = typeof serverTotal === 'number' ? serverTotal : tableData.value.length
    await loadStats()
  } catch (error) {
    ElMessage.error('加载收费记录失败')
    console.error(error)
  } finally {
    loading.value = false
  }
}

// 打开创建对话框
const handleCreate = () => {
  dialogMode.value = 'create'
  dialogVisible.value = true
}

// 打开编辑对话框
const handleEdit = (row: StaffCharge) => {
  dialogMode.value = 'edit'
  Object.assign(formData, {
    id: row.id,
    staff_member_id: row.staff_member_id,
    customer_id: row.customer_id,
    start: row.start,
    end: row.end
  })
  dialogVisible.value = true
}

// 结束服务
const handleEnd = async (row: StaffCharge) => {
  try {
    await ElMessageBox.confirm('确定要结束该服务吗？', '提示', {
      type: 'warning'
    })
    await endStaffCharge(row.id)
    ElMessage.success('结束成功')
    await loadStaffCharges()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('结束失败')
      console.error(error)
    }
  }
}

// 验证收费记录
const handleValidate = async (row: StaffCharge) => {
  try {
    await ElMessageBox.confirm('确定要验证该收费记录吗？', '提示', {
      type: 'info'
    })
    await validateStaffCharge(row.id)
    ElMessage.success('验证成功')
    await loadStaffCharges()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('验证失败')
      console.error(error)
    }
  }
}

// 豁免收费记录
const handleWaive = async (row: StaffCharge) => {
  try {
    await ElMessageBox.confirm('确定要豁免该收费记录吗？', '提示', {
      type: 'warning'
    })
    await waiveStaffCharge(row.id)
    ElMessage.success('豁免成功')
    await loadStaffCharges()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('豁免失败')
      console.error(error)
    }
  }
}

// 删除收费记录
const handleDelete = async (row: StaffCharge) => {
  try {
    await ElMessageBox.confirm('确定要删除该收费记录吗？此操作不可恢复！', '警告', {
      type: 'error',
      confirmButtonText: '确定删除'
    })
    await deleteStaffCharge(row.id)
    ElMessage.success('删除成功')
    await loadStaffCharges()
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
        ...formData,
        start: formData.start ? new Date(formData.start).toISOString() : undefined,
        end: formData.end ? new Date(formData.end).toISOString() : undefined
      }

      if (dialogMode.value === 'create') {
        await createStaffCharge(submitData)
        ElMessage.success('创建成功')
      } else {
        await updateStaffCharge(formData.id!, submitData)
        ElMessage.success('更新成功')
      }
      dialogVisible.value = false
      await loadStaffCharges()
    } catch (error) {
      ElMessage.error(dialogMode.value === 'create' ? '创建失败' : '更新失败')
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
    staff_member_id: undefined,
    customer_id: undefined,
    start: undefined,
    end: undefined
  })
}

// 初始化
onMounted(() => {
  loadStaffCharges()
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

.table-card {
  margin-top: 16px;
}

.pagination-container {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}
</style>
