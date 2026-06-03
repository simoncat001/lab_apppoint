<template>
  <div v-loading="loading" class="dashboard-page">
    <section class="hero-shell">
      <div class="hero-copy">
        <p class="hero-kicker">{{ reportKicker }}</p>
        <h1 class="hero-title">{{ reportTitle }}</h1>
        <p class="hero-description">{{ reportDescription }}</p>
        <div class="hero-meta">
          <span class="hero-meta-item">{{ periodText }}</span>
          <span class="hero-meta-item">{{ scopeText }}</span>
          <span class="hero-meta-item">覆盖 {{ stats.report_users }} 位用户</span>
        </div>
      </div>

      <div class="hero-controls">
        <el-radio-group v-model="presetDays" size="large" @change="handlePresetChange">
          <el-radio-button :value="7">近 7 天</el-radio-button>
          <el-radio-button :value="30">近 30 天</el-radio-button>
          <el-radio-button :value="90">近 90 天</el-radio-button>
          <el-radio-button :value="180">近 180 天</el-radio-button>
        </el-radio-group>

        <el-date-picker
          v-model="customDateRange"
          class="hero-date-picker"
          type="daterange"
          unlink-panels
          range-separator="至"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          value-format="YYYY-MM-DD"
          @change="handleCustomRangeChange"
        />

        <div class="hero-actions">
          <el-button @click="resetFilters">重置</el-button>
          <el-button type="primary" :loading="loading" @click="refreshCurrentRange">
            刷新报表
          </el-button>
        </div>
      </div>
    </section>

    <section class="status-strip">
      <div
        v-for="item in statusBreakdown"
        :key="item.key"
        class="status-pill"
        :class="`status-${item.key}`"
      >
        <span>{{ item.label }}</span>
        <strong>{{ item.count }}</strong>
      </div>
    </section>

    <el-row :gutter="18" class="stat-row">
      <el-col
        v-for="card in statCards"
        :key="card.label"
        :xs="24"
        :sm="12"
        :xl="6"
      >
        <el-card shadow="hover" class="stat-card" :class="`accent-${card.accent}`">
          <div class="stat-card-top">
            <div>
              <div class="stat-label">{{ card.label }}</div>
              <div class="stat-value">{{ card.value }}</div>
            </div>
            <div class="stat-icon">
              <el-icon>
                <component :is="card.icon" />
              </el-icon>
            </div>
          </div>
          <div class="stat-note">{{ card.note }}</div>
        </el-card>
      </el-col>
    </el-row>

    <section class="chart-grid">
      <el-card class="panel-card">
        <template #header>
          <div class="panel-header">
            <span>预约趋势</span>
            <small>按预约开始日期统计</small>
          </div>
        </template>
        <div ref="trendChartRef" class="chart-panel"></div>
      </el-card>

      <el-card class="panel-card">
        <template #header>
          <div class="panel-header">
            <span>状态分布</span>
            <small>进行中、未开始、完成、取消、失约</small>
          </div>
        </template>
        <div ref="statusChartRef" class="chart-panel"></div>
      </el-card>

      <el-card class="panel-card">
        <template #header>
          <div class="panel-header">
            <span>热门仪器</span>
            <small>预约量 Top 8</small>
          </div>
        </template>
        <div ref="toolChartRef" class="chart-panel"></div>
      </el-card>

    </section>

    <section class="detail-grid">
      <el-card class="profile-card">
        <template #header>
          <div class="panel-header">
            <span>{{ authStore.isStaff() ? '我的报表快照' : '个人预约画像' }}</span>
            <small>{{ currentUserReport.full_name }}</small>
          </div>
        </template>

        <div class="profile-title-block">
          <div class="profile-name">{{ currentUserReport.full_name }}</div>
          <div class="profile-subtitle">@{{ currentUserReport.username }}</div>
        </div>

        <div class="profile-tags">
          <el-tag :type="currentUserReport.is_staff ? 'primary' : 'info'">
            {{ currentUserReport.is_staff ? '管理员' : '普通用户' }}
          </el-tag>
          <el-tag :type="currentUserReport.is_verified ? 'success' : 'warning'">
            {{ currentUserReport.is_verified ? '已验证' : '未验证' }}
          </el-tag>
          <el-tag :type="currentUserReport.is_active ? 'success' : 'danger'">
            {{ currentUserReport.is_active ? '激活中' : '已停用' }}
          </el-tag>
        </div>

        <div class="profile-metrics">
          <div class="profile-metric">
            <span>预约总数</span>
            <strong>{{ currentUserReport.total_reservations }}</strong>
          </div>
          <div class="profile-metric">
            <span>进行中</span>
            <strong>{{ currentUserReport.ongoing_reservations }}</strong>
          </div>
          <div class="profile-metric">
            <span>预约时长</span>
            <strong>{{ currentUserReport.total_hours.toFixed(1) }} h</strong>
          </div>
          <div class="profile-metric">
            <span>涉及仪器</span>
            <strong>{{ currentUserReport.distinct_tools }}</strong>
          </div>
        </div>

        <div class="completion-block">
          <div class="completion-head">
            <span>完成率</span>
            <strong>{{ completionRate }}%</strong>
          </div>
          <el-progress
            :percentage="completionRate"
            :show-text="false"
            :stroke-width="10"
            color="#0f766e"
          />
        </div>

        <div class="profile-summary-list">
          <div class="profile-summary-item">
            <span>常用仪器</span>
            <strong>{{ currentUserReport.favorite_tool_name || '暂无' }}</strong>
          </div>
          <div class="profile-summary-item">
            <span>下一次预约</span>
            <strong>{{ formatDateTime(currentUserReport.next_reservation_at) }}</strong>
          </div>
          <div class="profile-summary-item">
            <span>最近预约</span>
            <strong>{{ formatDateTime(currentUserReport.latest_reservation_at) }}</strong>
          </div>
        </div>
      </el-card>

      <el-card class="table-panel">
        <template #header>
          <div class="panel-header">
            <span>最近预约</span>
            <small>当前筛选范围内最近 8 条</small>
          </div>
        </template>
        <el-table :data="recentReservations" size="small" stripe>
          <el-table-column v-if="showUserColumn" prop="user_name" label="用户" min-width="120" />
          <el-table-column prop="tool_name" label="仪器" min-width="120" />
          <el-table-column prop="project_name" label="项目" min-width="120" />
          <el-table-column label="开始时间" min-width="160">
            <template #default="{ row }">
              {{ formatDateTime(row.start) }}
            </template>
          </el-table-column>
          <el-table-column label="结束时间" min-width="160">
            <template #default="{ row }">
              {{ formatDateTime(row.end) }}
            </template>
          </el-table-column>
          <el-table-column label="状态" width="100">
            <template #default="{ row }">
              <el-tag :type="getReservationStatusType(row.status)">
                {{ getReservationStatusLabel(row.status) }}
              </el-tag>
            </template>
          </el-table-column>
        </el-table>
      </el-card>

      <el-card class="table-panel">
        <template #header>
          <div class="panel-header">
            <span>待处理任务</span>
            <small>开放工单与问题追踪</small>
          </div>
        </template>
        <el-table :data="pendingTasks" size="small" stripe>
          <el-table-column v-if="showUserColumn" prop="creator_name" label="提交人" min-width="110" />
          <el-table-column prop="tool_name" label="仪器" min-width="120" />
          <el-table-column prop="problem_description" label="问题描述" min-width="180" show-overflow-tooltip />
          <el-table-column label="紧急程度" width="100">
            <template #default="{ row }">
              <el-tag :type="getUrgencyType(row.urgency)">
                {{ getUrgencyLabel(row.urgency) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="创建时间" min-width="160">
            <template #default="{ row }">
              {{ formatDateTime(row.creation_time) }}
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </section>

    <el-card v-if="authStore.isStaff()" class="user-report-panel">
      <template #header>
        <div class="user-report-header">
          <div class="panel-header">
            <span>用户预约报表</span>
            <small>每个用户都有对应预约汇总</small>
          </div>
          <el-input
            v-model="reportKeyword"
            clearable
            placeholder="搜索用户 / 常用仪器"
            style="max-width: 280px"
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>
        </div>
      </template>

      <el-table :data="filteredUserReports" size="small" stripe border>
        <el-table-column label="用户" min-width="180" fixed="left">
          <template #default="{ row }">
            <div class="user-cell">
              <strong>{{ row.full_name }}</strong>
              <span>@{{ row.username }}</span>
            </div>
          </template>
        </el-table-column>

        <el-table-column label="状态" width="160">
          <template #default="{ row }">
            <div class="user-status-cell">
              <el-tag size="small" :type="row.is_staff ? 'primary' : 'info'">
                {{ row.is_staff ? '管理员' : '用户' }}
              </el-tag>
              <el-tag size="small" :type="row.is_verified ? 'success' : 'warning'">
                {{ row.is_verified ? '已验证' : '未验证' }}
              </el-tag>
            </div>
          </template>
        </el-table-column>

        <el-table-column prop="total_reservations" label="总预约" width="90" sortable />
        <el-table-column prop="ongoing_reservations" label="进行中" width="90" sortable />
        <el-table-column prop="upcoming_reservations" label="未开始" width="90" sortable />
        <el-table-column prop="completed_reservations" label="已完成" width="90" sortable />
        <el-table-column prop="cancelled_reservations" label="已取消" width="90" sortable />
        <el-table-column prop="missed_reservations" label="失约" width="80" sortable />
        <el-table-column label="时长(h)" width="100" sortable>
          <template #default="{ row }">
            {{ row.total_hours.toFixed(1) }}
          </template>
        </el-table-column>
        <el-table-column prop="distinct_tools" label="仪器数" width="90" sortable />
        <el-table-column prop="distinct_projects" label="项目数" width="90" sortable />
        <el-table-column prop="favorite_tool_name" label="常用仪器" min-width="150" show-overflow-tooltip />
        <el-table-column label="下一次预约" min-width="160">
          <template #default="{ row }">
            {{ formatDateTime(row.next_reservation_at) }}
          </template>
        </el-table-column>
        <el-table-column label="最近预约" min-width="160">
          <template #default="{ row }">
            {{ formatDateTime(row.latest_reservation_at) }}
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as echarts from 'echarts'
import dayjs from 'dayjs'
import {
  Calendar,
  Clock,
  DataAnalysis,
  Search,
  Tickets,
  User,
} from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { getTaskUrgencyLabel, getTaskUrgencyType } from '@/utils/helpers'
import { formatDateTime } from '@/utils/date'
import { getUserDisplayName } from '@/utils/user'
import { useAuthStore } from '@/stores/auth'
import {
  getDashboard,
  type DashboardResponse,
  type DashboardUserReport,
} from '@/api/dashboard'

type ChartKey = 'trend' | 'status' | 'tool'

const authStore = useAuthStore()
const loading = ref(false)
const presetDays = ref(30)
const customDateRange = ref<string[]>([])
const reportKeyword = ref('')
const dashboard = ref<DashboardResponse | null>(null)

const trendChartRef = ref<HTMLDivElement | null>(null)
const statusChartRef = ref<HTMLDivElement | null>(null)
const toolChartRef = ref<HTMLDivElement | null>(null)
const chartInstances: Partial<Record<ChartKey, echarts.ECharts>> = {}

const defaultStats = {
  total_tools: 0,
  active_users: 0,
  report_users: 0,
  total_reservations: 0,
  total_hours: 0,
  active_tasks: 0,
  distinct_tools: 0,
  distinct_projects: 0,
  ongoing_reservations: 0,
  upcoming_reservations: 0,
  completed_reservations: 0,
  cancelled_reservations: 0,
  missed_reservations: 0,
}

const emptyUserReport = computed<DashboardUserReport>(() => ({
  user_id: authStore.user?.id || 0,
  username: authStore.user?.username || '-',
  full_name: getUserDisplayName(authStore.user),
  is_active: authStore.user?.is_active ?? true,
  is_staff: authStore.isStaff(),
  is_verified: authStore.isVerified(),
  total_reservations: 0,
  ongoing_reservations: 0,
  completed_reservations: 0,
  upcoming_reservations: 0,
  cancelled_reservations: 0,
  missed_reservations: 0,
  total_hours: 0,
  distinct_tools: 0,
  distinct_projects: 0,
  favorite_tool_name: null,
  latest_reservation_at: null,
  next_reservation_at: null,
}))

const stats = computed(() => dashboard.value?.stats || defaultStats)
const statusBreakdown = computed(() => dashboard.value?.status_breakdown || [])
const recentReservations = computed(() => dashboard.value?.recent_reservations || [])
const pendingTasks = computed(() => dashboard.value?.pending_tasks || [])
const currentUserReport = computed(() => dashboard.value?.current_user_report || emptyUserReport.value)
const userReports = computed(() => dashboard.value?.user_reports || [])
const showUserColumn = computed(() => authStore.isStaff())

const filteredUserReports = computed(() => {
  if (!reportKeyword.value.trim()) {
    return userReports.value
  }

  const keyword = reportKeyword.value.trim().toLowerCase()
  return userReports.value.filter((row) => {
    return [row.full_name, row.username, row.favorite_tool_name || ''].some((value) =>
      value.toLowerCase().includes(keyword)
    )
  })
})

const reportKicker = computed(() =>
  authStore.isStaff() ? 'Reservation Intelligence' : 'My Reservation Report'
)
const reportTitle = computed(() => (authStore.isStaff() ? '预约报表中心' : '我的预约报表'))
const reportDescription = computed(() => {
  if (authStore.isStaff()) {
    return '围绕预约量、用户活跃度、仪器使用热点和项目分布，快速查看整个系统的预约运行情况。'
  }
  return '围绕你的预约数量、预约时长、常用仪器和未来安排，集中查看个人预约表现。'
})
const periodText = computed(() => {
  if (!dashboard.value) {
    return '统计周期加载中'
  }
  return `${dashboard.value.period_start} 至 ${dashboard.value.period_end}`
})
const scopeText = computed(() =>
  dashboard.value?.scope === 'global' ? '管理员全员视角' : '个人视角'
)

const statCards = computed(() => {
  if (authStore.isStaff()) {
    return [
      {
        label: '报表用户',
        value: stats.value.report_users,
        note: `系统活跃用户 ${stats.value.active_users}`,
        accent: 'user',
        icon: User,
      },
      {
        label: '预约总数',
        value: stats.value.total_reservations,
        note: `进行中 ${stats.value.ongoing_reservations}`,
        accent: 'reservation',
        icon: Calendar,
      },
      {
        label: '预约时长 (h)',
        value: stats.value.total_hours.toFixed(1),
        note: `涉及项目 ${stats.value.distinct_projects}`,
        accent: 'hours',
        icon: Clock,
      },
      {
        label: '开放任务',
        value: stats.value.active_tasks,
        note: `涉及仪器 ${stats.value.distinct_tools}`,
        accent: 'task',
        icon: Tickets,
      },
    ]
  }

  return [
    {
      label: '进行中预约',
      value: stats.value.ongoing_reservations,
      note: `未开始 ${stats.value.upcoming_reservations}`,
      accent: 'reservation',
      icon: Calendar,
    },
    {
      label: '我的预约',
      value: stats.value.total_reservations,
      note: `已完成 ${stats.value.completed_reservations}`,
      accent: 'user',
      icon: User,
    },
    {
      label: '预约时长 (h)',
      value: stats.value.total_hours.toFixed(1),
      note: `常用仪器 ${currentUserReport.value.favorite_tool_name || '暂无'}`,
      accent: 'hours',
      icon: Clock,
    },
    {
      label: '涉及仪器',
      value: stats.value.distinct_tools,
      note: `开放任务 ${stats.value.active_tasks}`,
      accent: 'task',
      icon: DataAnalysis,
    },
  ]
})

const completionRate = computed(() => {
  const total = currentUserReport.value.total_reservations
  if (!total) {
    return 0
  }
  return Math.round((currentUserReport.value.completed_reservations / total) * 100)
})

const getUrgencyLabel = getTaskUrgencyLabel
const getUrgencyType = getTaskUrgencyType

const reservationStatusMap: Record<
  string,
  { label: string; type: 'success' | 'primary' | 'info' | 'warning' | 'danger' }
> = {
  ongoing: { label: '进行中', type: 'success' },
  upcoming: { label: '未开始', type: 'primary' },
  completed: { label: '已完成', type: 'info' },
  cancelled: { label: '已取消', type: 'warning' },
  missed: { label: '已失约', type: 'danger' },
}

const getReservationStatusLabel = (status: string) => reservationStatusMap[status]?.label || status
const getReservationStatusType = (status: string) => reservationStatusMap[status]?.type || 'info'

const buildParams = () => {
  if (customDateRange.value.length === 2) {
    return {
      start_date: customDateRange.value[0],
      end_date: customDateRange.value[1],
    }
  }
  return {
    days: presetDays.value,
  }
}

const loadDashboard = async (params = buildParams()) => {
  loading.value = true
  try {
    dashboard.value = (await getDashboard(params)) as unknown as DashboardResponse
  } catch (error) {
    console.error(error)
    ElMessage.error('加载预约报表失败')
  } finally {
    loading.value = false
  }
}

const handlePresetChange = async (value: string | number | boolean | undefined) => {
  if (value === undefined) {
    return
  }
  presetDays.value = Number(value)
  customDateRange.value = []
  await loadDashboard({ days: presetDays.value })
}

const handleCustomRangeChange = async (value?: string[]) => {
  if (!value || value.length !== 2) {
    await resetFilters()
    return
  }
  await loadDashboard({
    start_date: value[0],
    end_date: value[1],
  })
}

const resetFilters = async () => {
  presetDays.value = 30
  customDateRange.value = []
  await loadDashboard({ days: 30 })
}

const refreshCurrentRange = async () => {
  await loadDashboard()
}

const ensureChart = (key: ChartKey, el: HTMLDivElement | null) => {
  if (!el) {
    return null
  }

  if (!chartInstances[key] || chartInstances[key]?.isDisposed()) {
    chartInstances[key] = echarts.init(el)
  }

  return chartInstances[key] || null
}

const renderTrendChart = () => {
  const chart = ensureChart('trend', trendChartRef.value)
  if (!chart || !dashboard.value) {
    return
  }

  const labels = dashboard.value.trend.map((item) =>
    dayjs(item.date).format(presetDays.value > 60 ? 'MM/DD' : 'M/D')
  )

  chart.setOption({
    color: ['#0f766e', '#2563eb', '#f59e0b', '#ef4444'],
    tooltip: { trigger: 'axis' },
    legend: {
      top: 0,
      data: ['总预约', '进行中', '未开始', '已取消'],
    },
    grid: {
      left: 24,
      right: 18,
      top: 48,
      bottom: 24,
      containLabel: true,
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: labels,
      axisLine: { lineStyle: { color: '#cbd5e1' } },
    },
    yAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: '#e2e8f0' } },
    },
    series: [
      {
        name: '总预约',
        type: 'line',
        smooth: true,
        areaStyle: { color: 'rgba(15, 118, 110, 0.10)' },
        data: dashboard.value.trend.map((item) => item.total),
      },
      {
        name: '进行中',
        type: 'line',
        smooth: true,
        data: dashboard.value.trend.map((item) => item.ongoing),
      },
      {
        name: '未开始',
        type: 'line',
        smooth: true,
        data: dashboard.value.trend.map((item) => item.upcoming),
      },
      {
        name: '已取消',
        type: 'line',
        smooth: true,
        data: dashboard.value.trend.map((item) => item.cancelled),
      },
    ],
  })
}

