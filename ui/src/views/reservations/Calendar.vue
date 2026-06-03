<template>
  <div class="page-container">
    <!-- 顶部操作栏 -->
    <el-card class="header-card" shadow="never">
      <div class="toolbar-shell">
        <div class="toolbar-group toolbar-group-left">
          <el-button type="primary" :icon="Plus" @click="handleCreate">
            创建预约
          </el-button>
          <el-button :icon="List" @click="goToList">
            列表视图
          </el-button>
          <el-button :icon="Refresh" @click="loadReservations">
            刷新
          </el-button>
        </div>
        <div class="toolbar-group toolbar-group-right">
          <el-button type="primary" class="filter-tool-btn" @click="openFilterDialog">
            筛选仪器
          </el-button>
          <el-tag
            v-if="selectedToolName"
            type="success"
            effect="dark"
            class="filter-state-tag filter-state-tag-tool"
          >
            仪器：{{ selectedToolName }}
          </el-tag>
          <el-button v-if="hasToolSelected" type="warning" @click="clearFilter">
            清除筛选
          </el-button>
          <el-radio-group v-model="viewMode" class="view-mode-switch" @change="loadReservations">
            <el-radio-button value="year">年</el-radio-button>
            <el-radio-button value="month">月</el-radio-button>
            <el-radio-button value="week">周</el-radio-button>
            <el-radio-button value="day">日</el-radio-button>
          </el-radio-group>
        </div>
      </div>
    </el-card>

    <!-- 日历视图 -->
    <el-card class="calendar-card" shadow="never">
      <template #header>
        <div class="calendar-header">
          <el-space>
            <el-button :icon="ArrowLeft" @click="prevPeriod" />
            <el-button :icon="ArrowRight" @click="nextPeriod" />
            <el-button @click="today">今天</el-button>
          </el-space>
          <div class="current-date">{{ currentDateDisplay }}</div>
        </div>
      </template>
      <div v-if="hasToolSelected" class="calendar-overview">
        <div class="calendar-legend">
          <span
            v-for="legend in reservationLegend"
            :key="legend.key"
            class="legend-item"
          >
            <span class="legend-dot" :class="legend.key"></span>
            {{ legend.label }}
          </span>
        </div>
        <div class="calendar-summary">
          <el-tag size="small" type="info" effect="plain">
            总数 {{ visibleReservationSummary.total }}
          </el-tag>
          <el-tag size="small" type="success" effect="plain">
            进行中 {{ visibleReservationSummary.ongoing }}
          </el-tag>
          <el-tag size="small" effect="plain">
            未开始 {{ visibleReservationSummary.upcoming }}
          </el-tag>
        </div>
      </div>

      <div v-if="!hasToolSelected" class="calendar-empty">
        <el-empty description="请选择仪器后查看预约日历" />
      </div>

      <!-- 年视图 -->
      <div v-else-if="viewMode === 'year'" class="year-view">
        <div class="year-grid">
          <section
            v-for="month in yearMonths"
            :key="month.monthKey"
            class="year-month-card"
          >
            <button
              type="button"
              class="year-month-header"
              @click="openYearMonth(month.monthStart)"
            >
              <span class="year-month-title">{{ month.label }}</span>
              <span class="year-month-meta">{{ month.totalReservations }} 条</span>
            </button>
            <div class="year-weekdays">
              <span
                v-for="label in yearWeekdayLabels"
                :key="`${month.monthKey}-${label}`"
                class="year-weekday"
              >
                {{ label }}
              </span>
            </div>
            <div class="year-days">
              <el-popover
                v-for="day in month.days"
                :key="day.date"
                :disabled="day.reservationCount === 0"
                placement="top"
                trigger="hover"
                :show-after="120"
                :hide-after="80"
                :width="360"
                popper-class="day-reservations-popper year-day-reservations-popper"
              >
                <template #reference>
                  <button
                    type="button"
                    class="year-day-cell"
                    :class="{
                      today: day.isToday,
                      outside: !day.isCurrentMonth,
                      busy: day.reservationCount > 0
                    }"
                    :title="`${day.date}${day.reservationCount > 0 ? ` · ${day.reservationCount} 条预约` : ''}`"
                    @click="openYearDay(day.date)"
                  >
                    <span class="year-day-number">{{ day.label }}</span>
                    <span v-if="day.reservationCount > 0" class="year-day-dot"></span>
                  </button>
                </template>
                <div class="day-reservations-panel">
                  <div class="day-reservations-panel__header">
                    <div>
                      <strong>{{ dayjs(day.date).format('M月D日') }}</strong>
                      <span>{{ getDayLoadLabel(day.date) }}</span>
                    </div>
                    <button class="day-reservations-panel__link" @click="openYearDay(day.date)">日视图</button>
                  </div>
                  <div class="day-reservations-panel__list">
                    <button
                      v-for="(reservation, popoverIdx) in getReservationsForDate(day.date)"
                      :key="`year-day-popover-${reservation.id}`"
                      class="day-reservation-row"
                      :style="getReservationMonthStyle(reservation, popoverIdx)"
                      @click="handleViewDetail(reservation)"
                    >
                      <span class="day-reservation-row__accent"></span>
                      <span class="day-reservation-row__main">
                        <span class="day-reservation-row__time">
                          {{ formatTime(reservation.start) }} - {{ formatTime(reservation.end) }}
                        </span>
                        <span class="day-reservation-row__user">{{ getDisplayUserName(reservation) }}</span>
                      </span>
                      <span class="day-reservation-row__status">{{ getReservationStatusLabel(reservation) }}</span>
                    </button>
                  </div>
                </div>
              </el-popover>
            </div>
            <div class="year-month-footer">
              <span>{{ month.totalReservations }} 条预约</span>
              <span>{{ month.totalLoadLabel }}</span>
            </div>
          </section>
        </div>
      </div>

      <!-- 月视图 -->
      <el-calendar v-else-if="viewMode === 'month'" v-model="currentDate">
        <template #date-cell="{ data }">
          <div
            class="calendar-day"
            :class="{
              'is-today': isToday(data.day),
              'is-other-month': data.type !== 'current-month'
            }"
          >
            <div class="day-header">
              <div class="day-title-group">
                <div class="day-number">{{ data.day.split('-')[2] }}</div>
                <div v-if="isToday(data.day)" class="day-today-label">今日</div>
              </div>
              <el-popover
                v-if="getReservationsForDate(data.day).length > 3"
                placement="bottom-end"
                trigger="click"
                :width="360"
                popper-class="day-reservations-popper"
              >
                <template #reference>
                  <button class="day-load day-load--interactive" @click.stop>
                    <strong>{{ getReservationsForDate(data.day).length }}</strong>
                    <span>条</span>
                  </button>
                </template>
                <div class="day-reservations-panel">
                  <div class="day-reservations-panel__header">
                    <div>
                      <strong>{{ dayjs(data.day).format('M月D日') }}</strong>
                      <span>{{ getDayLoadLabel(data.day) }}</span>
                    </div>
                    <button class="day-reservations-panel__link" @click="openYearDay(data.day)">日视图</button>
                  </div>
                  <div class="day-reservations-panel__list">
                    <button
                      v-for="(reservation, popoverIdx) in getReservationsForDate(data.day)"
                      :key="`day-popover-${reservation.id}`"
                      class="day-reservation-row"
                      :style="getReservationMonthStyle(reservation, popoverIdx)"
                      @click="handleViewDetail(reservation)"
                    >
                      <span class="day-reservation-row__accent"></span>
                      <span class="day-reservation-row__main">
                        <span class="day-reservation-row__time">
                          {{ formatTime(reservation.start) }} - {{ formatTime(reservation.end) }}
                        </span>
                        <span class="day-reservation-row__user">{{ getDisplayUserName(reservation) }}</span>
                      </span>
                      <span class="day-reservation-row__status">{{ getReservationStatusLabel(reservation) }}</span>
                    </button>
                  </div>
                </div>
              </el-popover>
              <div v-else-if="getReservationsForDate(data.day).length > 0" class="day-load">
                <strong>{{ getReservationsForDate(data.day).length }}</strong>
                <span>条</span>
              </div>
            </div>
            <div v-if="isToday(data.day) || getReservationsForDate(data.day).length > 0" class="day-subline">
              {{ getDayLoadLabel(data.day) || '暂无预约' }}
            </div>
            <div class="reservations-container">
                <div
                  v-for="(reservation, idx) in getReservationsForDate(data.day).slice(0, 3)"
                  :key="reservation.id"
                  class="reservation-item"
                  :class="getReservationClass(reservation)"
                  :style="getReservationMonthStyle(reservation, idx)"
                  @click="handleViewDetail(reservation)"
                >
                <el-popover
                  placement="top-start"
                  trigger="hover"
                  :show-after="120"
                  :hide-after="80"
                  :width="320"
                  popper-class="reservation-hover-popper"
                >
                  <template #reference>
                    <div class="reservation-item-content">
                      <div class="reservation-item-accent"></div>
                      <div class="reservation-item-main">
                        <div class="reservation-item-time">
                          {{ formatTime(reservation.start) }} - {{ formatTime(reservation.end) }}
                        </div>
                        <div class="reservation-item-user">
                        {{ getDisplayUserName(reservation) }}
                        </div>
                      </div>
                    </div>
                  </template>
                  <div class="reservation-hover-card" :style="getReservationDetailStyle(reservation)">
                    <div class="reservation-hover-title">用户：{{ getDisplayUserName(reservation) }}</div>
                    <div class="reservation-hover-time">{{ getReservationDisplayDate(reservation) }}</div>
                    <div class="reservation-hover-row">状态：{{ getReservationStatusLabel(reservation) }}</div>
                    <div
                      v-if="canViewReservationDetails(reservation) && reservation.additional_information"
                      class="reservation-hover-row"
                    >
                      备注：{{ reservation.additional_information }}
                    </div>
                  </div>
                </el-popover>
              </div>
              <div
                v-if="getReservationsForDate(data.day).length > 3"
                class="reservation-more"
                @click.stop="openYearDay(data.day)"
              >
                <span>+{{ getReservationsForDate(data.day).length - 3 }} 条</span>
                <strong>查看当天</strong>
              </div>
            </div>
          </div>
        </template>
      </el-calendar>

      <!-- 周视图 -->
      <div v-else-if="viewMode === 'week'" class="timeline-view">
        <div class="timeline-header">
          <div class="time-column">时间</div>
          <div class="days-row">
            <div
              v-for="day in weekDays"
              :key="day.date"
              class="day-column"
              :class="{ today: isToday(day.date) }"
            >
              <div class="day-name">{{ day.name }}</div>
              <div class="day-date">
                <span class="day-date-badge">{{ day.dateNum }}</span>
              </div>
            </div>
          </div>
        </div>
        <div class="timeline-legend">
          <span
            v-for="legend in reservationLegend"
            :key="`timeline-${legend.key}`"
            class="legend-item"
          >
            <span class="legend-dot" :class="legend.key"></span>
            {{ legend.label }}
          </span>
        </div>
        <div class="timeline-body">
          <div class="time-column time-column-body">
            <div v-for="hour in 24" :key="hour" class="time-label-row">
              {{ `${hour - 1}:00` }}
            </div>
          </div>
          <div class="days-row">
            <div v-for="day in weekDays" :key="day.date" class="day-column">
              <div class="day-grid">
                <div v-for="hour in 24" :key="`line-${day.date}-${hour}`" class="hour-line" />
                <div v-if="isNowLineVisible(day.date)" class="now-line" :style="getNowLineStyle(day.date)">
                  <span class="now-line-label">{{ nowLabel }}</span>
                </div>
                <div
                  v-for="(reservation, idx) in getReservationsForDay(day.date)"
                  :key="reservation.id"
                  class="reservation-block"
                  :class="[getReservationClass(reservation), { 'occupied-by-others': isOccupiedByOthers(reservation) }]"
                  :style="{
                    ...getReservationBlockStyle(reservation, day.date),
                    ...getTimelineReservationColorStyle(reservation, idx)
                  }"
                  @click="handleViewDetail(reservation)"
                >
                  <el-tooltip :content="getTooltipContent(reservation)" placement="top">
                    <div class="reservation-block-content">
                      <div class="reservation-block-time">
                        {{ formatTime(reservation.start) }} - {{ formatTime(reservation.end) }}
                      </div>
                      <div class="reservation-block-user">
                        {{ getDisplayUserName(reservation) }}
                      </div>
                    </div>
                  </el-tooltip>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 日视图 -->
      <div v-else class="calendar-day-view">
        <div class="timeline-legend day-view-legend">
          <span
            v-for="legend in reservationLegend"
            :key="`day-${legend.key}`"
            class="legend-item"
          >
            <span class="legend-dot" :class="legend.key"></span>
            {{ legend.label }}
          </span>
        </div>
        <div class="time-day-board calendar-day-board">
          <div class="time-day-board-header">
            <div class="calendar-day-board-title-group">
              <div class="calendar-day-board-title">{{ dayjs(currentDate).format('dddd') }}</div>
              <div class="time-day-board-date">{{ currentDateDisplay }}</div>
            </div>
            <el-tag size="small" effect="plain" class="calendar-day-board-tag">
              {{ selectedToolName || '未选择仪器' }}
            </el-tag>
          </div>
          <div class="time-day-scroll calendar-day-scroll">
            <div class="calendar-day-grid">
              <div
                v-for="slot in timeGridSlots"
                :key="`calendar-day-slot-${slot.index}`"
                class="time-day-row"
              >
                <div class="time-day-axis">
                  <span v-if="slot.showLabel">{{ slot.label }}</span>
                </div>
                <div class="calendar-day-slot-surface"></div>
              </div>
              <div
                v-if="isNowLineVisible(currentDate)"
                class="time-day-now-line"
                :style="getCalendarDayNowLineStyle(currentDate)"
              >
                <span class="time-day-now-label">{{ nowLabel }}</span>
              </div>
              <div
                v-for="(reservation, idx) in getReservationsForDay(currentDate)"
                :key="`calendar-day-${reservation.id}`"
                class="reservation-block calendar-day-reservation"
                :class="[getReservationClass(reservation), { 'occupied-by-others': isOccupiedByOthers(reservation) }]"
                :style="{
                  ...getReservationBlockStyle(reservation, currentDate),
                  ...getTimelineReservationColorStyle(reservation, idx)
                }"
                @click="handleViewDetail(reservation)"
              >
                <el-tooltip :content="getTooltipContent(reservation)" placement="top">
                  <div class="reservation-block-content">
                    <div class="reservation-block-time">
                      {{ formatTime(reservation.start) }} - {{ formatTime(reservation.end) }}
                    </div>
                    <div class="reservation-block-user">
                      {{ getDisplayUserName(reservation) }}
                    </div>
                  </div>
                </el-tooltip>
              </div>
            </div>
          </div>
        </div>
      </div>
    </el-card>

    <!-- 预约详情对话框 -->
    <el-dialog
      v-model="detailDialogVisible"
      width="720px"
      class="reservation-detail-dialog"
      :show-close="false"
    >
      <div
        v-if="selectedReservation"
        class="reservation-detail-card"
        :style="getReservationDetailStyle(selectedReservation)"
      >
        <div class="reservation-detail-hero">
          <span class="reservation-detail-marker"></span>
          <div class="reservation-detail-heading">
            <div class="reservation-detail-title">
              {{ getReservationDisplayTitle(selectedReservation) }}
            </div>
            <div class="reservation-detail-subtitle">
              {{ getReservationDisplayDate(selectedReservation) }}
            </div>
          </div>
          <div class="reservation-detail-top-right">
            <el-tag
              class="reservation-detail-status-tag"
              :type="getReservationStatusTagType(selectedReservation)"
              effect="light"
              round
            >
              {{ getReservationStatusLabel(selectedReservation) }}
            </el-tag>
            <div class="reservation-detail-actions">
              <el-button
                class="reservation-detail-icon-btn"
                circle
                :icon="Delete"
                :disabled="selectedReservation?.cancelled || isPast(selectedReservation) || !canViewReservationDetails(selectedReservation)"
                @click="handleCancel(selectedReservation!)"
              />
              <el-button
                class="reservation-detail-icon-btn"
                circle
                :icon="MoreFilled"
                @click="showReservationMoreActions(selectedReservation!)"
              />
              <el-button
                class="reservation-detail-icon-btn"
                circle
                :icon="CloseBold"
                @click="detailDialogVisible = false"
              />
            </div>
          </div>
        </div>

        <div class="reservation-detail-content">
          <div class="reservation-detail-grid">
            <div class="reservation-detail-field">
              <span class="reservation-detail-label">仪器</span>
              <span class="reservation-detail-value">{{ selectedReservation.tool?.name || '-' }}</span>
            </div>
            <div class="reservation-detail-field">
              <span class="reservation-detail-label">预约编号</span>
              <span class="reservation-detail-value">#{{ selectedReservation.id }}</span>
            </div>
            <div class="reservation-detail-field">
              <span class="reservation-detail-label">用户</span>
              <span class="reservation-detail-value">{{ getDisplayUserName(selectedReservation) }}</span>
            </div>
            <div class="reservation-detail-field">
              <span class="reservation-detail-label">项目</span>
              <span class="reservation-detail-value">{{ getDisplayProjectName(selectedReservation) }}</span>
            </div>
            <div class="reservation-detail-field">
              <span class="reservation-detail-label">开始时间</span>
              <span class="reservation-detail-value">{{ formatDateTime(selectedReservation.start) }}</span>
            </div>
            <div class="reservation-detail-field">
              <span class="reservation-detail-label">结束时间</span>
              <span class="reservation-detail-value">{{ formatDateTime(selectedReservation.end) }}</span>
            </div>
            <div class="reservation-detail-field">
              <span class="reservation-detail-label">自行配置</span>
              <span class="reservation-detail-value">
                {{
                  canViewReservationDetails(selectedReservation)
                    ? (selectedReservation?.self_configuration ? '是' : '否')
                    : '保密'
                }}
              </span>
            </div>
            <div class="reservation-detail-field reservation-detail-field-wide">
              <span class="reservation-detail-label">备注</span>
              <span class="reservation-detail-value reservation-detail-note">
                {{
                  canViewReservationDetails(selectedReservation)
                    ? (selectedReservation?.additional_information || '无')
                    : '保密'
                }}
              </span>
            </div>
          </div>
        </div>
      </div>
      <template #footer>
        <el-space class="reservation-detail-footer">
          <el-button @click="detailDialogVisible = false">关闭</el-button>
          <el-button
            type="primary"
            :icon="Edit"
            :disabled="selectedReservation?.cancelled || isPast(selectedReservation) || !canViewReservationDetails(selectedReservation)"
            @click="handleEdit(selectedReservation!)"
          >
            编辑
          </el-button>
          <el-button
            type="danger"
            :icon="Delete"
            :disabled="selectedReservation?.cancelled || isPast(selectedReservation) || !canViewReservationDetails(selectedReservation)"
            @click="handleCancel(selectedReservation!)"
          >
            取消预约
          </el-button>
        </el-space>
      </template>
    </el-dialog>

    <!-- 创建/编辑对话框 -->
    <el-dialog
      v-model="formDialogVisible"
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
            :model-value="selectedFormToolProjectName"
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
        <el-button @click="formDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">
          确定
        </el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="timePickerDialogVisible"
      title="选择预约时间段"
      width="760px"
      top="6vh"
      class="google-day-time-dialog"
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
      <div class="time-day-board">
        <div class="time-day-board-header">
          <div class="time-day-board-date">{{ reservationDateDisplay }}</div>
          <el-tag size="small" effect="plain">Day View</el-tag>
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
              <span class="time-day-now-label">{{ nowLabel }}</span>
            </div>
          </div>
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

    <!-- 筛选仪器对话框 -->
    <el-dialog
      v-model="filterDialogVisible"
      title="筛选仪器"
      width="420px"
    >
      <el-form label-width="100px">
        <el-form-item label="仪器" required>
          <el-select
            v-model="filterToolId"
            placeholder="请选择仪器"
            filterable
            style="width: 100%"
          >
            <el-option
              v-for="tool in tools"
              :key="tool.id"
              :label="tool.name"
              :value="tool.id"
            />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="filterDialogVisible = false">取消</el-button>
        <el-button type="warning" @click="clearFilter">清除筛选</el-button>
        <el-button type="primary" @click="applyFilter">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import {
  Plus,
  List,
  Refresh,
  Edit,
  Delete,
  MoreFilled,
  CloseBold,
  ArrowLeft,
  ArrowRight
} from '@element-plus/icons-vue'
import {
  getReservations,
  getOccupiedReservationSlots,
  createReservation,
  updateReservation,
  cancelReservation
} from '@/api/reservations'
import { getAccounts } from '@/api/accounts'
import { getTools } from '@/api/tools'
import { getProjects } from '@/api/projects'
import type { Account, Reservation, ReservationOccupiedSlot, Tool, Project } from '@/types'
import { formatDateTime } from '@/utils/helpers'
import { useAuthStore } from '@/stores/auth'
import { getProjectDisplayName } from '@/utils/project'
import { useProjectContextStore } from '@/stores/project-context'
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
import isoWeek from 'dayjs/plugin/isoWeek'
import weekday from 'dayjs/plugin/weekday'

