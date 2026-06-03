<template>
  <div class="reservation-create-page">
    <div class="reservation-create-shell">
      <div class="page-header">
        <div>
          <div class="page-kicker">Reservation</div>
          <h1 class="page-title">创建预约</h1>
          <p class="page-subtitle">
            {{
              isCountBasedTool
                ? '按次收费仪器只需要选择日期；当天次数达到上限后，日期会直接不可预约。'
                : requiresWholeHourSelection
                  ? '按小时计费仪器只能按整点预约；先选择日期，再在下方 Day 时间轴上选择整点起止。'
                  : '先在页面里选择日期，再直接在下方 Day 时间轴上选择时间段。'
            }}
          </p>
        </div>
        <el-button :icon="ArrowLeft" @click="goBack">返回</el-button>
      </div>

      <el-row :gutter="16">
        <el-col :xs="24" :lg="15">
          <el-card shadow="never" class="create-card">
            <el-form
              ref="formRef"
              :model="formData"
              :rules="formRules"
              label-position="top"
              class="create-form"
            >
              <el-form-item label="仪器" prop="tool_id">
                <el-select
                  v-model="formData.tool_id"
                  placeholder="请选择仪器"
                  filterable
                  clearable
                  :loading="loadingTools"
                  size="large"
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

              <el-form-item label="当前项目">
                <div class="project-display">
                  <span class="project-display-label">项目</span>
                  <span class="project-display-name">{{ selectedToolProjectName || '当前仪器未绑定项目' }}</span>
                </div>
              </el-form-item>

              <el-form-item label="结算账户" prop="payer_account_id">
                <el-select
                  v-model="formData.payer_account_id"
                  placeholder="请选择结算账户"
                  filterable
                  :loading="loadingAccounts"
                  :disabled="loadingAccounts || !accounts.length"
                  size="large"
                  style="width: 100%"
                >
                  <el-option
                    v-for="account in accounts"
                    :key="account.id"
                    :label="getAccountOptionLabel(account)"
                    :value="account.id"
                  />
                </el-select>
                <div class="field-helper">使用结束后，管理员确认使用记录时会从这里选择的账户自动扣费。</div>
              </el-form-item>

              <el-row :gutter="12" class="form-inline-row">
                <el-col :xs="24" :md="8">
                  <el-form-item label="预约日期">
                    <el-date-picker
                      v-model="reservationDate"
                      type="date"
                      value-format="YYYY-MM-DD"
                      placeholder="请选择日期"
                      size="large"
                      style="width: 100%"
                      :disabled-date="isReservationDateDisabled"
                      :clearable="false"
                      @change="handleReservationDateChange"
                    />
                    <div
                      v-if="isCountBasedTool"
                      class="count-based-date-status"
                      :class="{ full: isSelectedDateQuotaFull }"
                    >
                      <template v-if="dailyReservationQuota > 0">
                        {{
                          reservationDate
                            ? isSelectedDateQuotaFull
                              ? '当天预约次数已满，无法继续预约'
                              : `当天还可预约 ${selectedDateRemainingCount} 次 / 共 ${dailyReservationQuota} 次`
                            : `请选择预约日期（每日最多 ${dailyReservationQuota} 次）`
                        }}
                      </template>
                      <template v-else>
                        当前仪器按次收费，但暂未设置每日上限。
                      </template>
                    </div>
                  </el-form-item>
                </el-col>
                <el-col :xs="24" :md="16">
                  <el-form-item label="备注">
                    <el-input
                      v-model="formData.additional_information"
                      type="textarea"
                      :rows="3"
                      maxlength="300"
                      show-word-limit
                      placeholder="可填写样品、实验说明或注意事项"
                    />
                  </el-form-item>
                </el-col>
              </el-row>

              <div class="inline-day-calendar-section">
                <div class="day-calendar-header">
                  <div>
                    <div class="day-calendar-title">{{ isCountBasedTool ? '按次预约日历' : 'Day 时间轴' }}</div>
                    <div class="day-calendar-subtitle">
                      {{ reservationDate ? formatReservationDate(reservationDate) : '请先选择日期' }}
                    </div>
                  </div>
                  <el-space v-if="!isCountBasedTool" wrap>
                    <el-button @click="clearTimeSelection" :disabled="!selectedTimeRange">清空时间</el-button>
                    <el-button @click="resetTimeGridAnchor" :disabled="!canOpenDateTimeSelector">重选起点</el-button>
                  </el-space>
                  <el-tag v-else type="success" effect="light">按天限次</el-tag>
                </div>

                <div v-if="!formData.tool_id" class="day-calendar-empty">
                  <el-empty description="请先选择仪器，再在这里选择预约时间" :image-size="72" />
                </div>
                <div v-else-if="!formData.project_id" class="day-calendar-empty">
                  <el-empty description="当前仪器未绑定项目，暂时不能创建预约" :image-size="72" />
                </div>
                <div v-else-if="isCountBasedTool" class="count-based-board">
                  <div class="count-based-stat-grid">
                    <div class="count-based-stat-card">
                      <span class="count-based-stat-label">每日上限</span>
                      <strong class="count-based-stat-value">{{ dailyReservationQuota > 0 ? `${dailyReservationQuota} 次` : '未限制' }}</strong>
                    </div>
                    <div class="count-based-stat-card">
                      <span class="count-based-stat-label">已预约</span>
                      <strong class="count-based-stat-value">{{ `${selectedDateReservationCount} 次` }}</strong>
                    </div>
                    <div class="count-based-stat-card" :class="{ danger: isSelectedDateQuotaFull }">
                      <span class="count-based-stat-label">剩余</span>
                      <strong class="count-based-stat-value">
                        {{ selectedDateRemainingCount === null ? '不限' : `${selectedDateRemainingCount} 次` }}
                      </strong>
                    </div>
                  </div>
                  <div class="count-based-selected-date">
                    <span class="count-based-selected-date-label">当前日期</span>
                    <span class="count-based-selected-date-value">
                      {{ reservationDate ? formatReservationDate(reservationDate) : '未选择' }}
                    </span>
                  </div>
                </div>
                <div v-else>
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

                  <div class="time-day-board">
                    <div class="time-day-board-header">
                      <div class="time-day-board-date">{{ reservationDate ? formatReservationDate(reservationDate) : '' }}</div>
                      <div class="time-grid-current">{{ timeGridCurrentText }}</div>
                    </div>
                    <div class="time-day-scroll">
                      <div class="time-day-grid">
                        <div
                          v-for="slot in timeGridSlots"
                          :key="`slot-row-${slot.index}`"
                          class="time-day-row"
                        >
                          <div class="time-day-axis">
                            <span v-if="slot.showLabel">{{ slot.label }}</span>
                          </div>
                          <button
                            type="button"
                            class="time-day-slot"
                            :class="{
                              major: slot.showLabel,
                              mid: !slot.showLabel && slot.startMin % 30 === 0,
                              selected: isTimeGridSlotSelected(slot.startMin, slot.endMin),
                              reserved: isTimeGridSlotReserved(slot.startMin, slot.endMin),
                              disabled: isTimeGridSlotDisabled(slot.startMin, slot.endMin),
                              anchor: isTimeGridSlotAnchor(slot.startMin)
                            }"
                            :title="`${formatTimeFromMinutes(slot.startMin)} - ${formatTimeFromMinutes(slot.endMin)}`"
                            @click="handleTimeGridSlotClick(slot.startMin, slot.endMin)"
                          />
                        </div>
                        <div
                          v-if="timePickerNowLineVisible"
                          class="time-day-now-line"
                          :style="timePickerNowLineStyle"
                        >
                          <span class="time-day-now-label">{{ nowTimeLabel }}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

              </div>

              <el-form-item :label="isCountBasedTool ? '已选日期' : '已选时间'" prop="start">
                <div class="selected-time-panel">
                  <div class="selected-time-value">{{ selectedDateTimeLabel }}</div>
                  <div class="selected-time-helper">
                    {{
                      isCountBasedTool
                        ? '按次收费模式下，选中日期后会按当天一次预约处理。'
                        : requiresWholeHourSelection
                          ? '按小时计费模式下，只能选择整点起止时间。'
                          : '在下方 Day 时间轴上点击起点，再点击终点。'
                    }}
                  </div>
                </div>
              </el-form-item>

              <div class="form-submit-actions">
                <div class="form-submit-hint">
                  {{ hasDateTimeSelected ? selectedDateTimeLabel : (isCountBasedTool ? '请先选择可预约日期' : '请先选择预约日期和时间段') }}
                </div>
                <el-button
                  type="primary"
                  size="large"
                  :icon="Plus"
                  :loading="submitting"
                  @click="handleSubmit"
                >
                  提交预约
                </el-button>
              </div>

              <el-form-item label="自行配置">
                <el-switch
                  v-model="formData.self_configuration"
                  inline-prompt
                  active-text="是"
                  inactive-text="否"
                />
              </el-form-item>
            </el-form>
          </el-card>
        </el-col>

        <el-col :xs="24" :lg="9">
          <el-card shadow="never" class="summary-card">
            <template #header>
              <div class="summary-header">
                <span>预约摘要</span>
                <el-tag :type="summaryTagType" effect="plain">{{ summaryTagText }}</el-tag>
              </div>
            </template>

            <div class="summary-list">
              <div class="summary-item">
                <span class="summary-label">当前项目</span>
                <span class="summary-value">{{ currentProjectName || '未选择项目' }}</span>
              </div>
              <div class="summary-item">
                <span class="summary-label">结算账户</span>
                <span class="summary-value">{{ selectedPayerAccount?.name || '未选择' }}</span>
              </div>
              <div class="summary-item">
                <span class="summary-label">仪器</span>
                <span class="summary-value">{{ selectedTool?.name || '未选择' }}</span>
              </div>
              <div class="summary-item">
                <span class="summary-label">预约日期</span>
                <span class="summary-value">{{ reservationDate ? formatReservationDate(reservationDate) : '未选择' }}</span>
              </div>
              <div class="summary-item">
                <span class="summary-label">{{ isCountBasedTool ? '预约方式' : '预约时间' }}</span>
                <span class="summary-value">{{ isCountBasedTool ? '按次预约（按天）' : (selectedTimeRangeText || '未选择') }}</span>
              </div>
              <div class="summary-item">
                <span class="summary-label">{{ isCountBasedTool ? '预约数量' : '时长' }}</span>
                <span class="summary-value">{{ selectedDurationText || '未选择' }}</span>
              </div>
              <div v-if="isCountBasedTool" class="summary-item">
                <span class="summary-label">当日剩余次数</span>
                <span class="summary-value">
                  {{ selectedDateRemainingCount === null ? '不限' : `${selectedDateRemainingCount} 次` }}
                </span>
              </div>
            </div>

            <el-alert
              v-if="formData.tool_id && !formData.project_id"
              title="当前仪器未绑定项目，暂时不能创建预约。"
              type="warning"
              :closable="false"
              show-icon
            />
            <el-alert
              v-else-if="!loadingAccounts && !accounts.length"
              title="当前没有可用的结算账户，请先联系管理员配置账户后再预约。"
              type="warning"
              :closable="false"
              show-icon
            />

            <div class="summary-notes">
              <div class="summary-note-title">说明</div>
              <ul v-if="isCountBasedTool" class="summary-note-list">
                <li>按次收费仪器只按日期预约，不需要选择具体小时或分钟。</li>
                <li>达到每日预约上限后，日期会直接显示不可预约。</li>
                <li>提交后按 1 次计费，金额取仪器的按次单价。</li>
              </ul>
              <ul v-else class="summary-note-list">
                <li>开始时间早于当前时间的预约不会提交成功。</li>
                <li>红色表示该时间段已被预约，不可再次选择。</li>
                <li>灰色表示早于当前时间，或当前不可选。</li>
              </ul>
            </div>
          </el-card>
        </el-col>
      </el-row>

    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { ArrowLeft, Plus } from '@element-plus/icons-vue'