const renderStatusChart = () => {
  const chart = ensureChart('status', statusChartRef.value)
  if (!chart || !dashboard.value) {
    return
  }

  chart.setOption({
    color: ['#0f766e', '#2563eb', '#94a3b8', '#f59e0b', '#ef4444'],
    tooltip: { trigger: 'item' },
    series: [
      {
        type: 'pie',
        radius: ['45%', '72%'],
        center: ['50%', '52%'],
        label: {
          formatter: '{b}\n{c}',
        },
        data: dashboard.value.status_breakdown.map((item) => ({
          name: item.label,
          value: item.count,
        })),
      },
    ],
  })
}

const renderToolRankingChart = () => {
  const chart = ensureChart('tool', toolChartRef.value)
  if (!chart || !dashboard.value) {
    return
  }

  const reversed = [...dashboard.value.tool_rankings].reverse()

  chart.setOption({
    color: ['#0ea5e9'],
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (params: any) => {
        const current = params?.[0]?.data
        if (!current) {
          return ''
        }
        return `${current.name}<br/>预约数: ${current.value}<br/>时长: ${current.hours} h`
      },
    },
    grid: {
      left: 18,
      right: 24,
      top: 18,
      bottom: 12,
      containLabel: true,
    },
    xAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: '#e2e8f0' } },
    },
    yAxis: {
      type: 'category',
      data: reversed.map((item) => item.name),
      axisLabel: { width: 110, overflow: 'truncate' },
    },
    series: [
      {
        name: '热门仪器',
        type: 'bar',
        barWidth: 16,
        borderRadius: 999,
        data: reversed.map((item) => ({
          value: item.reservation_count,
          name: item.name,
          hours: item.total_hours,
        })),
      },
    ],
  })
}

