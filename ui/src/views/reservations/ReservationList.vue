<template>
  <div class="page-container">
    <!-- 统计卡片 -->
    <el-row :gutter="16" class="stats-row">
      <el-col :span="6">
        <el-card shadow="hover">
          <el-statistic title="总预约数" :value="stats.total">
            <template #prefix>
              <el-icon color="#409EFF"><Calendar /></el-icon>
            </template>
          </el-statistic>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <el-statistic title="进行中" :value="stats.ongoing">
            <template #prefix>
              <el-icon color="#67C23A"><Clock /></el-icon>
            </template>
          </el-statistic>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <el-statistic title="已取消" :value="stats.cancelled">
            <template #prefix>
              <el-icon color="#E6A23C"><Warning /></el-icon>
            </template>
          </el-statistic>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <el-statistic title="已错过" :value="stats.missed">
            <template #prefix>
              <el-icon color="#F56C6C"><CircleClose /></el-icon>
            </template>
          </el-statistic>
        </el-card>
      </el-col>
    </el-row>

    <!-- 顶部操作栏 -->
    <el-card class="header-card" shadow="never">
      <el-row :gutter="16" align="middle">
        <el-col :span="12">
          <el-space>
            <el-button type="primary" :icon="Plus" @click="handleCreate">
              创建预约
            </el-button>
            <el-button :icon="Refresh" @click="loadReservations">
              刷新
            </el-button>
            <el-button :icon="Calendar" @click="goToCalendar">
              日历视图
            </el-button>
            <el-button v-if="authStore.isStaff()" :icon="Download" @click="exportReservations">
              导出预约
            </el-button>
          </el-space>
        </el-col>
        <el-col :span="12" style="text-align: right">
          <el-space>
            <el-select
              v-if="authStore.isStaff()"
              v-model="filterUserId"
              placeholder="用户"
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
              v-model="filterCancelled"
              placeholder="状态"
              clearable
              style="width: 120px"
              @change="handleFilterChange"
            >
              <el-option label="未取消" :value="false" />
              <el-option label="已取消" :value="true" />
            </el-select>
          </el-space>
        </el-col>
      </el-row>
    </el-card>

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
        <el-table-column label="用户" width="120">
          <template #default="{ row }">
            {{ row.user?.username || '-' }}
          </template>
        </el-table-column>
        <el-table-column label="项目" width="150">
          <template #default="{ row }">
            {{ row.project?.name || '-' }}
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
        <el-table-column label="时长" width="100">
          <template #default="{ row }">
            {{ calculateDuration(row.start, row.end) }}
          </template>
        </el-table-column>
        <el-table-column label="状态" width="120">
          <template #default="{ row }">
            <el-tag v-if="row.cancelled" type="warning">
              已取消
            </el-tag>
            <el-tag v-else-if="row.missed" type="danger">
              已错过
            </el-tag>
            <el-tag v-else-if="isOngoing(row)" type="success">
              进行中
            </el-tag>
            <el-tag v-else-if="isPast(row)" type="info">
              已完成
            </el-tag>
            <el-tag v-else type="primary">
              未开始
            </el-tag>
            <el-tag
              v-if="row.completed_at"
              type="success"
              effect="plain"
              size="small"
              style="margin-left: 6px"
            >
              已填报
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="备注" min-width="150">
          <template #default="{ row }">
            {{ row.additional_information || '-' }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="340" fixed="right">
          <template #default="{ row }">
            <el-space wrap>
              <el-button size="small" @click="handleCollaboration(row)">
                协作记录
              </el-button>
              <el-button
                type="primary"
                size="small"
                :icon="Edit"
                :disabled="row.cancelled || isPast(row)"
                @click="handleEdit(row)"
              >
                编辑
              </el-button>
              <el-button
                type="danger"
                size="small"
                :icon="Delete"
                :disabled="row.cancelled || isPast(row)"
                @click="handleCancel(row)"
              >
                取消
              </el-button>
              <el-button
                v-if="authStore.isStaff()"
                type="warning"
                size="small"
                :disabled="!canComplete(row)"
                @click="handleComplete(row)"
              >
                {{ row.completed_at ? '修改填报' : '完成填报' }}
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
          @size-change="loadReservations"
          @current-change="loadReservations"
        />
      </div>
    </el-card>

    <!-- 完成填报对话框 -->
    <el-dialog v-model="completeDialogVisible" title="实验完成填报" width="600px">
      <el-form ref="completeFormRef" :model="completeForm" label-width="120px">
        <el-alert
          title="提交后会同步生成或更新一条待确认使用记录；真正扣费仍需在使用记录中确认。"
          type="info"
          :closable="false"
          show-icon
          style="margin-bottom: 12px"
        />
        <el-form-item label="实际开始">
          <el-date-picker
            v-model="completeForm.actual_start"
            type="datetime"
            value-format="YYYY-MM-DDTHH:mm:ss"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="实际结束">
          <el-date-picker
            v-model="completeForm.actual_end"
            type="datetime"
            value-format="YYYY-MM-DDTHH:mm:ss"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="completeForm.completion_note" type="textarea" :rows="3" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="completeDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submittingComplete" @click="submitComplete">提交</el-button>
      </template>
    </el-dialog>

    <!-- 预约协作记录 -->
    <el-dialog
      v-model="collaborationDialogVisible"
      title="预约协作记录"
      width="980px"
      top="6vh"
    >
      <CollaborationRecordPanel
        v-if="selectedReservationForCollaboration"
        :reservation-id="selectedReservationForCollaboration.id"
        :tool-id="selectedReservationForCollaboration.tool_id"
        default-record-type="reservation_note"
      />
    </el-dialog>

    <!-- 创建/编辑对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogTitle"
      width="980px"
      top="5vh"
      class="reservation-dialog"
      @close="resetForm"
    >
      <el-form
        ref="formRef"
        :model="formData"
        :rules="formRules"
        label-width="120px"
      >
        <el-form-item label="仪器" prop="tool_id">
          <el-select
            v-model="formData.tool_id"
            placeholder="请选择仪器"
            filterable
            style="width: 100%"
            @change="handleToolChange"
          >
            <el-option
              v-for="tool in tools"
              :key="tool.id"
              :label="tool.name"
              :value="tool.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="所属项目">
          <el-input
            :model-value="selectedToolProjectName"
            placeholder="请选择已绑定项目的仪器"
            readonly
          />
        </el-form-item>
        <el-form-item label="结算账户" prop="payer_account_id">
          <el-select
            v-model="formData.payer_account_id"
            placeholder="请选择结算账户"
            filterable
            :loading="loadingAccounts"
            :disabled="loadingAccounts || !accounts.length"
            style="width: 100%"
          >
            <el-option
              v-for="account in accounts"
              :key="account.id"
              :label="getAccountOptionLabel(account)"
              :value="account.id"
            />
          </el-select>
          <div class="field-helper">管理员确认使用记录后，会从这里选择的账户自动扣费。</div>
        </el-form-item>
        <el-row :gutter="16">
          <el-col :span="8">
            <el-form-item label="预约日期" required>
              <div class="date-picker-wrapper">
                <el-date-picker
                  v-model="reservationDate"
                  type="date"
                  placeholder="选择日期"
                  value-format="YYYY-MM-DD"
                  :disabled-date="isReservationDateDisabled"
                  style="width: 100%"
                  :clearable="false"
                  @change="updateTimeFromSlider"
                />
                <div class="date-display">{{ reservationDateDisplay }}</div>
              </div>
            </el-form-item>
          </el-col>
          <el-col :span="16">
            <el-form-item label="预约时间" required>
              <div class="time-picker-summary">
                <el-button type="primary" plain @click="openTimePickerDialog">
                  选择时间段
                </el-button>
                <span class="time-picker-value">
                  {{ formatTimeFromMinutes(timeRange[0]) }} - {{ formatTimeFromMinutes(timeRange[1]) }}
                </span>
                <el-tag size="small" type="info">
                  时长: {{ formatDuration(timeRange[1] - timeRange[0]) }}
                </el-tag>
              </div>
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="备注">
          <el-input
            v-model="formData.additional_information"
            type="textarea"
            :rows="3"
            placeholder="请输入备注信息"
          />
        </el-form-item>
        <el-form-item label="自行配置">
          <el-switch
            v-model="formData.self_configuration"
            active-text="是"
            inactive-text="否"
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

    <el-dialog
      v-model="timePickerDialogVisible"
      title="选择预约时间段"
      width="1080px"
      top="10vh"
    >
      <div class="time-grid-tip">{{ timeGridTipText }}</div>
      <div class="time-grid-legend">
        <span class="time-grid-legend-item">
          <span class="time-grid-dot time-grid-dot-available"></span>可选
        </span>
        <span class="time-grid-legend-item">
          <span class="time-grid-dot time-grid-dot-selected"></span>当前选择
        </span>
        <span class="time-grid-legend-item">
          <span class="time-grid-dot time-grid-dot-reserved"></span>已预约
        </span>
        <span class="time-grid-legend-item">
          <span class="time-grid-dot time-grid-dot-disabled"></span>不可选
        </span>
      </div>
      <div class="time-grid-scroll">
        <div class="time-grid-hours">
          <div
            v-for="slot in timeGridSlots"
            :key="`hour-${slot.index}`"
            class="time-grid-hour-cell"
          >
            <span v-if="slot.showLabel">{{ slot.label }}</span>
          </div>
        </div>
        <div class="time-grid-row">
          <button
            v-for="slot in timeGridSlots"
            :key="`slot-${slot.index}`"
            type="button"
            class="time-grid-slot"
            :class="{
              selected: isTimeGridSlotSelected(slot.startMin, slot.endMin),
              reserved: isTimeGridSlotReserved(slot.startMin, slot.endMin),
              disabled: isTimeGridSlotDisabled(slot.startMin, slot.endMin),
              anchor: isTimeGridSlotAnchor(slot.startMin)
            }"
            :title="`${formatTimeFromMinutes(slot.startMin)} - ${formatTimeFromMinutes(slot.endMin)}`"
            @click="handleTimeGridSlotClick(slot.startMin, slot.endMin)"
          />
        </div>
      </div>
      <div class="time-grid-current">
        当前选择：{{ formatTimeFromMinutes(timeGridDraftRange[0]) }} - {{ formatTimeFromMinutes(timeGridDraftRange[1]) }}
      </div>
      <template #footer>
        <el-button @click="timePickerDialogVisible = false">取消</el-button>
        <el-button @click="resetTimeGridAnchor">重选起点</el-button>
        <el-button type="primary" @click="applyTimeGridSelection">确认时间</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import {
  Plus,
  Refresh,
  Edit,
  Delete,
  Calendar,
  Clock,
  Warning,
  CircleClose,
  Download
} from '@element-plus/icons-vue'
import {
  getReservations,
  getOccupiedReservationSlots,
  createReservation,
  updateReservation,
  cancelReservation,
  completeReservation,
  exportReservationsCsv
} from '@/api/reservations'
import { getAccounts } from '@/api/accounts'
import { getTools, getToolCategories } from '@/api/tools'
import { getUsers } from '@/api/users'
import type { Account, Reservation, ReservationOccupiedSlot, Tool, User, ToolCategory } from '@/types'
import { formatDateTime } from '@/utils/helpers'
import {
  buildTimeGridSelectionRange,
  ceilMinuteToStep,
  getNormalizedTimeGridDuration,
  getTimeGridSelectionStepMinutes,
  isSelectableTimeGridBoundary,
  isTimeGridSelectionRangeValid,
  isHourlyPriceType,
  TIME_GRID_STEP_MINUTES
} from '@/utils/reservation-time'
import dayjs from 'dayjs'
import { useAuthStore } from '@/stores/auth'
import { useProjectContextStore } from '@/stores/project-context'
import CollaborationRecordPanel from '@/components/collaboration/CollaborationRecordPanel.vue'