dayjs.extend(isoWeek)
dayjs.extend(weekday)

const router = useRouter()
const authStore = useAuthStore()
const projectContextStore = useProjectContextStore()

// 预约时间相关
const reservationDate = ref(dayjs().format('YYYY-MM-DD'))
const timeRange = ref<[number, number]>([540, 600]) // Default 9:00 - 10:00

const TIME_GRID_SLOT_COUNT = 1440 / TIME_GRID_STEP_MINUTES
const TIME_DAY_SLOT_HEIGHT = 18

const HOUR_HEIGHT = TIME_DAY_SLOT_HEIGHT * 4
const MINUTE_HEIGHT = HOUR_HEIGHT / 60
const nowTick = ref(dayjs())
let nowTickTimer: number | null = null

const reservationLegend = [
  { key: 'ongoing', label: '进行中' },
  { key: 'upcoming', label: '未开始' },
  { key: 'past', label: '已结束' },
  { key: 'cancelled', label: '已取消' },
  { key: 'missed', label: '已错过' }
]

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

type ReservationTone = {
  accent: string
  background: string
  text: string
  border: string
}

const STATUS_COLOR_PALETTES: Record<string, ReservationTone[]> = {
  upcoming: [
    { accent: '#1a73e8', background: '#d2e3fc', text: '#174ea6', border: '#aecbfa' },
    { accent: '#1967d2', background: '#e8f0fe', text: '#185abc', border: '#c6dafc' },
    { accent: '#0b57d0', background: '#dbe8ff', text: '#0b57d0', border: '#b9d0ff' },
    { accent: '#4f46e5', background: '#e6e9ff', text: '#3730a3', border: '#c7d2fe' },
    { accent: '#0284c7', background: '#dff4ff', text: '#075985', border: '#b6e6ff' }
  ],
  ongoing: [
    { accent: '#188038', background: '#ceead6', text: '#137333', border: '#9ed2ae' },
    { accent: '#0f9d58', background: '#d7f5e3', text: '#0b8043', border: '#a8e1bf' },
    { accent: '#34a853', background: '#e2f4ea', text: '#1e8e3e', border: '#b7e1c3' }
  ],
  past: [
    { accent: '#5f6368', background: '#eceff1', text: '#3c4043', border: '#dadce0' },
    { accent: '#80868b', background: '#f1f3f4', text: '#5f6368', border: '#e0e3e7' },
    { accent: '#6b7280', background: '#eef2f7', text: '#4b5563', border: '#d7dee7' }
  ],
  cancelled: [
    { accent: '#f29900', background: '#fef0c7', text: '#b45309', border: '#fbd38d' }
  ],
  missed: [
    { accent: '#d93025', background: '#fce8e6', text: '#b3261e', border: '#f6c7c3' }
  ]
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

// 视图模式
const viewMode = ref<'year' | 'month' | 'week' | 'day'>('day')
const currentDate = ref(new Date())

// 数据
const reservations = ref<Reservation[]>([])
const tools = ref<Tool[]>([])
const accounts = ref<Account[]>([])
const projects = ref<Project[]>([])
const loadingAccounts = ref(false)
const selectedTool = ref<number>()
const selectedReservation = ref<Reservation | null>(null)
const hasToolSelected = computed(() => !!selectedTool.value)
const selectedToolName = computed(() => {
  const tool = tools.value.find((item) => item.id === selectedTool.value)
  return tool?.name || ''
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
const selectedFormToolProjectName = computed(() => {
  const tool = selectedFormTool.value
  if (!tool) return ''
  const matched = projects.value.find((item) => item.id === (tool.project_id ?? tool.project?.id))
  return getProjectDisplayName(matched || tool.project || null)
})

const visibleReservationSummary = computed(() => {
  const summary = {
    total: reservations.value.length,
    ongoing: 0,
    upcoming: 0,
    past: 0,
    cancelled: 0,
    missed: 0
  }
  reservations.value.forEach((reservation) => {
    const cls = getReservationClass(reservation)
    if (cls === 'ongoing') summary.ongoing += 1
    else if (cls === 'upcoming') summary.upcoming += 1
    else if (cls === 'past') summary.past += 1
    else if (cls === 'cancelled') summary.cancelled += 1
    else if (cls === 'missed') summary.missed += 1
  })
  return summary
})

const nowLabel = computed(() => nowTick.value.format('HH:mm'))

const timePickerNowLineVisible = computed(() => {
  if (!reservationDate.value) return false
  return dayjs(reservationDate.value).isSame(nowTick.value, 'day')
})

const timePickerNowLineStyle = computed(() => {
  if (!timePickerNowLineVisible.value || !reservationDate.value) {
    return {}
  }
  const dayStart = dayjs(reservationDate.value).startOf('day')
  const offsetMinutes = Math.min(Math.max(nowTick.value.diff(dayStart, 'minute'), 0), 1440)
  const offsetRows = offsetMinutes / TIME_GRID_STEP_MINUTES
  return {
    top: `${offsetRows * TIME_DAY_SLOT_HEIGHT}px`
  }
})

const filterDialogVisible = ref(false)
const filterToolId = ref<number>()

const reservedReservations = ref<ReservationOccupiedSlot[]>([])
const lastValidTimeRange = ref<[number, number]>([540, 600])
const isAdjustingTimeRange = ref(false)

// 对话框
const detailDialogVisible = ref(false)
const formDialogVisible = ref(false)
const dialogMode = ref<'create' | 'edit'>('create')
const dialogTitle = computed(() => (dialogMode.value === 'create' ? '创建预约' : '编辑预约'))
const submitting = ref(false)
const isCreateMode = computed(() => dialogMode.value === 'create')
const timePickerDialogVisible = ref(false)
const timeGridDraftRange = ref<[number, number]>([540, 600])
const timeGridAnchorStart = ref<number | null>(null)

const earliestSelectableMinute = computed(() => {
  if (!reservationDate.value || !isCreateMode.value) return 0
  const selectedDay = dayjs(reservationDate.value).startOf('day')
  const now = nowTick.value
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
const formData = reactive<Partial<Reservation>>({
  tool_id: undefined,
  project_id: undefined,
  payer_account_id: undefined,
  user_id: authStore.user?.id,
  start: '',
  end: '',
  additional_information: '',
  self_configuration: false
})

const formRules: FormRules = {
  tool_id: [{ required: true, message: '请选择仪器', trigger: 'change' }],
  payer_account_id: [{ required: true, message: '请选择结算账户', trigger: 'change' }],
  start: [{ required: true, message: '请选择开始时间', trigger: 'change' }],
  end: [{ required: true, message: '请选择结束时间', trigger: 'change' }]
}

// 计算当前日期显示
const currentDateDisplay = computed(() => {
  if (viewMode.value === 'year') {
    return dayjs(currentDate.value).format('YYYY年')
  } else if (viewMode.value === 'month') {
    return dayjs(currentDate.value).format('YYYY年 MM月')
  } else if (viewMode.value === 'week') {
    const start = dayjs(currentDate.value).startOf('week')
    const end = dayjs(currentDate.value).endOf('week')
    return `${start.format('YYYY年 MM月DD日')} - ${end.format('MM月DD日')}`
  } else {
    return dayjs(currentDate.value).format('YYYY年 MM月DD日')
  }
})

const reservationDateDisplay = computed(() => {
  if (!reservationDate.value) return ''
  return dayjs(reservationDate.value).format('YYYY年MM月DD日 dddd')
})

const yearWeekdayLabels = ['日', '一', '二', '三', '四', '五', '六']

// 计算周视图的天数
const weekDays = computed(() => {
  const start = dayjs(currentDate.value).startOf('week')
  return Array.from({ length: 7 }, (_, i) => {
    const date = start.add(i, 'day')
    return {
      date: date.format('YYYY-MM-DD'),
      dateNum: date.format('D'),
      name: date.format('ddd')
    }
  })
})

const yearMonths = computed(() => {
  const yearStart = dayjs(currentDate.value).startOf('year')

  return Array.from({ length: 12 }, (_, monthIndex) => {
    const monthStart = yearStart.month(monthIndex).startOf('month')
    const calendarStart = monthStart.startOf('week')
    const calendarEnd = monthStart.endOf('month').endOf('week')
    const days: Array<{
      date: string
      label: string
      isToday: boolean
      isCurrentMonth: boolean
      reservationCount: number
    }> = []

    let cursor = calendarStart
    while (cursor.isBefore(calendarEnd) || cursor.isSame(calendarEnd, 'day')) {
      const date = cursor.format('YYYY-MM-DD')
      days.push({
        date,
        label: cursor.format('D'),
        isToday: cursor.isSame(nowTick.value, 'day'),
        isCurrentMonth: cursor.isSame(monthStart, 'month'),
        reservationCount: getReservationsForDate(date).length
      })
      cursor = cursor.add(1, 'day')
    }

    const monthReservations = reservations.value.filter((reservation) =>
      dayjs(reservation.start).isSame(monthStart, 'month')
    )
    const totalMinutes = monthReservations.reduce((sum, reservation) => {
      const start = dayjs(reservation.start)
      const end = dayjs(reservation.end)
      return sum + Math.max(end.diff(start, 'minute'), 0)
    }, 0)

    return {
      monthKey: monthStart.format('YYYY-MM'),
      monthStart: monthStart.toDate(),
      label: monthStart.format('M月'),
      days,
      totalReservations: monthReservations.length,
      totalLoadLabel: totalMinutes > 0 ? formatHourLoad(totalMinutes) : '空闲'
    }
  })
})

// 加载仪器列表
const loadTools = async () => {
  try {
    const response: any = await getTools({ skip: 0, limit: 1000 })
    tools.value = Array.isArray(response) ? response : response.data || []
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

// 加载项目列表
const loadProjects = async () => {
  try {
    const response: any = await getProjects({ skip: 0, limit: 1000, active: true })
    projects.value = Array.isArray(response) ? response : response.data || []
  } catch (error) {
    console.error('加载项目列表失败:', error)
  }
}

// 加载预约数据
const loadReservations = async () => {
  try {
    if (!selectedTool.value) {
      reservations.value = []
      return
    }
    let startDate, endDate

    if (viewMode.value === 'year') {
      startDate = dayjs(currentDate.value).startOf('year').format('YYYY-MM-DD HH:mm:ss')
      endDate = dayjs(currentDate.value).endOf('year').format('YYYY-MM-DD HH:mm:ss')
    } else if (viewMode.value === 'month') {
      startDate = dayjs(currentDate.value).startOf('month').format('YYYY-MM-DD HH:mm:ss')
      endDate = dayjs(currentDate.value).endOf('month').format('YYYY-MM-DD HH:mm:ss')
    } else if (viewMode.value === 'week') {
      startDate = dayjs(currentDate.value).startOf('week').format('YYYY-MM-DD HH:mm:ss')
      endDate = dayjs(currentDate.value).endOf('week').format('YYYY-MM-DD HH:mm:ss')
    } else {
      startDate = dayjs(currentDate.value).startOf('day').format('YYYY-MM-DD HH:mm:ss')
      endDate = dayjs(currentDate.value).endOf('day').format('YYYY-MM-DD HH:mm:ss')
    }

    const params: any = {
      start_date: startDate,
      end_date: endDate,
      limit: 1000
    }

    params.tool_id = selectedTool.value
    if (!authStore.isStaff()) {
      params.include_all = true
    }

    const response = await getReservations(params)
    reservations.value = Array.isArray(response) ? response : []
  } catch (error) {
    ElMessage.error('加载预约数据失败')
    console.error(error)
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

const isTimeGridSlotDisabled = (startMin: number, _endMin: number) => {
  if (isCreateMode.value && startMin < earliestSelectableMinute.value) {
    return true
  }
  return !isSelectableTimeGridBoundary({
    anchorStart: timeGridAnchorStart.value,
    startMin,
    endMin: _endMin,
    requiresWholeHourSelection: requiresWholeHourSelection.value
  })
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
  if (isTimeGridSlotDisabled(startMin, endMin) || isTimeGridSlotReserved(startMin, endMin)) {
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

const openFilterDialog = () => {
  filterToolId.value = selectedTool.value
  filterDialogVisible.value = true
}

const applyFilter = async () => {
  if (!filterToolId.value) {
    ElMessage.warning('请选择仪器')
    return
  }
  selectedTool.value = filterToolId.value
  filterDialogVisible.value = false
  await loadReservations()
}

const clearFilter = async () => {
  selectedTool.value = undefined
  filterToolId.value = undefined
  filterDialogVisible.value = false
  await loadReservations()
}

const reservationsByDate = computed<Record<string, Reservation[]>>(() => {
  const grouped: Record<string, Reservation[]> = {}
  reservations.value.forEach((reservation) => {
    const date = dayjs(reservation.start).format('YYYY-MM-DD')
    if (!grouped[date]) {
      grouped[date] = []
    }
    grouped[date].push(reservation)
  })
  Object.values(grouped).forEach((items) => {
    items.sort((a, b) => dayjs(a.start).valueOf() - dayjs(b.start).valueOf())
  })
  return grouped
})

// 获取指定日期的预约
const getReservationsForDate = (date: string) => {
  return reservationsByDate.value[date] || []
}

const formatHourLoad = (totalMinutes: number) => {
  if (totalMinutes < 60) return `${totalMinutes}分`
  const hours = totalMinutes / 60
  return Number.isInteger(hours) ? `${hours}小时` : `${hours.toFixed(1)}小时`
}

const getDayLoadLabel = (date: string) => {
  const dayReservations = getReservationsForDate(date)
  if (!dayReservations.length) return ''
  const totalMinutes = dayReservations.reduce((sum, reservation) => {
    const start = dayjs(reservation.start)
    const end = dayjs(reservation.end)
    return sum + Math.max(end.diff(start, 'minute'), 0)
  }, 0)
  return `${dayReservations.length}条 · ${formatHourLoad(totalMinutes)}`
}

const openYearMonth = async (date: Date) => {
  currentDate.value = date
  viewMode.value = 'month'
  await loadReservations()
}

const openYearDay = async (date: string) => {
  currentDate.value = dayjs(date).toDate()
  viewMode.value = 'day'
  await loadReservations()
}

// 获取指定日期的预约（包含跨天）
const getReservationsForDay = (date: string | Date) => {
  const dateStr = typeof date === 'string' ? date : dayjs(date).format('YYYY-MM-DD')
  const dayStart = dayjs(dateStr).startOf('day')
  const dayEnd = dayjs(dateStr).endOf('day')
  return reservations.value.filter(r => {
    const start = dayjs(r.start)
    const end = dayjs(r.end)
    return start.isBefore(dayEnd) && end.isAfter(dayStart)
  }).sort((a, b) => dayjs(a.start).valueOf() - dayjs(b.start).valueOf())
}

// 获取预约样式
const getReservationClass = (reservation: Reservation) => {
  if (reservation.cancelled) return 'cancelled'
  if (reservation.missed) return 'missed'
  if (isOngoing(reservation)) return 'ongoing'
  if (isPast(reservation)) return 'past'
  return 'upcoming'
}

const getReservationTone = (reservation: Reservation, index: number) => {
  const status = getReservationClass(reservation)
  const palette = STATUS_COLOR_PALETTES[status] || STATUS_COLOR_PALETTES.upcoming
  return palette[index % palette.length]
}

const getReservationColorStyle = (reservation: Reservation, index: number) => {
  const tone = getReservationTone(reservation, index)
  return {
    '--reservation-bg': tone.background,
    '--reservation-accent': tone.accent,
    '--reservation-text': tone.text,
    '--reservation-border': tone.border,
    color: tone.text
  }
}

const getReservationMonthStyle = (reservation: Reservation, index: number) => {
  const tone = getReservationTone(reservation, index)
  return {
    '--reservation-pill-bg': `linear-gradient(135deg, ${tone.background}, #ffffff)`,
    '--reservation-pill-accent': tone.accent,
    '--reservation-pill-accent-soft': `${tone.accent}1f`,
    '--reservation-pill-border': tone.border,
    '--reservation-pill-shadow': `${tone.accent}1f`,
    '--reservation-pill-text': tone.text,
    color: tone.text
  }
}

const isOccupiedByOthers = (reservation: Reservation | null) => {
  if (!reservation) return false
  if (authStore.isStaff()) return false
  return reservation.user_id !== authStore.user?.id
}

const getTimelineReservationColorStyle = (reservation: Reservation, index: number) => {
  if (isOccupiedByOthers(reservation)) {
    return {
      '--reservation-bg': '#d93025',
      '--reservation-accent': '#b3261e',
      '--reservation-text': '#ffffff',
      '--reservation-border': '#f6a7a2',
      color: '#ffffff'
    }
  }
  return getReservationColorStyle(reservation, index)
}

const getReservationDetailStyle = (reservation: Reservation) => {
  const tone = getReservationTone(reservation, 0)
  return {
    '--detail-accent': tone.accent,
    '--detail-soft': tone.background,
    '--detail-soft-border': tone.border,
    '--detail-text': tone.text
  }
}

const getReservationStatusLabel = (reservation: Reservation | null) => {
  if (!reservation) return '-'
  const status = getReservationClass(reservation)
  if (status === 'cancelled') return '已取消'
  if (status === 'missed') return '已错过'
  if (status === 'ongoing') return '进行中'
  if (status === 'past') return '已结束'
  return '未开始'
}

const getReservationStatusTagType = (reservation: Reservation | null) => {
  if (!reservation) return 'info'
  const status = getReservationClass(reservation)
  if (status === 'cancelled') return 'warning'
  if (status === 'missed') return 'danger'
  if (status === 'ongoing') return 'success'
  if (status === 'past') return 'info'
  return 'primary'
}

const getReservationDisplayTitle = (reservation: Reservation | null) => {
  if (!reservation) return '-'
  if (reservation.tool?.name) return reservation.tool.name
  const actor = getDisplayUserName(reservation)
  if (actor === '其他用户') return '预约事项'
  return `${actor} 的预约`
}

const getReservationDisplayDate = (reservation: Reservation | null) => {
  if (!reservation) return '-'
  return `${dayjs(reservation.start).format('YYYY年M月D日')} ${formatTime(reservation.start)} - ${formatTime(reservation.end)}`
}

const showReservationMoreActions = (reservation: Reservation) => {
  ElMessage.info(`预约 #${reservation.id}，状态：${getReservationStatusLabel(reservation)}`)
}

// 获取预约块样式（用于周/日时间线视图）
const getReservationBlockStyle = (reservation: Reservation, date: string | Date) => {
  const dateStr = typeof date === 'string' ? date : dayjs(date).format('YYYY-MM-DD')
  const dayStart = dayjs(dateStr).startOf('day')
  const dayEnd = dayjs(dateStr).endOf('day')
  const start = dayjs(reservation.start)
  const end = dayjs(reservation.end)

  const displayStart = start.isBefore(dayStart) ? dayStart : start
  const displayEnd = end.isAfter(dayEnd) ? dayEnd : end
  const offsetMinutes = displayStart.diff(dayStart, 'minute')
  const minimumMinutes = isOccupiedByOthers(reservation) ? 20 : 15
  const duration = Math.max(displayEnd.diff(displayStart, 'minute'), minimumMinutes)

  return {
    top: `${offsetMinutes * MINUTE_HEIGHT}px`,
    height: `${duration * MINUTE_HEIGHT}px`
  }
}

const isNowLineVisible = (date: string | Date) => {
  const dateStr = typeof date === 'string' ? date : dayjs(date).format('YYYY-MM-DD')
  return dayjs(dateStr).isSame(nowTick.value, 'day')
}

const getNowLineStyle = (date: string | Date) => {
  const dateStr = typeof date === 'string' ? date : dayjs(date).format('YYYY-MM-DD')
  const dayStart = dayjs(dateStr).startOf('day')
  const offsetMinutes = Math.min(Math.max(nowTick.value.diff(dayStart, 'minute'), 0), 1440)
  return {
    top: `${offsetMinutes * MINUTE_HEIGHT}px`
  }
}

const getCalendarDayNowLineStyle = (date: string | Date) => {
  return getNowLineStyle(date)
}

const canViewReservationDetails = (reservation: Reservation | null) => {
  if (!reservation) return false
  if (authStore.isStaff()) return true
  return reservation.user_id === authStore.user?.id
}

const getDisplayUserName = (reservation: Reservation | null) => {
  if (!reservation) return '-'
  if (canViewReservationDetails(reservation)) {
    return reservation.user?.username || '-'
  }
  return '其他用户'
}

const getDisplayProjectName = (reservation: Reservation | null) => {
  if (!reservation) return '-'
  if (canViewReservationDetails(reservation)) {
    const matched = projects.value.find((item) => item.id === reservation.project_id)
    const byProjectList = getProjectDisplayName(matched)
    if (byProjectList) return byProjectList
    return getProjectDisplayName(reservation.project || null) || '-'
  }
  return '保密'
}

// 获取提示内容
const getTooltipContent = (reservation: Reservation) => {
  const showDetails = canViewReservationDetails(reservation)
  const noteText = showDetails && reservation.additional_information
    ? `备注: ${reservation.additional_information}`
    : ''
  return `
    仪器: ${reservation.tool?.name || '-'}
    用户: ${getDisplayUserName(reservation)}
    时间: ${formatDateTime(reservation.start)} - ${formatDateTime(reservation.end)}
    ${noteText}
  `
}

// 格式化时间
const formatTime = (datetime: string) => {
  return dayjs(datetime).format('HH:mm')
}

// 判断是否是今天
const isToday = (date: string) => {
  return dayjs(date).isSame(nowTick.value, 'day')
}

// 判断预约是否进行中
const isOngoing = (reservation: Reservation | null) => {
  if (!reservation) return false
  const now = nowTick.value
  const start = dayjs(reservation.start)
  const end = dayjs(reservation.end)
  return now.isAfter(start) && now.isBefore(end)
}

// 判断预约是否已过期
const isPast = (reservation: Reservation | null) => {
  if (!reservation) return false
  const now = nowTick.value
  const end = dayjs(reservation.end)
  return now.isAfter(end)
}

// 切换到上一个时间段
const prevPeriod = () => {
  if (viewMode.value === 'year') {
    currentDate.value = dayjs(currentDate.value).subtract(1, 'year').toDate()
  } else if (viewMode.value === 'month') {
    currentDate.value = dayjs(currentDate.value).subtract(1, 'month').toDate()
  } else if (viewMode.value === 'week') {
    currentDate.value = dayjs(currentDate.value).subtract(1, 'week').toDate()
  } else {
    currentDate.value = dayjs(currentDate.value).subtract(1, 'day').toDate()
  }
  loadReservations()
}

// 切换到下一个时间段
const nextPeriod = () => {
  if (viewMode.value === 'year') {
    currentDate.value = dayjs(currentDate.value).add(1, 'year').toDate()
  } else if (viewMode.value === 'month') {
    currentDate.value = dayjs(currentDate.value).add(1, 'month').toDate()
  } else if (viewMode.value === 'week') {
    currentDate.value = dayjs(currentDate.value).add(1, 'week').toDate()
  } else {
    currentDate.value = dayjs(currentDate.value).add(1, 'day').toDate()
  }
  loadReservations()
}

// 回到今天
const today = () => {
  currentDate.value = new Date()
  loadReservations()
}

// 跳转到列表视图
const goToList = () => {
  router.push('/reservations')
}

// 查看预约详情
const handleViewDetail = (reservation: Reservation) => {
  selectedReservation.value = reservation
  detailDialogVisible.value = true
}

// 创建预约
const handleCreate = async () => {
  router.push({
    name: 'ReservationCreate',
    query: {
      from: 'calendar',
      ...(selectedTool.value ? { toolId: String(selectedTool.value) } : {}),
      date: dayjs(currentDate.value).format('YYYY-MM-DD')
    }
  })
}

// 编辑预约
const handleEdit = async (reservation: Reservation) => {
  dialogMode.value = 'edit'
  Object.assign(formData, {
    id: reservation.id,
    tool_id: reservation.tool_id,
    project_id: reservation.project_id,
    payer_account_id: reservation.payer_account_id,
    user_id: reservation.user_id,
    start: reservation.start,
    end: reservation.end,
    additional_information: reservation.additional_information,
    self_configuration: reservation.self_configuration
  })
  await loadAccounts(reservation.user_id)
  
  const start = dayjs(reservation.start)
  const end = dayjs(reservation.end)
  reservationDate.value = start.format('YYYY-MM-DD')
  const startMinutes = start.hour() * 60 + start.minute()
  let endMinutes = end.hour() * 60 + end.minute()
  
  // 处理跨天情况（如果是第二天0点，设为1440）
  if (end.date() !== start.date()) {
      endMinutes += 1440
  }
  
  timeRange.value = [startMinutes, endMinutes]
  lastValidTimeRange.value = [startMinutes, endMinutes]
  
  detailDialogVisible.value = false
  formDialogVisible.value = true
  await loadReservedReservations()
  updateTimeFromSlider()
}

// 取消预约
const handleCancel = async (reservation: Reservation) => {
  try {
    await ElMessageBox.confirm('确定要取消该预约吗？', '警告', {
      type: 'warning',
      confirmButtonText: '确定取消'
    })
    await cancelReservation(reservation.id)
    ElMessage.success('取消成功')
    detailDialogVisible.value = false
    await loadReservations()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('取消失败')
      console.error(error)
    }
  }
}

// 提交表单
const handleSubmit = async () => {
  if (!formRef.value) return

  await loadReservedReservations()

  await formRef.value.validate(async (valid: any) => {
    if (!valid) return

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
      formDialogVisible.value = false
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
  nowTickTimer = window.setInterval(() => {
    nowTick.value = dayjs()
  }, 60 * 1000)
  await Promise.all([loadTools(), loadProjects(), loadAccounts()])
  await loadReservations()
})

onUnmounted(() => {
  if (nowTickTimer) {
    window.clearInterval(nowTickTimer)
    nowTickTimer = null
  }
})
</script>

<style scoped>
.page-container {
  padding: 16px 18px 18px;
}

.header-card {
  margin-bottom: 10px;
  border: 1px solid #e3e8f0;
  border-radius: 18px;
  background: linear-gradient(180deg, #ffffff 0%, #fafcff 100%);
  box-shadow: 0 10px 26px rgba(15, 23, 42, 0.045);
}

.calendar-card {
  margin-top: 0;
  border: 1px solid #e3e8f0;
  border-radius: 18px;
  background: #ffffff;
  overflow: hidden;
  box-shadow: 0 16px 40px rgba(15, 23, 42, 0.06);
}

.header-card :deep(.el-card__body),
.calendar-card :deep(.el-card__body),
.calendar-card :deep(.el-card__header) {
  padding-inline: 16px;
}

.header-card :deep(.el-card__body) {
  padding-block: 10px;
}

.calendar-card :deep(.el-card__header) {
  padding-top: 12px;
  padding-bottom: 10px;
  border-bottom: 1px solid #eef2f7;
}

.toolbar-shell {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px 16px;
  flex-wrap: wrap;
}

.toolbar-group {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.toolbar-group-right {
  margin-left: auto;
  justify-content: flex-end;
}

.calendar-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.calendar-empty {
  padding: 22px 0;
}

.current-date {
  font-size: 20px;
  font-weight: 600;
  letter-spacing: -0.02em;
  color: #202124;
}

.calendar-overview {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: center;
  gap: 8px 12px;
  margin-bottom: 10px;
  padding: 8px 10px;
  border: 1px solid #edf2fb;
  border-radius: 14px;
  background: linear-gradient(180deg, #f8fbff 0%, #ffffff 100%);
}

.calendar-legend {
  display: flex;
  align-items: center;
  gap: 10px 12px;
  flex-wrap: wrap;
}

.legend-item {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 11px;
  color: #5f6368;
}

.legend-dot {
  width: 10px;
  height: 10px;
  border-radius: 99px;
  border: 1px solid transparent;
}

.legend-dot.upcoming {
  background: #409eff;
  border-color: #2563eb;
}

.legend-dot.ongoing {
  background: #67c23a;
  border-color: #3f8600;
}

.legend-dot.past {
  background: #909399;
  border-color: #6b7280;
}

.legend-dot.cancelled {
  background: #e6a23c;
  border-color: #b45309;
}

.legend-dot.missed {
  background: #f56c6c;
  border-color: #dc2626;
}

.calendar-summary {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

:deep(.reservation-detail-dialog .el-dialog) {
  border-radius: 34px;
  overflow: hidden;
  background: #eef2f6;
  box-shadow: 0 28px 60px rgba(15, 23, 42, 0.22);
}

:deep(.reservation-detail-dialog .el-dialog__header) {
  display: none;
}

:deep(.reservation-detail-dialog .el-dialog__body) {
  padding: 0;
}

:deep(.reservation-detail-dialog .el-dialog__footer) {
  padding: 0 28px 28px;
  background: #eef2f6;
}

.reservation-detail-card {
  padding: 28px 28px 20px;
  background:
    radial-gradient(circle at top right, rgba(255, 255, 255, 0.55), transparent 38%),
    linear-gradient(180deg, #eef2f6 0%, #edf1f4 100%);
  color: #202124;
}

.reservation-detail-hero {
  display: flex;
  align-items: flex-start;
  gap: 18px;
}

.reservation-detail-marker {
  width: 28px;
  height: 28px;
  margin-top: 8px;
  border-radius: 9px;
  background: var(--detail-accent, #1a73e8);
  box-shadow: 0 8px 18px rgba(15, 23, 42, 0.14);
  flex: none;
}

.reservation-detail-heading {
  flex: 1;
  min-width: 0;
}

.reservation-detail-top-right {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 10px;
}

.reservation-detail-title {
  font-size: 22px;
  line-height: 1.2;
  font-weight: 500;
  color: #202124;
}

.reservation-detail-subtitle {
  margin-top: 8px;
  font-size: 14px;
  color: #5f6368;
}

.reservation-detail-status-tag {
  margin-top: 6px;
}

.reservation-detail-actions {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.reservation-detail-icon-btn {
  width: 36px;
  height: 36px;
  border: none;
  background: rgba(255, 255, 255, 0.74);
  color: #3c4043;
  box-shadow: 0 1px 6px rgba(15, 23, 42, 0.1);
}

.reservation-detail-icon-btn:hover {
  background: rgba(255, 255, 255, 0.92);
  color: #202124;
}

.reservation-detail-content {
  margin-top: 28px;
}

.reservation-detail-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px 16px;
}

.reservation-detail-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-height: 82px;
  padding: 16px 18px;
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.62);
  border: 1px solid rgba(255, 255, 255, 0.85);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.7);
}

.reservation-detail-field-wide {
  grid-column: 1 / -1;
  min-height: 110px;
}

.reservation-detail-label {
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.04em;
  color: #6b7280;
}

.reservation-detail-value {
  font-size: 15px;
  line-height: 1.5;
  color: #202124;
  word-break: break-word;
}

.reservation-detail-note {
  white-space: pre-wrap;
}

.reservation-detail-footer {
  width: 100%;
  justify-content: flex-end;
}

:deep(.google-day-time-dialog .el-dialog) {
  border-radius: 22px;
  overflow: hidden;
}

:deep(.google-day-time-dialog .el-dialog__header) {
  padding: 16px 20px 12px;
  border-bottom: 1px solid #e8edf5;
}

:deep(.google-day-time-dialog .el-dialog__body) {
  padding: 14px 20px 16px;
  background: linear-gradient(180deg, #f9fbff 0%, #ffffff 100%);
}

:deep(.google-day-time-dialog .el-dialog__footer) {
  padding: 12px 20px 18px;
  border-top: 1px solid #e8edf5;
  background: #ffffff;
}

.year-view {
  padding-top: 2px;
}

.year-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
}

.year-month-card {
  border: 1px solid #e8edf5;
  border-radius: 18px;
  padding: 13px 13px 12px;
  background: linear-gradient(180deg, #ffffff 0%, #fbfdff 100%);
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.05);
}

.year-month-header {
  width: 100%;
  padding: 0;
  margin-bottom: 10px;
  border: none;
  background: transparent;
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  cursor: pointer;
  text-align: left;
}

.year-month-title {
  font-size: 16px;
  font-weight: 600;
  color: #202124;
}

.year-month-meta {
  font-size: 12px;
  color: #5f6368;
}

.year-weekdays {
  display: grid;
  grid-template-columns: repeat(7, minmax(0, 1fr));
  margin-bottom: 6px;
}

.year-weekday {
  text-align: center;
  font-size: 11px;
  color: #80868b;
  padding-block: 4px;
}

.year-days {
  display: grid;
  grid-template-columns: repeat(7, minmax(0, 1fr));
  gap: 2px;
}

.year-days :deep(.el-popover__reference-wrapper) {
  display: block;
}

.year-day-cell {
  position: relative;
  width: 100%;
  min-height: 30px;
  border: none;
  border-radius: 10px;
  background: transparent;
  color: #202124;
  cursor: pointer;
  transition: background-color 0.18s ease, transform 0.18s ease;
}

.year-day-cell:hover {
  background: #f1f3f4;
}

.year-day-cell.outside {
  color: #bdc1c6;
}

.year-day-cell.today {
  background: #e8f0fe;
}

.year-day-cell.busy .year-day-number {
  font-weight: 600;
}

.year-day-cell.busy {
  background: #edf5ff;
  box-shadow: inset 0 0 0 1px rgba(26, 115, 232, 0.12);
}

.year-day-cell.busy:hover {
  background: #e8f0fe;
  transform: translateY(-1px);
}

.year-day-number {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  padding-top: 4px;
  font-size: 11px;
  line-height: 1;
}

.year-day-cell.today .year-day-number {
  color: #174ea6;
}

.year-day-dot {
  position: absolute;
  left: 50%;
  bottom: 5px;
  width: 6px;
  height: 6px;
  border-radius: 999px;
  background: linear-gradient(135deg, #1a73e8, #1557b0);
  transform: translateX(-50%);
  box-shadow: 0 0 0 3px rgba(26, 115, 232, 0.08);
}

.year-month-footer {
  margin-top: 10px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 12px;
  color: #5f6368;
}

.filter-tool-btn {
  font-weight: 600;
  min-height: 36px;
  padding-inline: 16px;
  border-radius: 999px;
  box-shadow: 0 6px 16px rgba(26, 115, 232, 0.18);
}

.filter-tool-btn.el-button--primary {
  background: linear-gradient(135deg, #1a73e8, #1557b0);
  border-color: #1557b0;
}

.filter-tool-btn.el-button--primary:hover {
  filter: brightness(1.03);
}

.filter-state-tag {
  --el-tag-border-color: transparent;
  border-radius: 10px;
  min-height: 32px;
  padding-inline: 12px;
  font-size: 13px;
  font-weight: 700;
  letter-spacing: 0.01em;
  color: #ffffff;
  border: 1px solid transparent;
  box-shadow: 0 6px 14px rgba(15, 23, 42, 0.14);
  white-space: nowrap;
}

.filter-state-tag-project {
  background: linear-gradient(135deg, #4b5563, #374151);
  border-color: #1f2937;
}

.filter-state-tag-tool {
  background: linear-gradient(135deg, #34a853, #188038);
  border-color: #137333;
}

:deep(.header-card .el-button) {
  border-radius: 999px;
  font-weight: 500;
  min-height: 34px;
}

:deep(.calendar-card .el-button) {
  border-radius: 999px;
  min-height: 34px;
}

.view-mode-switch :deep(.el-radio-button__inner) {
  border-radius: 999px;
  min-width: 44px;
  min-height: 34px;
  border-color: #dbe4f0;
  color: #5f6368;
  background: #ffffff;
  box-shadow: none;
}

.view-mode-switch :deep(.el-radio-button:first-child .el-radio-button__inner),
.view-mode-switch :deep(.el-radio-button:last-child .el-radio-button__inner) {
  border-radius: 999px;
}

.view-mode-switch :deep(.el-radio-button__original-radio:checked + .el-radio-button__inner) {
  background: #e8f0fe;
  border-color: #aecbfa;
  color: #174ea6;
  box-shadow: none;
}

:deep(.el-calendar__header) {
  display: none;
}

:deep(.el-calendar-table) {
  border-top: 1px solid #edf2fb;
  border-left: 1px solid #edf2fb;
}

:deep(.el-calendar-table th) {
  padding: 10px 4px;
  border-right: 1px solid #edf2fb;
  border-bottom: 1px solid #edf2fb;
  color: #5f6368;
  font-weight: 500;
  background: #ffffff;
}

:deep(.el-calendar-table td) {
  border-right: 1px solid #edf2fb;
  border-bottom: 1px solid #edf2fb;
  vertical-align: top;
  background: #ffffff;
}

:deep(.el-calendar-table .el-calendar-day) {
  height: 138px;
  padding: 0;
}

:deep(.el-calendar-table td.is-selected) {
  background: #f6faff;
}

:deep(.el-calendar-table td:hover) {
  background: #fbfdff;
}

.calendar-day {
  position: relative;
  overflow: hidden;
  height: 100%;
  padding: 8px 9px 9px;
  display: flex;
  flex-direction: column;
  gap: 5px;
  background: #ffffff;
  transition: background-color 0.18s ease, box-shadow 0.18s ease, transform 0.18s ease;
}

.calendar-day.is-today {
  background:
    radial-gradient(circle at 100% 0%, rgba(26, 115, 232, 0.14) 0, rgba(26, 115, 232, 0) 34%),
    linear-gradient(180deg, #f4f9ff 0%, #ffffff 82%);
  box-shadow: inset 0 0 0 1px rgba(26, 115, 232, 0.18), 0 10px 28px rgba(26, 115, 232, 0.09);
}

.calendar-day.is-today::before {
  content: '';
  position: absolute;
  inset: 0 auto 0 0;
  width: 4px;
  background: linear-gradient(180deg, #1a73e8, #34a853);
}

.calendar-day.is-other-month {
  opacity: 0.62;
}

.day-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  position: relative;
  z-index: 1;
}

.day-title-group {
  display: flex;
  align-items: center;
  gap: 7px;
}

.day-number {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 28px;
  height: 28px;
  padding: 0 7px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 500;
  color: #202124;
}

.calendar-day.is-today .day-number {
  background: linear-gradient(135deg, #1a73e8, #1557b0);
  color: #ffffff;
  box-shadow: 0 8px 18px rgba(26, 115, 232, 0.25);
}

.day-today-label {
  padding: 3px 8px;
  border-radius: 999px;
  font-size: 10px;
  line-height: 1;
  font-weight: 700;
  color: #174ea6;
  background: rgba(232, 240, 254, 0.92);
  border: 1px solid rgba(174, 203, 250, 0.9);
}

.day-load {
  appearance: none;
  border: none;
  display: inline-flex;
  align-items: baseline;
  gap: 2px;
  font-size: 10px;
  color: #174ea6;
  background: #eef5ff;
  border: 1px solid #d5e6ff;
  border-radius: 999px;
  padding: 3px 8px;
}

.day-load--interactive {
  cursor: pointer;
  transition: transform 0.18s ease, box-shadow 0.18s ease, background-color 0.18s ease;
}

.day-load--interactive:hover {
  transform: translateY(-1px);
  background: #e8f0fe;
  box-shadow: 0 8px 18px rgba(26, 115, 232, 0.14);
}

.day-load strong {
  font-size: 12px;
}

.day-subline {
  position: relative;
  z-index: 1;
  min-height: 14px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 10px;
  color: #64748b;
  padding-left: 2px;
}

.reservations-container {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-height: 0;
  flex: 1;
  position: relative;
  z-index: 1;
}

.reservation-item {
  position: relative;
  min-height: 30px;
  border-radius: 12px;
  padding: 5px 8px;
  border: 1px solid var(--reservation-pill-border, rgba(174, 203, 250, 0.88));
  font-size: 11px;
  cursor: pointer;
  transition: transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease;
  box-shadow: 0 7px 16px var(--reservation-pill-shadow, rgba(15, 23, 42, 0.06));
  background: var(--reservation-pill-bg, #eef5ff);
  color: var(--reservation-pill-text, #174ea6);
  backdrop-filter: blur(8px);
}

.reservation-item :deep(.el-popover__reference) {
  width: 100%;
}

.reservation-item:hover {
  transform: translateY(-2px);
  border-color: var(--reservation-pill-accent, #1a73e8);
  box-shadow: 0 12px 24px var(--reservation-pill-shadow, rgba(15, 23, 42, 0.1));
}

.reservation-item-content {
  display: flex;
  align-items: center;
  gap: 7px;
  min-width: 0;
}

.reservation-item-accent {
  width: 4px;
  align-self: stretch;
  min-height: 22px;
  border-radius: 999px;
  background: var(--reservation-pill-accent, #1a73e8);
  flex: none;
  box-shadow: 0 0 0 3px var(--reservation-pill-accent-soft, rgba(26, 115, 232, 0.12));
}

.reservation-item-main {
  min-width: 0;
  flex: 1;
}

.reservation-item-time {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-weight: 800;
  font-size: 10px;
  line-height: 1.15;
  color: var(--reservation-pill-text, #174ea6);
}

.reservation-item-user {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  margin-top: 2px;
  font-size: 10px;
  font-weight: 700;
  color: #334155;
}

:deep(.reservation-hover-popper) {
  border-radius: 16px !important;
  padding: 0 !important;
  border: none !important;
  box-shadow: 0 16px 34px rgba(15, 23, 42, 0.2) !important;
  overflow: hidden;
  min-width: 300px;
}

:deep(.day-reservations-popper) {
  padding: 0 !important;
  border: none !important;
  border-radius: 18px !important;
  overflow: hidden;
  box-shadow: 0 18px 42px rgba(15, 23, 42, 0.22) !important;
}

.day-reservations-panel {
  background:
    radial-gradient(circle at 100% 0%, rgba(26, 115, 232, 0.12) 0, transparent 34%),
    linear-gradient(180deg, #f8fbff 0%, #ffffff 72%);
}

.day-reservations-panel__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 14px 15px 12px;
  border-bottom: 1px solid #e6eefb;
}

.day-reservations-panel__header div {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.day-reservations-panel__header strong {
  font-size: 15px;
  color: #0f172a;
}

.day-reservations-panel__header span {
  font-size: 12px;
  color: #64748b;
}

.day-reservations-panel__link {
  flex: none;
  border: 1px solid #c7dcff;
  border-radius: 999px;
  padding: 5px 10px;
  color: #174ea6;
  background: #edf5ff;
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
}

.day-reservations-panel__list {
  max-height: 288px;
  overflow-y: auto;
  padding: 10px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.day-reservations-panel__list::-webkit-scrollbar {
  width: 8px;
}

.day-reservations-panel__list::-webkit-scrollbar-thumb {
  border-radius: 999px;
  background: #c8d8ef;
  border: 2px solid #f8fbff;
}

.day-reservation-row {
  width: 100%;
  border: 1px solid var(--reservation-pill-border, #d7e6ff);
  border-radius: 14px;
  padding: 9px 10px;
  display: flex;
  align-items: center;
  gap: 9px;
  background: var(--reservation-pill-bg, #ffffff);
  text-align: left;
  cursor: pointer;
  box-shadow: 0 8px 18px var(--reservation-pill-shadow, rgba(15, 23, 42, 0.06));
  transition: transform 0.18s ease, border-color 0.18s ease, box-shadow 0.18s ease;
}

.day-reservation-row:hover {
  transform: translateY(-1px);
  border-color: var(--reservation-pill-accent, #1a73e8);
  box-shadow: 0 12px 24px var(--reservation-pill-shadow, rgba(15, 23, 42, 0.1));
}

.day-reservation-row__accent {
  width: 5px;
  align-self: stretch;
  border-radius: 999px;
  background: var(--reservation-pill-accent, #1a73e8);
  box-shadow: 0 0 0 3px var(--reservation-pill-accent-soft, rgba(26, 115, 232, 0.12));
}

.day-reservation-row__main {
  min-width: 0;
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.day-reservation-row__time {
  color: var(--reservation-pill-text, #174ea6);
  font-size: 12px;
  font-weight: 800;
}

.day-reservation-row__user {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: #334155;
  font-size: 12px;
  font-weight: 700;
}

.day-reservation-row__status {
  flex: none;
  border-radius: 999px;
  padding: 4px 8px;
  background: rgba(255, 255, 255, 0.78);
  color: var(--reservation-pill-text, #174ea6);
  font-size: 11px;
  font-weight: 800;
}

.reservation-hover-card {
  padding: 14px 16px;
  background: linear-gradient(180deg, #f3f8ff 0%, #ffffff 100%);
  border-left: 6px solid var(--detail-accent, #1a73e8);
}

.reservation-hover-title {
  font-size: 15px;
  font-weight: 600;
  color: #1f2937;
  line-height: 1.3;
}

.reservation-hover-time {
  margin-top: 6px;
  font-size: 12px;
  color: #4b5563;
}

.reservation-hover-row {
  margin-top: 7px;
  font-size: 12px;
  color: #334155;
}

.reservation-more {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
  margin-top: 1px;
  padding: 5px 8px;
  border-radius: 11px;
  font-size: 10px;
  color: #174ea6;
  background: linear-gradient(135deg, #edf5ff, #f7fbff);
  border: 1px dashed #b7d4ff;
  font-weight: 700;
  cursor: pointer;
  transition: transform 0.18s ease, background-color 0.18s ease;
}

.reservation-more:hover {
  transform: translateY(-1px);
  background: #e8f0fe;
}

.reservation-more strong {
  font-size: 10px;
  color: #1557b0;
}

.reservation-block {
  position: absolute;
  left: 6px;
  right: 6px;
  border-radius: 10px;
  padding: 6px 8px 6px 12px;
  font-size: 11px;
  cursor: pointer;
  overflow: hidden;
  z-index: 1;
  border: 1px solid var(--reservation-border, #d2e3fc);
  border-left: 4px solid var(--reservation-accent, #1a73e8);
  background: var(--reservation-bg, #e8f0fe);
  color: var(--reservation-text, #174ea6);
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.08);
  backdrop-filter: blur(2px);
}

.reservation-block.occupied-by-others {
  box-shadow: 0 6px 14px rgba(217, 48, 37, 0.28);
  border-left-width: 5px;
  min-height: 14px;
}

.reservation-block-content {
  display: flex;
  flex-direction: column;
  gap: 2px;
  line-height: 1.25;
}

.reservation-block-time {
  font-weight: 600;
}

.reservation-block-user {
  opacity: 0.92;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
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

/* 时间线视图样式 */
.timeline-view {
  border: 1px solid #dfe5f1;
  border-radius: 18px;
  overflow: hidden;
  background: #ffffff;
  box-shadow: 0 12px 30px rgba(15, 23, 42, 0.05);
}

.timeline-header {
  display: flex;
  border-bottom: 1px solid #e7ecf5;
  background: linear-gradient(180deg, #f7faff 0%, #ffffff 100%);
}

.time-column {
  width: 70px;
  padding: 14px 10px;
  font-weight: 600;
  border-right: 1px solid #e5eaf3;
  color: #64748b;
  background: #ffffff;
}

.time-column-body {
  padding: 0;
  font-weight: normal;
  background: #ffffff;
}

.days-row {
  flex: 1;
  display: flex;
}

.timeline-header .day-column {
  flex: 1;
  text-align: center;
  padding: 10px 8px 12px;
  border-right: 1px solid #e5eaf3;
}

.timeline-header .day-column:last-child {
  border-right: none;
}

.timeline-header .day-column.today {
  background: #f8fbff;
  color: #174ea6;
}

.day-name {
  font-size: 12px;
  margin-bottom: 4px;
  color: #5f6368;
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

.day-date {
  display: flex;
  justify-content: center;
}

.day-date-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  border-radius: 999px;
  font-size: 16px;
  font-weight: 500;
  color: #202124;
  background: transparent;
}

.timeline-header .day-column.today .day-date-badge {
  background: #1a73e8;
  color: #ffffff;
}

.timeline-legend {
  display: flex;
  align-items: center;
  gap: 10px 12px;
  flex-wrap: wrap;
  padding: 8px 10px;
  border-bottom: 1px solid #eef2f7;
  background: #fbfcff;
}

.timeline-body {
  display: flex;
  max-height: 560px;
  overflow-y: auto;
  background: #ffffff;
}

.time-label-row {
  height: 72px;
  padding: 6px 8px 0;
  font-size: 11px;
  color: #8b96a7;
  border-bottom: 1px solid #edf1f7;
}

.timeline-body .day-column {
  flex: 1;
  border-right: 1px solid #e5eaf3;
  background: #ffffff;
}

.timeline-body .day-column:last-child {
  border-right: none;
}

.day-grid {
  position: relative;
  height: 1728px;
  background:
    repeating-linear-gradient(
      to bottom,
      rgba(26, 115, 232, 0.014) 0,
      rgba(26, 115, 232, 0.014) 18px,
      transparent 18px,
      transparent 36px
    ),
    repeating-linear-gradient(
      to bottom,
      transparent 0,
      transparent 71px,
      #edf1f7 71px,
      #edf1f7 72px
    );
}

.hour-line {
  height: 72px;
  border-bottom: 1px solid transparent;
}

.now-line {
  position: absolute;
  left: 0;
  right: 0;
  height: 2px;
  background: #ea4335;
  z-index: 4;
}

.now-line::before {
  content: '';
  position: absolute;
  left: -6px;
  top: 50%;
  width: 10px;
  height: 10px;
  border-radius: 999px;
  background: #ea4335;
  transform: translateY(-50%);
  box-shadow: 0 0 0 3px rgba(234, 67, 53, 0.14);
}

.now-line-label {
  position: absolute;
  left: 12px;
  top: -10px;
  padding: 2px 8px;
  border-radius: 999px;
  background: #ea4335;
  color: #fff;
  font-size: 10px;
  line-height: 1.2;
  box-shadow: 0 4px 12px rgba(234, 67, 53, 0.24);
}

.reservation-block:hover {
  z-index: 5;
  transform: translateY(-1px);
  box-shadow: 0 8px 18px rgba(15, 23, 42, 0.12);
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

.time-day-board {
  border: 1px solid #dfe5f1;
  border-radius: 12px;
  overflow: hidden;
  background: #ffffff;
}

.time-day-board-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 7px 10px;
  border-bottom: 1px solid #e7ecf5;
  background: linear-gradient(180deg, #f7faff 0%, #ffffff 100%);
}

.time-day-board-date {
  font-size: 13px;
  color: #374151;
  font-weight: 600;
}

.time-day-scroll {
  max-height: min(58vh, 520px);
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
  border-right: 1px solid #e5eaf3;
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
  border-bottom: 1px solid #edf1f7;
  background: #ffffff;
  cursor: pointer;
  transition: background-color 0.15s ease;
}

.time-day-slot:hover {
  background: #f4f8ff;
}

.time-day-slot.selected {
  background: #2563eb;
}

.time-day-slot.anchor {
  box-shadow: inset 0 0 0 2px #0f172a;
}

.time-day-slot.reserved {
  background: #ef4444;
  cursor: not-allowed;
}

.time-day-slot.disabled {
  background: #9ca3af;
  cursor: not-allowed;
}

.time-day-slot.reserved.disabled {
  background: #ef4444;
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

.field-helper {
  margin-top: 6px;
  font-size: 12px;
  line-height: 1.5;
  color: #64748b;
}

.calendar-day-view {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.day-view-legend {
  border: 1px solid #dfe5f1;
  border-radius: 12px;
}

.calendar-day-board {
  border-radius: 12px;
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.045);
}

.calendar-day-board-title-group {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.calendar-day-board-title {
  font-size: 15px;
  font-weight: 700;
  color: #0f172a;
}

.calendar-day-board-tag {
  color: #2563eb;
  border-color: #bfdbfe;
  background: #eff6ff;
}

.calendar-day-scroll {
  max-height: 520px;
}

.calendar-day-grid {
  position: relative;
}

.calendar-day-slot-surface {
  height: 18px;
  width: 100%;
  border-bottom: 1px solid #edf1f7;
  background:
    linear-gradient(180deg, rgba(26, 115, 232, 0.014) 0, rgba(26, 115, 232, 0.014) 100%);
}

.calendar-day-reservation {
  left: 78px;
  right: 10px;
  z-index: 3;
}

@media (max-width: 1400px) {
  .year-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 900px) {
  .page-container {
    padding: 12px;
  }

  .toolbar-group-right {
    margin-left: 0;
    justify-content: flex-start;
  }

  .calendar-overview {
    grid-template-columns: minmax(0, 1fr);
  }

  .calendar-header {
    align-items: flex-start;
  }

  .reservation-detail-grid {
    grid-template-columns: minmax(0, 1fr);
  }

  .year-grid {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