const renderCharts = () => {
  renderTrendChart()
  renderStatusChart()
  renderToolRankingChart()
}

const resizeCharts = () => {
  Object.values(chartInstances).forEach((chart) => chart?.resize())
}

const disposeCharts = () => {
  Object.values(chartInstances).forEach((chart) => chart?.dispose())
  Object.keys(chartInstances).forEach((key) => delete chartInstances[key as ChartKey])
}

watch(
  dashboard,
  async (value) => {
    if (!value) {
      return
    }
    await nextTick()
    renderCharts()
  },
  { deep: true }
)

onMounted(async () => {
  await loadDashboard({ days: presetDays.value })
  window.addEventListener('resize', resizeCharts)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', resizeCharts)
  disposeCharts()
})
</script>

<style scoped>
.dashboard-page {
  --dash-bg: linear-gradient(135deg, #f8fafc 0%, #eef7f5 48%, #fff4eb 100%);
  --dash-surface: rgba(255, 255, 255, 0.82);
  --dash-border: rgba(148, 163, 184, 0.2);
  --dash-text: #0f172a;
  --dash-muted: #64748b;
  --dash-teal: #0f766e;
  --dash-blue: #2563eb;
  --dash-orange: #f97316;
  --dash-red: #ef4444;
  --dash-shadow: 0 24px 60px rgba(15, 23, 42, 0.08);
  padding: 20px;
  background: var(--dash-bg);
  border-radius: 28px;
}

.hero-shell {
  position: relative;
  display: grid;
  grid-template-columns: 1.4fr 1fr;
  gap: 20px;
  padding: 28px;
  margin-bottom: 18px;
  background:
    radial-gradient(circle at top right, rgba(14, 165, 233, 0.22), transparent 32%),
    radial-gradient(circle at bottom left, rgba(249, 115, 22, 0.18), transparent 30%),
    rgba(15, 23, 42, 0.96);
  border-radius: 26px;
  color: #f8fafc;
  overflow: hidden;
}

.hero-kicker {
  margin-bottom: 10px;
  font-size: 12px;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: rgba(226, 232, 240, 0.72);
}

.hero-title {
  margin-bottom: 12px;
  font-size: 34px;
  line-height: 1.15;
  font-family: 'Avenir Next', 'PingFang SC', 'Microsoft YaHei', sans-serif;
}

.hero-description {
  max-width: 640px;
  color: rgba(226, 232, 240, 0.86);
  line-height: 1.7;
}

.hero-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 18px;
}