import dayjs from 'dayjs'
import {
  createReservation,
  getReservations,
  getOccupiedReservationSlots
} from '@/api/reservations'
import { getAccounts } from '@/api/accounts'
import { getTools } from '@/api/tools'
import type { Account, Reservation, ReservationOccupiedSlot, Tool } from '@/types'
import { useAuthStore } from '@/stores/auth'
import { useProjectContextStore } from '@/stores/project-context'
import { getProjectDisplayName } from '@/utils/project'
import {
  buildTimeGridSelectionRange,
  ceilMinuteToStep,
  getNormalizedTimeGridDuration,
  getTimeGridSelectionStepMinutes,
  isCountBasedPriceType,
  isSelectableTimeGridBoundary,
  isTimeGridSelectionRangeValid,
  isHourlyPriceType,
  TIME_GRID_STEP_MINUTES
} from '@/utils/reservation-time'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()
const projectContextStore = useProjectContextStore()

const TIME_GRID_SLOT_COUNT = 1440 / TIME_GRID_STEP_MINUTES
const TIME_DAY_SLOT_HEIGHT = 18
const COUNT_BASED_AVAILABILITY_DAYS = 365

const formRef = ref<FormInstance>()
const tools = ref<Tool[]>([])
const accounts = ref<Account[]>([])
const loadingTools = ref(false)
const loadingAccounts = ref(false)
const submitting = ref(false)