const router = useRouter()
const authStore = useAuthStore()
const projectContextStore = useProjectContextStore()

// 预约时间相关
const reservationDate = ref(dayjs().format('YYYY-MM-DD'))
const timeRange = ref<[number, number]>([540, 600]) // Default 9:00 - 10:00

const TIME_GRID_SLOT_COUNT = 1440 / TIME_GRID_STEP_MINUTES

const formatTimeFromMinutes = (val: number) => {
    const hours = Math.floor(val / 60)
    const minutes = val % 60
    return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}`
}

const formatDuration = (minutes: number) => {
    const h = Math.floor(minutes / 60)
    const m = minutes % 60
    if (h > 0) {
        return `${h}小时${m > 0 ? ` ${m}分钟` : ''}`
    }
    return `${m}分钟`
}

const updateTimeFromSlider = () => {
    if (!reservationDate.value || isAdjustingTimeRange.value) return

    if (!isTimeRangeAvailable(timeRange.value as [number, number])) {
        const fallbackRange = isTimeRangeAvailable(lastValidTimeRange.value)
          ? lastValidTimeRange.value
          : findFirstAvailableRange()
        isAdjustingTimeRange.value = true
        if (fallbackRange) {
          timeRange.value = [...fallbackRange]
          lastValidTimeRange.value = [...fallbackRange]
        } else {
          formData.start = ''
          formData.end = ''
        }
        isAdjustingTimeRange.value = false
        ElMessage.warning(fallbackRange ? '该时间段不可预约（可能已被预约或早于当前时间）' : '当前日期已无可预约时段')
        return
    }

    lastValidTimeRange.value = [...timeRange.value]

    const startMinutes = timeRange.value[0]
    const endMinutes = timeRange.value[1]

    const start = dayjs(reservationDate.value).startOf('day').add(startMinutes, 'minute')
    const end = dayjs(reservationDate.value).startOf('day').add(endMinutes, 'minute')

    formData.start = start.format('YYYY-MM-DD HH:mm:ss')
    formData.end = end.format('YYYY-MM-DD HH:mm:ss')
}

// 数据列表
const loading = ref(false)
const tableData = ref<Reservation[]>([])

// 仪器列表
const tools = ref<Tool[]>([])
const accounts = ref<Account[]>([])
const categories = ref<ToolCategory[]>([])
const loadingAccounts = ref(false)

// 用户列表（仅 staff 用于筛选）
const users = ref<User[]>([])
// 项目列表（用于预约归属/组织账户结算）

// 过滤器
const dateRange = ref<[string, string]>()
const filterCancelled = ref<boolean>()
const filterUserId = ref<number>()
const filterToolId = ref<number>()
const filterCategoryId = ref<number>()

const filteredTools = computed(() => {
  if (!filterCategoryId.value) return tools.value
  return tools.value.filter(
    (tool) => (tool.category?.id ?? tool.category_id) === filterCategoryId.value
  )
})

const selectedFormTool = computed(() => tools.value.find((item) => item.id === formData.tool_id))
const requiresWholeHourSelection = computed(() => !!selectedFormTool.value && isHourlyPriceType(selectedFormTool.value.price_type))
const timeGridSelectionStepMinutes = computed(() => getTimeGridSelectionStepMinutes(requiresWholeHourSelection.value))
const timeGridTipText = computed(() => {
  if (requiresWholeHourSelection.value) {
    return '按小时计费仅支持整点起止；先点击起始整点，再点击结束整点'
  }
  return '点击起始格子，再点击结束格子（每格 15 分钟）'
})

const selectedToolProjectName = computed(() => {
  return selectedFormTool.value?.project?.name || ''
})

const reservationDateDisplay = computed(() => {
  if (!reservationDate.value) return ''
  return dayjs(reservationDate.value).format('YYYY年MM月DD日 dddd')
})

// 分页
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)

// 统计数据
const stats = reactive({
  total: 0,
  ongoing: 0,
  cancelled: 0,
  missed: 0
})

// 对话框
const dialogVisible = ref(false)
const dialogMode = ref<'create' | 'edit'>('create')
const dialogTitle = computed(() => (dialogMode.value === 'create' ? '创建预约' : '编辑预约'))
const submitting = ref(false)
const submittingComplete = ref(false)
const isCreateMode = computed(() => dialogMode.value === 'create')
const timePickerDialogVisible = ref(false)
const timeGridDraftRange = ref<[number, number]>([540, 600])
const timeGridAnchorStart = ref<number | null>(null)

const earliestSelectableMinute = computed(() => {
  if (!reservationDate.value || !isCreateMode.value) return 0
  const selectedDay = dayjs(reservationDate.value).startOf('day')
  const now = dayjs()
  if (selectedDay.isAfter(now, 'day')) return 0
  if (selectedDay.isBefore(now, 'day')) return 1440
  const currentMinute = now.diff(selectedDay, 'minute')
  return ceilMinuteToStep(currentMinute, timeGridSelectionStepMinutes.value)
})

const isReservationDateDisabled = (date: Date) => {
  if (!isCreateMode.value) return false
  return dayjs(date).isBefore(dayjs().startOf('day'))
}

// 表单
const formRef = ref<FormInstance>()
const completeFormRef = ref<FormInstance>()
const formData = reactive<Partial<Reservation>>({
  tool_id: undefined,
  project_id: undefined,
  payer_account_id: undefined,
  user_id: authStore.user?.id,
  start: '',
  end: '',
  additional_information: '',
  self_configuration: false,
  cancelled: false,
  missed: false
})

const reservedReservations = ref<ReservationOccupiedSlot[]>([])
const lastValidTimeRange = ref<[number, number]>([540, 600])
const isAdjustingTimeRange = ref(false)

const completeDialogVisible = ref(false)
const collaborationDialogVisible = ref(false)
const selectedReservationForCollaboration = ref<Reservation | null>(null)
const completeForm = reactive({
  id: 0,
  actual_start: '',
  actual_end: '',
  completion_note: '',
})

const formRules: FormRules = {
  tool_id: [{ required: true, message: '请选择仪器', trigger: 'change' }],
  payer_account_id: [{ required: true, message: '请选择结算账户', trigger: 'change' }],
  start: [{ required: true, message: '请选择开始时间', trigger: 'change' }],
  end: [{ required: true, message: '请选择结束时间', trigger: 'change' }]
}

// 加载仪器列表
const loadTools = async () => {
  try {
    const response = await getTools({ skip: 0, limit: 1000 })
    tools.value = Array.isArray(response) ? response : (response as any)?.data || []
  } catch (error) {
    console.error('加载仪器列表失败:', error)
  }
}

const ensureSelectedPayerAccount = () => {
  if (!accounts.value.length) {
    formData.payer_account_id = undefined
    return
  }
  if (accounts.value.some((item) => item.id === formData.payer_account_id)) {
    return
  }
  formData.payer_account_id = accounts.value[0].id
}

const loadAccounts = async (userId?: number) => {
  loadingAccounts.value = true
  try {
    const currentProjectId = projectContextStore.currentProjectId
    const effectiveUserId = Number(userId || formData.user_id || authStore.user?.id || 0)
    if (!currentProjectId || !effectiveUserId) {
      accounts.value = []
      ensureSelectedPayerAccount()
      return
    }
    const response = await getAccounts({
      skip: 0,
      limit: 1000,
      active: true,
      user_id: effectiveUserId,
      reservable_project_id: currentProjectId
    })
    accounts.value = Array.isArray(response) ? response : (response as any)?.data || []
    ensureSelectedPayerAccount()
  } catch (error) {
    console.error('加载账户列表失败:', error)
    ElMessage.error('加载账户列表失败')
  } finally {
    loadingAccounts.value = false
  }
}

const getAccountOptionLabel = (account: Account) => account.name

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
  await loadReservations()
}

// 加载预约列表
const loadReservations = async () => {
  loading.value = true
  try {
    const params: any = {
      skip: (currentPage.value - 1) * pageSize.value,
      limit: pageSize.value
    }

    if (filterToolId.value !== undefined) {
      params.tool_id = filterToolId.value
    }
    if (authStore.isStaff() && filterUserId.value !== undefined) {
      params.user_id = filterUserId.value
    }
    if (filterCategoryId.value !== undefined) {
      params.category_id = filterCategoryId.value
    }
    
    if (dateRange.value) {
      params.start_date = dateRange.value[0]
      params.end_date = dateRange.value[1]
    }
    if (filterCancelled.value !== undefined) {
      params.cancelled = filterCancelled.value
    }

    const response = await getReservations(params)
    const data = Array.isArray(response) ? response : []
    const serverTotal = (response as any)?._total

    tableData.value = data
    total.value = typeof serverTotal === 'number' ? serverTotal : data.length

    // 计算统计数据
    calculateStats(data)
  } catch (error) {
    ElMessage.error('加载预约列表失败')
    console.error(error)
  } finally {
    loading.value = false
  }
}

const loadReservedReservations = async () => {
  try {
    if (!formData.tool_id || !reservationDate.value) {
      reservedReservations.value = []
      return
    }
    const startDate = dayjs(reservationDate.value).startOf('day').format('YYYY-MM-DD HH:mm:ss')
    const endDate = dayjs(reservationDate.value).endOf('day').format('YYYY-MM-DD HH:mm:ss')
    const params = {
      tool_id: formData.tool_id,
      start_date: startDate,
      end_date: endDate,
    }
    const data = await getOccupiedReservationSlots(params)
    const excludeId = dialogMode.value === 'edit' ? formData.id : undefined
    reservedReservations.value = excludeId ? data.filter((r: ReservationOccupiedSlot) => r.id !== excludeId) : data
  } catch (error) {
    console.error('加载已预约时间失败:', error)
  }
}

const reservedBlocks = computed(() => {
  if (!reservationDate.value) return []
  const dayStart = dayjs(reservationDate.value).startOf('day')
  const dayEnd = dayjs(reservationDate.value).endOf('day')
  return reservedReservations.value
    .map((reservation) => {
      const start = dayjs(reservation.start)
      const end = dayjs(reservation.end)
      const displayStart = start.isBefore(dayStart) ? dayStart : start
      const displayEnd = end.isAfter(dayEnd) ? dayEnd : end
      const startMin = Math.max(displayStart.diff(dayStart, 'minute'), 0)
      const endMin = Math.min(displayEnd.diff(dayStart, 'minute'), 1440)
      if (endMin <= startMin) return null
      return {
        id: reservation.id,
        startMin,
        endMin,
        start: reservation.start,
        end: reservation.end
      }
    })
    .filter(Boolean) as Array<{ id: number; startMin: number; endMin: number; start: string; end: string }>
})

const timeGridSlots = computed(() => {
  return Array.from({ length: TIME_GRID_SLOT_COUNT }, (_, index) => {
    const startMin = index * TIME_GRID_STEP_MINUTES
    return {
      index,
      startMin,
      endMin: startMin + TIME_GRID_STEP_MINUTES,
      label: formatTimeFromMinutes(startMin),
      showLabel: index % 4 === 0
    }
  })
})

const isTimeRangeAvailable = (range: [number, number]) => {
  if (isCreateMode.value && range[0] < earliestSelectableMinute.value) {
    return false
  }
  return !reservedBlocks.value.some((block) => range[0] < block.endMin && range[1] > block.startMin)
}

const findFirstAvailableRange = () => {
  const duration = getNormalizedTimeGridDuration(
    timeRange.value[1] - timeRange.value[0],
    requiresWholeHourSelection.value
  )
  const earliest = isCreateMode.value ? earliestSelectableMinute.value : 0
  for (let start = earliest; start + duration <= 1440; start += timeGridSelectionStepMinutes.value) {
    const candidate: [number, number] = [start, start + duration]
    if (
      isTimeGridSelectionRangeValid(candidate, requiresWholeHourSelection.value) &&
      isTimeRangeAvailable(candidate)
    ) {
      return candidate
    }
  }
  return null
}

const isTimeGridSlotReserved = (startMin: number, endMin: number) => {
  return reservedBlocks.value.some((block) => startMin < block.endMin && endMin > block.startMin)
}

const isTimeGridSlotDisabled = (startMin: number, endMin: number) => {
  if (isCreateMode.value && startMin < earliestSelectableMinute.value) {
    return true
  }
  if (
    !isSelectableTimeGridBoundary({
      anchorStart: timeGridAnchorStart.value,
      startMin,
      endMin,
      requiresWholeHourSelection: requiresWholeHourSelection.value
    })
  ) {
    return true
  }
  return isTimeGridSlotReserved(startMin, endMin)
}

const isTimeGridSlotSelected = (startMin: number, endMin: number) => {
  return startMin < timeGridDraftRange.value[1] && endMin > timeGridDraftRange.value[0]
}

const isTimeGridSlotAnchor = (startMin: number) => {
  return timeGridAnchorStart.value === startMin
}

const openTimePickerDialog = async () => {
  if (!formData.tool_id) {
    ElMessage.warning('请先选择仪器')
    return
  }
  if (!reservationDate.value) {
    ElMessage.warning('请先选择预约日期')
    return
  }
  await loadReservedReservations()
  const currentRange = [...timeRange.value] as [number, number]
  const fallbackRange =
    isTimeGridSelectionRangeValid(currentRange, requiresWholeHourSelection.value) &&
    isTimeRangeAvailable(currentRange)
      ? currentRange
      : findFirstAvailableRange()
  if (fallbackRange) {
    timeGridDraftRange.value = [...fallbackRange]
  } else {
    const step = timeGridSelectionStepMinutes.value
    const baseStart = Math.min(Math.max(earliestSelectableMinute.value, 0), 1440 - step)
    timeGridDraftRange.value = [baseStart, baseStart + step]
  }
  timeGridAnchorStart.value = null
  timePickerDialogVisible.value = true
}

const handleTimeGridSlotClick = (startMin: number, endMin: number) => {
  if (isTimeGridSlotDisabled(startMin, endMin)) {
    return
  }
  if (timeGridAnchorStart.value === null) {
    timeGridAnchorStart.value = startMin
    timeGridDraftRange.value = [
      startMin,
      Math.min(startMin + timeGridSelectionStepMinutes.value, 1440)
    ]
    return
  }
  const candidateRange = buildTimeGridSelectionRange({
    anchorStart: timeGridAnchorStart.value,
    startMin,
    endMin,
    requiresWholeHourSelection: requiresWholeHourSelection.value
  })
  if (!candidateRange) {
    ElMessage.warning('按小时计费仪器只能选择整点起止时间')
    return
  }
  if (!isTimeRangeAvailable(candidateRange)) {
    ElMessage.warning('所选时间段不可预约，请重新选择')
    return
  }
  timeGridDraftRange.value = candidateRange
}

const resetTimeGridAnchor = () => {
  timeGridAnchorStart.value = null
}

const applyTimeGridSelection = () => {
  if (!isTimeGridSelectionRangeValid(timeGridDraftRange.value, requiresWholeHourSelection.value)) {
    ElMessage.warning('按小时计费仪器只能选择整点起止时间')
    return
  }
  if (!isTimeRangeAvailable(timeGridDraftRange.value)) {
    ElMessage.warning('所选时间段不可预约，请重新选择')
    return
  }
  timeRange.value = [...timeGridDraftRange.value]
  updateTimeFromSlider()
  timeGridAnchorStart.value = null
  timePickerDialogVisible.value = false
}

const handleToolChange = async () => {
  const tool = tools.value.find((item) => item.id === formData.tool_id)
  formData.project_id = tool?.project_id ?? tool?.project?.id ?? undefined
  await loadReservedReservations()
  updateTimeFromSlider()
}

watch(
  [reservationDate, () => formData.tool_id],
  async () => {
    await loadReservedReservations()
    updateTimeFromSlider()
  }
)

// 计算统计数据
const calculateStats = (data: Reservation[]) => {
  stats.total = data.length
  stats.ongoing = data.filter(r => !r.cancelled && !r.missed && isOngoing(r)).length
  stats.cancelled = data.filter(r => r.cancelled).length
  stats.missed = data.filter(r => r.missed).length
}

// 判断预约是否进行中
const isOngoing = (reservation: Reservation) => {
  const now = dayjs()
  const start = dayjs(reservation.start)
  const end = dayjs(reservation.end)
  return now.isAfter(start) && now.isBefore(end)
}

// 判断预约是否已过期
const isPast = (reservation: Reservation) => {
  const now = dayjs()
  const end = dayjs(reservation.end)
  return now.isAfter(end)
}

const canComplete = (reservation: Reservation) => {
  return authStore.isStaff() && !reservation.cancelled && isPast(reservation)
}

const formatCompleteDateTime = (value?: string) => {
  return value ? dayjs(value).format('YYYY-MM-DDTHH:mm:ss') : ''
}

// 计算时长
const calculateDuration = (start: string, end: string) => {
  const startTime = dayjs(start)
  const endTime = dayjs(end)
  const diffMinutes = endTime.diff(startTime, 'minute')
  const hours = Math.floor(diffMinutes / 60)
  const minutes = diffMinutes % 60
  return `${hours}h${minutes}m`
}

// 跳转到日历视图
const goToCalendar = () => {
  router.push('/calendar')
}

// 打开创建对话框
const handleCreate = async () => {
  router.push({
    name: 'ReservationCreate',
    query: {
      from: 'reservations',
      ...(filterToolId.value ? { toolId: String(filterToolId.value) } : {})
    }
  })
}

// 打开编辑对话框
const handleEdit = async (row: Reservation) => {
  dialogMode.value = 'edit'
  Object.assign(formData, {
    id: row.id,
    tool_id: row.tool_id,
    project_id: row.project_id,
    payer_account_id: row.payer_account_id,
    user_id: row.user_id,
    start: row.start,
    end: row.end,
    additional_information: row.additional_information,
    self_configuration: row.self_configuration
  })
  await loadAccounts(row.user_id)
  
  const start = dayjs(row.start)
  const end = dayjs(row.end)
  reservationDate.value = start.format('YYYY-MM-DD')
  const startMinutes = start.hour() * 60 + start.minute()
  let endMinutes = end.hour() * 60 + end.minute()
  
  // 处理跨天情况（如果是第二天0点，设为1440）
  if (end.date() !== start.date()) {
      endMinutes += 1440
  }
  
  timeRange.value = [startMinutes, endMinutes]
  lastValidTimeRange.value = [startMinutes, endMinutes]
  
  dialogVisible.value = true
  await loadReservedReservations()
  updateTimeFromSlider()
}

// 取消预约
const handleCancel = async (row: Reservation) => {
  try {
    await ElMessageBox.confirm('确定要取消该预约吗？', '警告', {
      type: 'warning',
      confirmButtonText: '确定取消'
    })
    await cancelReservation(row.id)
    ElMessage.success('取消成功')
    await loadReservations()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error((error as any)?.response?.data?.detail || '取消失败')
      console.error(error)
    }
  }
}

const handleComplete = (row: Reservation) => {
  if (!canComplete(row)) {
    ElMessage.warning(row.cancelled ? '已取消的预约不能完成填报' : '预约尚未结束，不能完成填报')
    return
  }
  completeForm.id = row.id
  completeForm.actual_start = formatCompleteDateTime(row.actual_start || row.start)
  completeForm.actual_end = formatCompleteDateTime(row.actual_end || row.end)
  completeForm.completion_note = row.completion_note || ''
  completeDialogVisible.value = true
}

const handleCollaboration = (row: Reservation) => {
  selectedReservationForCollaboration.value = row
  collaborationDialogVisible.value = true
}

const submitComplete = async () => {
  if (!completeForm.actual_start || !completeForm.actual_end) {
    ElMessage.warning('请填写实际开始和实际结束时间')
    return
  }
  if (!dayjs(completeForm.actual_end).isAfter(dayjs(completeForm.actual_start))) {
    ElMessage.warning('实际结束时间必须晚于实际开始时间')
    return
  }
  if (dayjs(completeForm.actual_end).isAfter(dayjs())) {
    ElMessage.warning('实际结束时间不能晚于当前时间')
    return
  }

  submittingComplete.value = true
  try {
    await completeReservation(completeForm.id, {
      actual_start: completeForm.actual_start || undefined,
      actual_end: completeForm.actual_end || undefined,
      completion_note: completeForm.completion_note || undefined,
    })
    ElMessage.success('填报成功')
    completeDialogVisible.value = false
    await loadReservations()
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '填报失败')
  } finally {
    submittingComplete.value = false
  }
}

const exportReservations = async () => {
  try {
    await exportReservationsCsv()
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '导出失败')
  }
}

// 提交表单
const handleSubmit = async () => {
  if (!formRef.value) return

  await loadReservedReservations()

  await formRef.value.validate(async (valid: any) => {
    if (!valid) return

    // 验证时间
    if (!dayjs(formData.end).isAfter(dayjs(formData.start))) {
      ElMessage.error('结束时间必须晚于开始时间')
      return
    }
    if (dialogMode.value === 'create' && dayjs(formData.start).isBefore(dayjs())) {
      ElMessage.error('开始时间不能早于当前时间')
      return
    }
    if (!isTimeRangeAvailable(timeRange.value as [number, number])) {
      ElMessage.error('该时间段不可预约（可能已被预约或早于当前时间）')
      return
    }

    submitting.value = true
    try {
      if (dialogMode.value === 'create') {
        await createReservation(formData)
        ElMessage.success('创建成功')
      } else {
        await updateReservation(formData.id!, formData)
        ElMessage.success('更新成功')
      }
      dialogVisible.value = false
      await loadReservations()
    } catch (error: any) {
      const detail = error?.response?.data?.detail
      if (typeof detail === 'string' && detail.trim()) {
        ElMessage.error(detail)
      } else if (Array.isArray(detail) && detail.length) {
        const message = detail
          .map((item: any) => item?.msg || item?.message || JSON.stringify(item))
          .join('；')
        ElMessage.error(message)
      } else if (detail) {
        ElMessage.error(JSON.stringify(detail))
      } else if (error.response?.status === 409) {
        ElMessage.error('该时间段已被预约')
      } else {
        ElMessage.error(dialogMode.value === 'create' ? '创建失败' : '更新失败')
      }
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
    id: undefined,
    tool_id: undefined,
    project_id: undefined,
    payer_account_id: accounts.value[0]?.id,
    user_id: authStore.user?.id,
    start: '',
    end: '',
    additional_information: '',
    self_configuration: false
  })
  reservedReservations.value = []
  timeGridAnchorStart.value = null
  timePickerDialogVisible.value = false
}

// 初始化
onMounted(async () => {
  projectContextStore.hydrate()
  await Promise.all([loadTools(), loadCategories(), loadUsers(), loadAccounts()])
  await loadReservations()
})
</script>

<style scoped>
.page-container {
  padding: 20px;
}

.stats-row {
  margin-bottom: 16px;
}

.header-card {
  margin-bottom: 16px;
}

.table-card {
  margin-top: 16px;
}

.pagination-container {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}

.time-picker-summary {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.time-picker-value {
  font-size: 14px;
  color: #303133;
}

.time-grid-tip {
  margin-bottom: 10px;
  font-size: 13px;
  color: #606266;
}

.time-grid-legend {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 10px;
  font-size: 12px;
  color: #606266;
}

.time-grid-legend-item {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.time-grid-dot {
  width: 10px;
  height: 10px;
  border-radius: 999px;
  display: inline-block;
}

.time-grid-dot-available {
  background: #ffffff;
  border: 1px solid #cbd5e1;
}

.time-grid-dot-selected {
  background: #2563eb;
  border: 1px solid #1d4ed8;
}

.time-grid-dot-reserved {
  background: #ef4444;
  border: 1px solid #dc2626;
}

.time-grid-dot-disabled {
  background: #9ca3af;
  border: 1px solid #6b7280;
}

.time-grid-scroll {
  overflow-x: auto;
  overflow-y: hidden;
  padding-bottom: 8px;
}

.time-grid-hours,
.time-grid-row {
  display: grid;
  grid-template-columns: repeat(96, 18px);
  column-gap: 2px;
  width: max-content;
  min-width: 100%;
}

.time-grid-hours {
  margin-bottom: 6px;
}

.time-grid-hour-cell {
  text-align: left;
  font-size: 10px;
  color: #909399;
  height: 16px;
}

.time-grid-slot {
  width: 18px;
  height: 28px;
  padding: 0;
  border-radius: 2px;
  border: 1px solid #cbd5e1;
  background: #ffffff;
  cursor: pointer;
  transition: all 0.15s ease;
}

.time-grid-slot:hover {
  border-color: #2563eb;
}

.time-grid-slot.selected {
  background: #2563eb;
  border-color: #1d4ed8;
}

.time-grid-slot.anchor {
  box-shadow: inset 0 0 0 1px #0f172a;
}

.time-grid-slot.reserved {
  background: #ef4444;
  border-color: #dc2626;
  cursor: not-allowed;
}

.time-grid-slot.disabled {
  background: #9ca3af;
  border-color: #6b7280;
  cursor: not-allowed;
}

.time-grid-current {
  margin-top: 8px;
  font-size: 13px;
  color: #303133;
}

.date-picker-wrapper {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.date-display {
  font-size: 12px;
  color: #909399;
}

.field-helper {
  margin-top: 6px;
  font-size: 12px;
  line-height: 1.5;
  color: #64748b;
}

</style>