.hero-meta-item {
  padding: 8px 12px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.08);
  font-size: 13px;
}

.hero-controls {
  display: flex;
  flex-direction: column;
  gap: 14px;
  align-items: flex-end;
  justify-content: center;
}

.hero-date-picker {
  width: min(100%, 320px);
}

.hero-actions {
  display: flex;
  gap: 10px;
}

.status-strip {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 18px;
}

.status-pill {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px;
  border-radius: 18px;
  background: var(--dash-surface);
  border: 1px solid var(--dash-border);
  box-shadow: var(--dash-shadow);
}

.status-pill span {
  color: var(--dash-muted);
  font-size: 13px;
}

.status-pill strong {
  font-size: 22px;
  color: var(--dash-text);
}

.status-ongoing {
  border-color: rgba(15, 118, 110, 0.25);
}

.status-upcoming {
  border-color: rgba(37, 99, 235, 0.25);
}

.status-completed {
  border-color: rgba(148, 163, 184, 0.25);
}

.status-cancelled {
  border-color: rgba(245, 158, 11, 0.25);
}

.status-missed {
  border-color: rgba(239, 68, 68, 0.25);
}

.stat-row {
  margin-bottom: 6px;
}

.stat-card {
  border-radius: 22px;
  border: 1px solid var(--dash-border);
  background: var(--dash-surface);
  box-shadow: var(--dash-shadow);
}