const reservationDate = ref('')
const selectedTimeRange = ref<[number, number] | null>(null)
const timeGridDraftRange = ref<[number, number]>([540, 600])
const timeGridAnchorStart = ref<number | null>(null)
const reservedReservations = ref<ReservationOccupiedSlot[]>([])
const countBasedReservationsByDate = ref<Record<string, number>>({})
const nowTick = ref(dayjs())

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

const formRules: FormRules = {
  tool_id: [{ required: true, message: '请选择仪器', trigger: 'change' }],
  payer_account_id: [{ required: true, message: '请选择结算账户', trigger: 'change' }],
  start: [{ required: true, message: '请选择日期与时间', trigger: 'change' }],
  end: [{ required: true, message: '请选择日期与时间', trigger: 'change' }]
}

const currentProjectName = computed(() => projectContextStore.currentProjectName || '')
const selectedTool = computed(() => tools.value.find((item) => item.id === formData.tool_id))
const selectedPayerAccount = computed(() => accounts.value.find((item) => item.id === formData.payer_account_id))
const isCountBasedTool = computed(() => isCountBasedPriceType(selectedTool.value?.price_type))
const requiresWholeHourSelection = computed(() => !!selectedTool.value && isHourlyPriceType(selectedTool.value.price_type))
const timeGridSelectionStepMinutes = computed(() => getTimeGridSelectionStepMinutes(requiresWholeHourSelection.value))
const dailyReservationQuota = computed(() => {
  const rawQuota = Number(selectedTool.value?.maximum_reservations_per_day || 0)
  return rawQuota > 0 ? rawQuota : 0
})
const selectedToolProjectName = computed(() => {
  const tool = selectedTool.value
  const toolProjectName = getProjectDisplayName(tool?.project)
  if (toolProjectName) return toolProjectName
  const toolProjectId = tool?.project_id ?? tool?.project?.id
  if (toolProjectId && projectContextStore.currentProjectId === toolProjectId) {
    return projectContextStore.currentProjectName
  }
  return ''
})
const canOpenDateTimeSelector = computed(() => !!formData.tool_id && !!formData.project_id)
const selectedDateReservationCount = computed(() => {
  if (!reservationDate.value) return 0
  return Number(countBasedReservationsByDate.value[reservationDate.value] || 0)
})
const selectedDateRemainingCount = computed(() => {
  if (dailyReservationQuota.value <= 0) return null
  return Math.max(dailyReservationQuota.value - selectedDateReservationCount.value, 0)
})
const isSelectedDateQuotaFull = computed(() => {
  return isCountBasedTool.value && dailyReservationQuota.value > 0 && selectedDateReservationCount.value >= dailyReservationQuota.value
})
const hasDateTimeSelected = computed(() => !!formData.start && !!formData.end)
const summaryTagType = computed(() => {
  if (isCountBasedTool.value && isSelectedDateQuotaFull.value) return 'danger'
  return hasDateTimeSelected.value ? 'success' : 'info'
})
const summaryTagText = computed(() => {
  if (isCountBasedTool.value && isSelectedDateQuotaFull.value) return '当日已满'
  return hasDateTimeSelected.value ? '已选择' : '待选择'
})
const nowTimeLabel = computed(() => nowTick.value.format('HH:mm'))
const timeGridTipText = computed(() => {
  if (requiresWholeHourSelection.value) {
    return '按小时计费仅支持整点起止；先点击起始整点，再点击结束整点'
  }
  return '点击起始格子，再点击结束格子（每格 15 分钟）'
})

const selectedTimeRangeText = computed(() => {
  if (isCountBasedTool.value) {
    return reservationDate.value ? '按次预约（按天）' : ''
  }
  if (!selectedTimeRange.value) return ''
  return `${formatTimeFromMinutes(selectedTimeRange.value[0])} - ${formatTimeFromMinutes(selectedTimeRange.value[1])}`
})

const selectedDurationText = computed(() => {
  if (isCountBasedTool.value) {
    return reservationDate.value ? '1 次' : ''
  }
  if (!selectedTimeRange.value) return ''
  return formatDuration(selectedTimeRange.value[1] - selectedTimeRange.value[0])
})

const selectedDateTimeLabel = computed(() => {
  if (isCountBasedTool.value) {
    if (!reservationDate.value) {
      return '请先选择预约日期'
    }
    if (isSelectedDateQuotaFull.value) {
      return `${formatReservationDate(reservationDate.value)}（当天预约次数已满）`
    }
    return `${formatReservationDate(reservationDate.value)}（按次预约）`
  }
  if (reservationDate.value && timeGridAnchorStart.value !== null && !selectedTimeRange.value) {
    return `${formatReservationDate(reservationDate.value)} ${formatTimeFromMinutes(timeGridAnchorStart.value)} 起，请继续选择结束时间`
  }
  if (!reservationDate.value || !selectedTimeRange.value) {
    return '请在下方 Day 时间轴中选择时间段'
  }
  return `${formatReservationDate(reservationDate.value)} ${selectedTimeRangeText.value}`
})

const earliestSelectableMinute = computed(() => {
  if (!reservationDate.value) return 0
  const selectedDay = dayjs(reservationDate.value).startOf('day')
  const now = nowTick.value
  if (selectedDay.isAfter(now, 'day')) return 0
  if (selectedDay.isBefore(now, 'day')) return 1440
  const currentMinute = now.diff(selectedDay, 'minute')
  return ceilMinuteToStep(currentMinute, timeGridSelectionStepMinutes.value)
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
        endMin
      }
    })
    .filter(Boolean) as Array<{ id: number; startMin: number; endMin: number }>
})

const timePickerNowLineVisible = computed(() => {
  if (!reservationDate.value) return false
  return dayjs(reservationDate.value).isSame(nowTick.value, 'day')
})

const timePickerNowLineStyle = computed(() => {
  if (!timePickerNowLineVisible.value || !reservationDate.value) {
    return {}
  }
  const selectedDay = dayjs(reservationDate.value).startOf('day')
  const currentMinute = Math.min(Math.max(nowTick.value.diff(selectedDay, 'minute'), 0), 1440)
  return {
    top: `${currentMinute / TIME_GRID_STEP_MINUTES * TIME_DAY_SLOT_HEIGHT}px`
  }
})

const timeGridCurrentText = computed(() => {
  if (!selectedTimeRange.value && timeGridAnchorStart.value === null) {
    return '当前尚未选择时间段'
  }
  return `${formatTimeFromMinutes(timeGridDraftRange.value[0])} - ${formatTimeFromMinutes(timeGridDraftRange.value[1])}`
})

const formatTimeFromMinutes = (minutes: number) => {
  const hours = Math.floor(minutes / 60)
  const mins = minutes % 60
  return `${hours.toString().padStart(2, '0')}:${mins.toString().padStart(2, '0')}`
}

const formatDuration = (minutes: number) => {
  const h = Math.floor(minutes / 60)
  const m = minutes % 60
  if (h > 0) return `${h}小时${m > 0 ? ` ${m}分钟` : ''}`
  return `${m}分钟`
}

const formatReservationDate = (value: string) => dayjs(value).format('YYYY年MM月DD日')

const isReservationDateDisabled = (date: Date) => {
  const dateKey = dayjs(date).format('YYYY-MM-DD')
  if (dayjs(date).isBefore(dayjs().startOf('day'))) {
    return true
  }
  if (!isCountBasedTool.value || dailyReservationQuota.value <= 0) {
    return false
  }
  return Number(countBasedReservationsByDate.value[dateKey] || 0) >= dailyReservationQuota.value
}

const isTimeRangeAvailable = (range: [number, number]) => {
  if (!isTimeGridSelectionRangeValid(range, requiresWholeHourSelection.value)) {
    return false
  }
  if (range[0] < earliestSelectableMinute.value) {
    return false
  }
  return !reservedBlocks.value.some((block) => range[0] < block.endMin && range[1] > block.startMin)
}