.stat-card-top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.stat-label {
  color: var(--dash-muted);
  font-size: 13px;
}

.stat-value {
  margin-top: 10px;
  font-size: 34px;
  font-weight: 700;
  color: var(--dash-text);
  line-height: 1;
}

.stat-icon {
  width: 52px;
  height: 52px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 16px;
  font-size: 24px;
  color: #fff;
}

.accent-user .stat-icon {
  background: linear-gradient(135deg, #2563eb, #38bdf8);
}

.accent-reservation .stat-icon {
  background: linear-gradient(135deg, #0f766e, #34d399);
}

.accent-hours .stat-icon {
  background: linear-gradient(135deg, #f97316, #fb923c);
}

.accent-task .stat-icon {
  background: linear-gradient(135deg, #7c3aed, #3b82f6);
}

.stat-note {
  margin-top: 16px;
  color: var(--dash-muted);
  font-size: 13px;
}

.chart-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 18px;
  margin-top: 18px;
}

.panel-card,
.profile-card,
.table-panel,
.user-report-panel {
  border-radius: 24px;
  border: 1px solid var(--dash-border);
  background: var(--dash-surface);
  box-shadow: var(--dash-shadow);
}

.panel-header {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.panel-header span {
  font-size: 16px;
  font-weight: 600;
  color: var(--dash-text);
}

.panel-header small {
  color: var(--dash-muted);
}

.chart-panel {
  height: 320px;
}

.detail-grid {
  display: grid;
  grid-template-columns: 1.1fr 1.4fr 1.3fr;
  gap: 18px;
  margin-top: 18px;
}

.profile-title-block {
  margin-bottom: 14px;
}

.profile-name {
  font-size: 28px;
  line-height: 1.2;
  color: var(--dash-text);
  font-family: 'Avenir Next', 'PingFang SC', 'Microsoft YaHei', sans-serif;
}

.profile-subtitle {
  margin-top: 6px;
  color: var(--dash-muted);
}

.profile-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 16px;
}

.profile-metrics {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 16px;
}

.profile-metric {
  padding: 14px;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.7);
  border: 1px solid rgba(148, 163, 184, 0.18);
}

.profile-metric span {
  display: block;
  color: var(--dash-muted);
  font-size: 12px;
}

.profile-metric strong {
  display: block;
  margin-top: 8px;
  font-size: 22px;
  color: var(--dash-text);
}

.completion-block {
  margin-bottom: 18px;
  padding: 14px 16px;
  border-radius: 18px;
  background: linear-gradient(
    135deg,
    rgba(15, 118, 110, 0.09),
    rgba(37, 99, 235, 0.06)
  );
}

.completion-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
  color: var(--dash-text);
}

.profile-summary-list {
  display: grid;
  gap: 12px;
}

.profile-summary-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding-bottom: 10px;
  border-bottom: 1px dashed rgba(148, 163, 184, 0.25);
}

.profile-summary-item span {
  color: var(--dash-muted);
}

.profile-summary-item strong {
  color: var(--dash-text);
  text-align: right;
}

.user-report-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.user-cell {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.user-cell strong {
  color: var(--dash-text);
}

.user-cell span {
  color: var(--dash-muted);
  font-size: 12px;
}

.user-status-cell {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

@media (max-width: 1400px) {
  .chart-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 1280px) {
  .detail-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 1100px) {
  .hero-shell,
  .chart-grid {
    grid-template-columns: 1fr;
  }

  .hero-controls {
    align-items: stretch;
  }

  .status-strip {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 768px) {
  .dashboard-page {
    padding: 12px;
    border-radius: 18px;
  }

  .hero-shell {
    padding: 20px;
  }

  .hero-title {
    font-size: 28px;
  }

  .status-strip,
  .profile-metrics {
    grid-template-columns: 1fr;
  }

  .chart-panel {
    height: 280px;
  }

  .user-report-header {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