const findFirstAvailableRange = () => {
  const duration = selectedTimeRange.value
    ? selectedTimeRange.value[1] - selectedTimeRange.value[0]
    : timeGridSelectionStepMinutes.value
  const safeDuration = getNormalizedTimeGridDuration(duration, requiresWholeHourSelection.value)
  for (
    let start = earliestSelectableMinute.value;
    start + safeDuration <= 1440;
    start += timeGridSelectionStepMinutes.value
  ) {
    const candidate: [number, number] = [start, start + safeDuration]
    if (isTimeRangeAvailable(candidate)) return candidate
  }
  return null
}

const isTimeGridSlotReserved = (startMin: number, endMin: number) => {
  return reservedBlocks.value.some((block) => startMin < block.endMin && endMin > block.startMin)
}

const isTimeGridSlotDisabled = (startMin: number, endMin: number) => {
  if (startMin < earliestSelectableMinute.value) {
    return true
  }
  return !isSelectableTimeGridBoundary({
    anchorStart: timeGridAnchorStart.value,
    startMin,
    endMin,
    requiresWholeHourSelection: requiresWholeHourSelection.value
  })
}

const isTimeGridSlotSelected = (startMin: number, endMin: number) => {
  if (!selectedTimeRange.value && timeGridAnchorStart.value === null) {
    return false
  }
  return startMin < timeGridDraftRange.value[1] && endMin > timeGridDraftRange.value[0]
}

const isTimeGridSlotAnchor = (startMin: number) => {
  return timeGridAnchorStart.value === startMin
}

const syncTimeRangeToForm = (range: [number, number]) => {
  const start = dayjs(reservationDate.value).startOf('day').add(range[0], 'minute')
  const end = dayjs(reservationDate.value).startOf('day').add(range[1], 'minute')
  formData.start = start.format('YYYY-MM-DD HH:mm:ss')
  formData.end = end.format('YYYY-MM-DD HH:mm:ss')
}

const clearSelectedDateTime = () => {
  selectedTimeRange.value = null
  formData.start = ''
  formData.end = ''
}

const syncCountBasedReservationToForm = () => {
  if (!reservationDate.value) {
    formData.start = ''
    formData.end = ''
    return
  }
  const start = dayjs(reservationDate.value).startOf('day')
  const end = dayjs(reservationDate.value).endOf('day')
  formData.start = start.format('YYYY-MM-DD HH:mm:ss')
  formData.end = end.format('YYYY-MM-DD HH:mm:ss')
}

const findNextAvailableCountBasedDate = () => {
  const baseDay = reservationDate.value && !dayjs(reservationDate.value).isBefore(dayjs(), 'day')
    ? dayjs(reservationDate.value)
    : dayjs().startOf('day')

  for (let offset = 0; offset <= COUNT_BASED_AVAILABILITY_DAYS; offset += 1) {
    const candidate = baseDay.add(offset, 'day')
    if (!isReservationDateDisabled(candidate.toDate())) {
      return candidate.format('YYYY-MM-DD')
    }
  }

  return ''
}

const loadCountBasedAvailability = async () => {
  countBasedReservationsByDate.value = {}
  if (!formData.tool_id || !formData.project_id || !isCountBasedTool.value) {
    return
  }
  try {
    const startDate = dayjs().startOf('day')
    const endDate = startDate.add(COUNT_BASED_AVAILABILITY_DAYS, 'day').endOf('day')
    const response = await getReservations({
      tool_id: Number(formData.tool_id),
      start_date: startDate.format('YYYY-MM-DD HH:mm:ss'),
      end_date: endDate.format('YYYY-MM-DD HH:mm:ss'),
      include_all: true,
      limit: 5000,
    })
    const reservations = Array.isArray(response)
      ? response
      : (((response as any)?.data || []) as Reservation[])
    const nextMap: Record<string, number> = {}
    reservations.forEach((item) => {
      if (item.cancelled) return
      const dayKey = dayjs(item.start).format('YYYY-MM-DD')
      nextMap[dayKey] = (nextMap[dayKey] || 0) + 1
    })
    countBasedReservationsByDate.value = nextMap
  } catch (error) {
    console.error('加载按次预约可用日期失败:', error)
    ElMessage.error('加载按次预约可用日期失败')
  }
}

const ensureCountBasedReservationDate = () => {
  if (!isCountBasedTool.value) return
  if (reservationDate.value && !isReservationDateDisabled(dayjs(reservationDate.value).toDate())) {
    syncCountBasedReservationToForm()
    return
  }
  reservationDate.value = findNextAvailableCountBasedDate()
  syncCountBasedReservationToForm()
}

const loadTools = async () => {
  loadingTools.value = true
  try {
    const response = await getTools({ skip: 0, limit: 1000 })
    tools.value = Array.isArray(response) ? response : (response as any)?.data || []
  } catch (error) {
    console.error('加载仪器失败:', error)
    ElMessage.error('加载仪器失败')
  } finally {
    loadingTools.value = false
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

const loadAccounts = async () => {
  loadingAccounts.value = true
  try {
    const currentProjectId = projectContextStore.currentProjectId
    const effectiveUserId = Number(formData.user_id || authStore.user?.id || 0)
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
    console.error('加载账户失败:', error)
    ElMessage.error('加载账户失败')
  } finally {
    loadingAccounts.value = false
  }
}

const getAccountOptionLabel = (account: Account) => account.name

const loadReservedReservations = async () => {
  if (isCountBasedTool.value || !formData.tool_id || !reservationDate.value) {
    reservedReservations.value = []
    return
  }
  try {
    const startDate = dayjs(reservationDate.value).startOf('day').format('YYYY-MM-DD HH:mm:ss')
    const endDate = dayjs(reservationDate.value).endOf('day').format('YYYY-MM-DD HH:mm:ss')
    reservedReservations.value = await getOccupiedReservationSlots({
      tool_id: Number(formData.tool_id),
      start_date: startDate,
      end_date: endDate
    })
  } catch (error) {
    console.error('加载已预约时段失败:', error)
    ElMessage.error('加载已预约时段失败')
  }
}

const prepareTimeDraftRange = () => {
  const baseRange =
    selectedTimeRange.value && isTimeRangeAvailable(selectedTimeRange.value)
      ? selectedTimeRange.value
      : findFirstAvailableRange()

  if (baseRange) {
    timeGridDraftRange.value = [...baseRange]
    return
  }

  const step = timeGridSelectionStepMinutes.value
  const baseStart = Math.min(Math.max(earliestSelectableMinute.value, 0), 1440 - step)
  timeGridDraftRange.value = [baseStart, baseStart + step]
}

const applyRouteDefaults = async () => {
  const queryToolId = Number(route.query.toolId)
  const matchedTool = Number.isFinite(queryToolId) ? tools.value.find((item) => item.id === queryToolId) : null
  if (matchedTool) {
    formData.tool_id = matchedTool.id
    formData.project_id = matchedTool.project_id ?? matchedTool.project?.id ?? undefined
  }

  const queryDate = typeof route.query.date === 'string' ? route.query.date : ''
  if (queryDate && dayjs(queryDate, 'YYYY-MM-DD', true).isValid() && !dayjs(queryDate).isBefore(dayjs(), 'day')) {
    reservationDate.value = queryDate
  } else {
    reservationDate.value = dayjs().format('YYYY-MM-DD')
  }

  if (formData.tool_id && reservationDate.value) {
    if (isCountBasedTool.value) {
      await loadCountBasedAvailability()
      ensureCountBasedReservationDate()
      reservedReservations.value = []
      return
    }
    await loadReservedReservations()
    prepareTimeDraftRange()
  }
}

const handleToolChange = async () => {
  const tool = selectedTool.value
  formData.project_id = tool?.project_id ?? tool?.project?.id ?? undefined
  clearSelectedDateTime()
  countBasedReservationsByDate.value = {}
  if (!formData.project_id && formData.tool_id) {
    ElMessage.warning('该仪器未绑定项目，暂时无法创建预约')
  }
  if (reservationDate.value) {
    if (isCountBasedTool.value) {
      await loadCountBasedAvailability()
      ensureCountBasedReservationDate()
      reservedReservations.value = []
      return
    }
    await loadReservedReservations()
    prepareTimeDraftRange()
  }
}

const handleReservationDateChange = async () => {
  clearSelectedDateTime()
  timeGridAnchorStart.value = null
  if (!formData.tool_id || !formData.project_id) {
    reservedReservations.value = []
    countBasedReservationsByDate.value = {}
    prepareTimeDraftRange()
    return
  }
  if (isCountBasedTool.value) {
    syncCountBasedReservationToForm()
    return
  }
  await loadReservedReservations()
  prepareTimeDraftRange()
}

const handleTimeGridSlotClick = (startMin: number, endMin: number) => {
  if (isTimeGridSlotDisabled(startMin, endMin) || isTimeGridSlotReserved(startMin, endMin)) {
    return
  }
  if (timeGridAnchorStart.value === null) {
    timeGridAnchorStart.value = startMin
    const initialRange: [number, number] = [
      startMin,
      Math.min(startMin + timeGridSelectionStepMinutes.value, 1440)
    ]
    timeGridDraftRange.value = initialRange
    selectedTimeRange.value = null
    formData.start = ''
    formData.end = ''
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
  selectedTimeRange.value = candidateRange
  syncTimeRangeToForm(candidateRange)
  timeGridAnchorStart.value = null
}

const resetTimeGridAnchor = () => {
  timeGridAnchorStart.value = null
}

const clearTimeSelection = () => {
  timeGridAnchorStart.value = null
  clearSelectedDateTime()
  if (isCountBasedTool.value) {
    syncCountBasedReservationToForm()
    return
  }
  prepareTimeDraftRange()
}

const goBack = () => {
  const from = typeof route.query.from === 'string' ? route.query.from : ''
  router.push(from === 'calendar' ? '/calendar' : '/reservations')
}

const handleSubmit = async () => {
  if (!formRef.value) return

  if (isCountBasedTool.value) {
    if (!reservationDate.value) {
      ElMessage.error('请选择预约日期')
      return
    }
    await loadCountBasedAvailability()
    if (isSelectedDateQuotaFull.value) {
      ElMessage.error('当天预约次数已满，无法继续预约')
      return
    }
    syncCountBasedReservationToForm()
  } else {
    await loadReservedReservations()
  }

  await formRef.value.validate(async (valid) => {
    if (!valid) return

    if (!formData.project_id) {
      ElMessage.error('当前仪器未绑定项目，无法创建预约')
      return
    }
    if (!formData.start || !formData.end) {
      ElMessage.error(isCountBasedTool.value ? '请选择预约日期' : '请选择日期与时间')
      return
    }

    if (isCountBasedTool.value) {
      if (dayjs(reservationDate.value).isBefore(dayjs(), 'day')) {
        ElMessage.error('预约日期不能早于今天')
        return
      }
      if (isSelectedDateQuotaFull.value) {
        ElMessage.error('当天预约次数已满，无法继续预约')
        return
      }
    } else {
      if (!dayjs(formData.end).isAfter(dayjs(formData.start))) {
        ElMessage.error('结束时间必须晚于开始时间')
        return
      }
      if (dayjs(formData.start).isBefore(dayjs())) {
        ElMessage.error('开始时间不能早于当前时间')
        return
      }
      if (!selectedTimeRange.value || !isTimeRangeAvailable(selectedTimeRange.value)) {
        ElMessage.error('该时间段不可预约（可能已被预约或早于当前时间）')
        return
      }
    }

    submitting.value = true
    try {
      await createReservation(formData)
      ElMessage.success('创建成功')
      goBack()
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
      } else if (error?.response?.status === 409) {
        ElMessage.error('该时间段已被预约')
      } else {
        ElMessage.error('创建失败')
      }
      console.error(error)
    } finally {
      submitting.value = false
    }
  })
}

let nowTickTimer: number | undefined

onMounted(async () => {
  if (!projectContextStore.currentProjectId) {
    projectContextStore.hydrate()
  }
  await Promise.all([loadTools(), loadAccounts()])
  await applyRouteDefaults()
  nowTickTimer = window.setInterval(() => {
    nowTick.value = dayjs()
  }, 60 * 1000)
})

onUnmounted(() => {
  if (nowTickTimer) {
    window.clearInterval(nowTickTimer)
  }
})

watch(
  () => route.query.toolId,
  async () => {
    await applyRouteDefaults()
  }
)
</script>

<style scoped>
.reservation-create-page {
  padding: 18px;
}

.reservation-create-shell {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  padding: 22px 24px;
  border-radius: 24px;
  background:
    radial-gradient(circle at top left, rgba(37, 99, 235, 0.16), transparent 34%),
    linear-gradient(135deg, #ffffff 0%, #f8fbff 55%, #f1f6ff 100%);
  border: 1px solid #dfe8f7;
  box-shadow: 0 16px 36px rgba(15, 23, 42, 0.06);
}

.page-kicker {
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: #2563eb;
}

.page-title {
  margin: 8px 0 6px;
  font-size: 30px;
  line-height: 1.08;
  font-weight: 700;
  color: #0f172a;
}

.page-subtitle {
  margin: 0;
  max-width: 560px;
  font-size: 14px;
  line-height: 1.6;
  color: #475569;
}

.create-card,
.summary-card {
  border-radius: 20px;
  border: 1px solid #dfe7f3;
  box-shadow: 0 12px 30px rgba(15, 23, 42, 0.05);
}

.summary-card {
  position: sticky;
  top: 18px;
  max-height: calc(100vh - 36px);
  overflow: auto;
}

.create-card :deep(.el-card__body),
.summary-card :deep(.el-card__body) {
  padding: 16px;
}

.create-form :deep(.el-form-item__label) {
  font-size: 13px;
  font-weight: 700;
  color: #334155;
}

.create-form :deep(.el-form-item) {
  margin-bottom: 16px;
}

.form-inline-row {
  margin-bottom: 16px;
}

.form-inline-row :deep(.el-form-item) {
  margin-bottom: 0;
}

.count-based-date-status {
  margin-top: 8px;
  font-size: 12px;
  line-height: 1.6;
  color: #2f6b2f;
}

.count-based-date-status.full {
  color: #b42318;
}

.inline-day-calendar-section {
  margin-bottom: 16px;
  padding: 14px;
  border-radius: 16px;
  background: linear-gradient(180deg, #f8fbff 0%, #ffffff 100%);
}

.count-based-board {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 8px 2px 2px;
}

.count-based-stat-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.count-based-stat-card {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 14px;
  border-radius: 14px;
  background: #f8fafc;
  border: 1px solid #dbe4ef;
}

.count-based-stat-card.danger {
  background: #fff4f2;
  border-color: #f3b3ab;
}

.count-based-stat-label {
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: #64748b;
}

.count-based-stat-value {
  font-size: 18px;
  font-weight: 700;
  color: #0f172a;
}

.count-based-selected-date {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 14px;
  border-radius: 14px;
  background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
  border: 1px solid #dbe4ef;
}

.count-based-selected-date-label {
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #64748b;
}

.count-based-selected-date-value {
  font-size: 14px;
  font-weight: 600;
  color: #0f172a;
}

.selected-time-panel {
  display: flex;
  flex-direction: column;
  gap: 6px;
  width: 100%;
  min-height: 64px;
  padding: 12px 14px;
  border-radius: 14px;
  border: 1px solid #dbe4ef;
  background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
}

.selected-time-value {
  font-size: 15px;
  font-weight: 600;
  color: #0f172a;
}

.selected-time-helper {
  font-size: 12px;
  color: #64748b;
}

.field-helper {
  margin-top: 8px;
  font-size: 12px;
  color: #64748b;
  line-height: 1.5;
}

.project-display {
  display: flex;
  align-items: center;
  gap: 10px;
  min-height: 46px;
  padding: 0 14px;
  border-radius: 14px;
  background: #f8fafc;
  border: 1px solid #dbe4ef;
}

.project-display-label {
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #64748b;
}

.project-display-name {
  font-size: 14px;
  font-weight: 600;
  color: #0f172a;
}

.summary-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.summary-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-bottom: 14px;
}

.summary-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding-bottom: 10px;
  border-bottom: 1px solid #e8eef6;
}

.summary-label {
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #64748b;
}

.summary-value {
  font-size: 14px;
  font-weight: 600;
  color: #111827;
  word-break: break-word;
}

.summary-notes {
  margin-top: 14px;
  padding: 12px 14px;
  border-radius: 14px;
  background: #f8fafc;
  border: 1px solid #dbe4ef;
}

.summary-note-title {
  margin-bottom: 8px;
  font-size: 13px;
  font-weight: 700;
  color: #334155;
}

.summary-note-list {
  margin: 0;
  padding-left: 16px;
  color: #475569;
  font-size: 12px;
  line-height: 1.6;
}

.form-submit-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid rgba(219, 228, 239, 0.75);
}

.form-submit-hint {
  font-size: 13px;
  color: #64748b;
}

.day-calendar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;
}

.day-calendar-title {
  font-size: 16px;
  font-weight: 700;
  color: #0f172a;
}

.day-calendar-subtitle {
  margin-top: 4px;
  font-size: 12px;
  color: #64748b;
}

.day-calendar-empty {
  padding: 10px 0 4px;
}

.time-grid-tip {
  margin-bottom: 8px;
  font-size: 13px;
  color: #5f6368;
  font-weight: 500;
}

.time-grid-legend {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 8px;
  font-size: 12px;
  color: #606266;
  flex-wrap: wrap;
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
  background: #f8fafc;
  border: 1px solid #d7dde6;
}

.time-grid-dot-selected {
  background: #bfd3ff;
  border: 1px solid #98b5f6;
}

.time-grid-dot-reserved {
  background: #f7c3bd;
  border: 1px solid #e6a49e;
}

.time-grid-dot-disabled {
  background: #d8dee7;
  border: 1px solid #b8c1ce;
}

.time-day-board {
  border-radius: 14px;
  overflow: hidden;
  background: linear-gradient(180deg, #fbfcff 0%, #ffffff 100%);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.7);
}

.time-day-board-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 8px 10px;
  background: rgba(248, 250, 255, 0.9);
}

.time-day-board-date {
  margin-top: 2px;
  font-size: 13px;
  color: #374151;
  font-weight: 600;
}

.time-day-scroll {
  max-height: min(58vh, 560px);
  overflow-y: auto;
}

.time-day-grid {
  position: relative;
}

.time-day-row {
  display: grid;
  grid-template-columns: 70px 1fr;
  min-height: 18px;
}

.time-day-axis {
  position: relative;
  font-size: 11px;
  color: #8b96a7;
  text-align: right;
  padding-right: 10px;
  line-height: 1;
}

.time-day-axis span {
  position: absolute;
  top: -6px;
  right: 10px;
}

.time-day-slot {
  height: 18px;
  width: 100%;
  border: none;
  background: transparent;
  cursor: pointer;
  transition: background-color 0.15s ease;
}

.time-day-slot.major {
  border-top-color: transparent;
}

.time-day-slot.mid {
  border-top-color: transparent;
}

.time-day-slot:hover {
  background: rgba(191, 211, 255, 0.18);
}

.time-day-slot.selected {
  background: #d9e6ff;
}

.time-day-slot.anchor {
  box-shadow: inset 0 0 0 1.5px #6b7280;
}

.time-day-slot.reserved {
  background: #fde3df;
  cursor: not-allowed;
}

.time-day-slot.disabled {
  background: #eceff4;
  cursor: not-allowed;
}

.time-day-slot.reserved.disabled {
  background: #fde3df;
}

.time-day-now-line {
  position: absolute;
  left: 70px;
  right: 0;
  height: 2px;
  background: #ea4335;
  z-index: 2;
  pointer-events: none;
}

.time-day-now-line::before {
  content: '';
  position: absolute;
  left: -5px;
  top: 50%;
  width: 8px;
  height: 8px;
  border-radius: 999px;
  background: #ea4335;
  transform: translateY(-50%);
}

.time-day-now-label {
  position: absolute;
  left: 8px;
  top: -11px;
  padding: 2px 6px;
  border-radius: 999px;
  background: #ea4335;
  color: #ffffff;
  font-size: 10px;
  line-height: 1;
  box-shadow: 0 4px 10px rgba(234, 67, 53, 0.28);
}

.time-grid-current {
  margin-top: 0;
  font-size: 12px;
  color: #303133;
}

@media (max-width: 900px) {
  .reservation-create-page {
    padding: 12px;
  }

  .page-header {
    flex-direction: column;
    padding: 18px 16px;
  }

  .inline-day-calendar-section {
    padding: 12px;
  }

  .summary-card {
    position: static;
    top: auto;
    max-height: none;
    overflow: visible;
  }

  .form-submit-actions {
    flex-direction: column;
    align-items: stretch;
  }

  .form-submit-hint {
    text-align: center;
  }

  .page-title {
    font-size: 26px;
  }
}
</style>
