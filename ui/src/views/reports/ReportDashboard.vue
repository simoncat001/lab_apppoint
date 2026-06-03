<template>
  <div class="reports-page" v-loading="loading">
    <section class="report-header">
      <div>
        <div class="eyebrow">CURRENT PROJECT REPORT</div>
        <h1>{{ currentProjectName }} 数据报表</h1>
        <p>{{ periodText }}</p>
      </div>

      <div class="report-actions">
        <el-date-picker
          v-model="dateRange"
          type="daterange"
          range-separator="至"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          value-format="YYYY-MM-DD"
          unlink-panels
        />
        <div class="quick-actions">
          <el-button plain @click="applyQuickRange(7)">近 7 天</el-button>
          <el-button plain @click="applyQuickRange(30)">近 30 天</el-button>
          <el-button plain @click="clearRange">全部</el-button>
          <el-button type="primary" :icon="RefreshRight" @click="loadReports">刷新</el-button>
        </div>
      </div>
    </section>

    <section class="metric-grid">
      <article v-for="card in statCards" :key="card.label" class="metric-card">
        <div class="metric-icon" :class="`tone-${card.tone}`">
          <component :is="card.icon" />
        </div>
        <div>
          <span>{{ card.label }}</span>
          <strong>{{ card.value }}</strong>
          <small>{{ card.note }}</small>
        </div>
      </article>
    </section>

    <section class="analysis-grid">
      <div class="panel tool-ranking">
        <div class="panel-head">
          <div>
            <div class="eyebrow">INSTRUMENT RANKING</div>
            <h2>仪器活跃排行</h2>
          </div>
          <el-tag type="primary" effect="plain">当前项目</el-tag>
        </div>

        <div v-if="topTools.length" class="ranking-list">
          <article v-for="(tool, index) in topTools" :key="tool.tool_id" class="ranking-row">
            <div class="rank-no">{{ index + 1 }}</div>
            <div class="rank-content">
              <div class="rank-title">
                <strong>{{ tool.tool_name }}</strong>
                <span>{{ tool.reservation_count }} 次预约</span>
              </div>
              <div class="rank-track">
                <div class="rank-fill" :style="{ width: `${getToolShare(tool.reservation_count)}%` }" />
              </div>
            </div>
          </article>
        </div>
        <el-empty v-else description="当前周期暂无仪器预约数据" />
      </div>

      <div class="panel insights-panel">
        <div class="panel-head">
          <div>
            <div class="eyebrow">INSTRUMENT INSIGHTS</div>
            <h2>核心洞察</h2>
          </div>
          <el-tag type="success" effect="plain">仪器视角</el-tag>
        </div>

        <div class="insight-grid">
          <article class="insight-item">
            <span>最活跃仪器</span>
            <strong>{{ mostActiveToolName }}</strong>
            <small>{{ mostActiveTool?.reservation_count ?? 0 }} 次预约</small>
          </article>
          <article class="insight-item">
            <span>仪器覆盖率</span>
            <strong>{{ formatPercent(toolCoverageRate) }}</strong>
            <small>{{ currentProjectReport?.active_tool_count ?? 0 }} / {{ currentProjectReport?.tool_count ?? 0 }} 台有预约</small>
          </article>
          <article class="insight-item">
            <span>空闲仪器</span>
            <strong>{{ currentProjectReport?.idle_tool_count ?? 0 }}</strong>
            <small>当前周期未产生预约</small>
          </article>
          <article class="insight-item">
            <span>取消率</span>
            <strong>{{ formatPercent(cancelRate) }}</strong>
            <small>{{ reservationReport.cancelled }} / {{ reservationReport.total }} 次预约取消</small>
          </article>
          <article class="insight-item">
            <span>收费使用</span>
            <strong>{{ reservationReport.paid }}</strong>
            <small>已验证且未减免的使用记录</small>
          </article>
          <article class="insight-item">
            <span>项目用户</span>
            <strong>{{ userReport.total }}</strong>
            <small>周期内产生预约的用户</small>
          </article>
        </div>
      </div>
    </section>

    <section class="panel project-snapshot">
      <div class="panel-head">
        <div>
          <div class="eyebrow">PROJECT SNAPSHOT</div>
          <h2>当前项目概况</h2>
        </div>
        <el-tag :type="currentProjectReport?.active ? 'success' : 'danger'" effect="plain">
          {{ currentProjectReport?.active ? '启用中' : '已停用' }}
        </el-tag>
      </div>

      <div class="snapshot-grid">
        <div class="snapshot-item">
          <span>项目名称</span>
          <strong>{{ currentProjectName }}</strong>
        </div>
        <div class="snapshot-item">
          <span>仪器总数</span>
          <strong>{{ currentProjectReport?.tool_count ?? 0 }}</strong>
        </div>
        <div class="snapshot-item">
          <span>预约总数</span>
          <strong>{{ currentProjectReport?.reservation_count ?? 0 }}</strong>
        </div>
        <div class="snapshot-item">
          <span>取消预约</span>
          <strong>{{ currentProjectReport?.cancelled_reservation_count ?? 0 }}</strong>
        </div>
        <div class="snapshot-item">
          <span>收费使用</span>
          <strong>{{ currentProjectReport?.paid_usage_count ?? 0 }}</strong>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import dayjs from 'dayjs'
import { Calendar, DataAnalysis, RefreshRight, Tickets, User } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { getProjectReport, getReservationReport, getToolReport, getUserReport } from '@/api/reports'
import { useProjectContextStore } from '@/stores/project-context'
import type {
  ProjectReportGlobalTool,
  ProjectReportItem,
  ProjectReportSummary,
  ReservationReport,
  ToolReport,
  UserReport,
} from '@/types'

const projectStore = useProjectContextStore()
projectStore.hydrate()

const loading = ref(false)
const dateRange = ref<string[]>([])

const userReport = reactive<UserReport>({
  total: 0,
  active: 0,
  new_count: 0,
  login_count: 0,
  export_count: 0,
})
const reservationReport = reactive<ReservationReport>({
  total: 0,
  cancelled: 0,
  paid: 0,
})
const toolReport = reactive<ToolReport>({
  total: 0,
  usage_by_tool: {},
})
const projectSummary = ref<ProjectReportSummary | null>(null)

const currentProjectName = computed(() => projectStore.currentProjectName || '当前项目')
const currentProjectReport = computed<ProjectReportItem | null>(() => {
  return projectSummary.value?.project_reports?.[0] || null
})
const topTools = computed<ProjectReportGlobalTool[]>(() => projectSummary.value?.top_tools ?? [])
const mostActiveTool = computed(() => topTools.value[0] || null)
const mostActiveToolName = computed(() => mostActiveTool.value?.tool_name || '暂无')
const maxToolReservations = computed(() =>
  Math.max(...topTools.value.map((tool) => tool.reservation_count), 1)
)
const toolCoverageRate = computed(() => {
  const report = currentProjectReport.value
  if (!report?.tool_count) return 0
  return report.active_tool_count / report.tool_count
})
const cancelRate = computed(() => {
  if (!reservationReport.total) return 0
  return reservationReport.cancelled / reservationReport.total
})

const buildParams = () => {
  if (dateRange.value.length === 2) {
    return {
      start_date: dateRange.value[0],
      end_date: dateRange.value[1],
    }
  }
  return undefined
}

const applyQuickRange = (days: number) => {
  const end = dayjs().format('YYYY-MM-DD')
  const start = dayjs().subtract(days - 1, 'day').format('YYYY-MM-DD')
  dateRange.value = [start, end]
  loadReports()
}

const clearRange = () => {
  dateRange.value = []
  loadReports()
}

const loadReports = async () => {
  loading.value = true
  try {
    const params = buildParams()
    const [userData, reservationData, toolData, projectData] = await Promise.all([
      getUserReport(params),
      getReservationReport(params),
      getToolReport(params),
      getProjectReport(params),
    ])

    Object.assign(userReport, userData)
    Object.assign(reservationReport, reservationData)
    Object.assign(toolReport, toolData)
    projectSummary.value = projectData
  } catch (error) {
    console.error(error)
    ElMessage.error('加载报表失败')
  } finally {
    loading.value = false
  }
}

const statCards = computed(() => [
  {
    label: '项目仪器',
    value: toolReport.total,
    note: `活跃 ${currentProjectReport.value?.active_tool_count ?? 0} / 空闲 ${currentProjectReport.value?.idle_tool_count ?? 0}`,
    tone: 'teal',
    icon: Tickets,
  },
  {
    label: '预约总数',
    value: reservationReport.total,
    note: `取消 ${reservationReport.cancelled}`,
    tone: 'amber',
    icon: Calendar,
  },
  {
    label: '收费使用',
    value: reservationReport.paid,
    note: '已验证且未减免',
    tone: 'blue',
    icon: DataAnalysis,
  },
  {
    label: '项目用户',
    value: userReport.total,
    note: `活跃 ${userReport.active} / 新增 ${userReport.new_count}`,
    tone: 'slate',
    icon: User,
  },
])

const getToolShare = (count: number) => {
  if (!count) return 0
  return Math.max(8, Math.round((count / maxToolReservations.value) * 100))
}

const formatPercent = (value: number) => `${Math.round(value * 100)}%`

const periodText = computed(() => {
  if (dateRange.value.length === 2) {
    return `统计周期 ${dateRange.value[0]} 至 ${dateRange.value[1]}`
  }
  return '统计周期 全部数据'
})

onMounted(() => {
  loadReports()
})
</script>

<style scoped>
.reports-page {
  --report-bg: #f5f7fb;
  --report-surface: #ffffff;
  --report-line: #d8e0ea;
  --report-text: #172033;
  --report-muted: #64748b;
  --report-teal: #0f766e;
  --report-blue: #2563eb;
  --report-amber: #b45309;
  min-height: 100%;
  padding: 20px;
  background: var(--report-bg);
  color: var(--report-text);
}

.report-header,
.panel,
.metric-card {
  border: 1px solid var(--report-line);
  border-radius: 8px;
  background: var(--report-surface);
}

.report-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
  padding: 20px;
}

.eyebrow {
  color: var(--report-teal);
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0;
}

h1,
h2 {
  margin: 0;
  color: var(--report-text);
  font-weight: 700;
}

h1 {
  margin-top: 6px;
  font-size: 24px;
}

h2 {
  margin-top: 4px;
  font-size: 18px;
}

.report-header p {
  margin: 8px 0 0;
  color: var(--report-muted);
}

.report-actions {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 12px;
}

.quick-actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 8px;
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  margin-top: 12px;
}

.metric-card {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 16px;
}

.metric-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 42px;
  height: 42px;
  border-radius: 8px;
  font-size: 22px;
}

.tone-teal {
  color: var(--report-teal);
  background: #e7f4f1;
}

.tone-blue {
  color: var(--report-blue);
  background: #eaf1ff;
}

.tone-amber {
  color: var(--report-amber);
  background: #fff3df;
}

.tone-slate {
  color: #475569;
  background: #eef2f7;
}

.metric-card span,
.metric-card small,
.insight-item span,
.insight-item small,
.snapshot-item span {
  display: block;
  color: var(--report-muted);
  font-size: 13px;
}

.metric-card strong {
  display: block;
  margin-top: 4px;
  font-size: 26px;
  line-height: 1.1;
}

.metric-card small {
  margin-top: 6px;
}

.analysis-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.1fr) minmax(360px, 0.9fr);
  gap: 12px;
  margin-top: 12px;
}

.panel {
  padding: 18px;
}

.panel-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 16px;
}

.ranking-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.ranking-row {
  display: grid;
  grid-template-columns: 36px minmax(0, 1fr);
  gap: 12px;
  align-items: center;
  padding: 12px;
  border: 1px solid #e6ebf2;
  border-radius: 8px;
  background: #fbfcfe;
}

.rank-no {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: 8px;
  background: #172033;
  color: #fff;
  font-weight: 700;
}

.rank-title {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;
}

.rank-title span {
  color: var(--report-muted);
  white-space: nowrap;
}

.rank-track {
  height: 8px;
  overflow: hidden;
  border-radius: 999px;
  background: #e6ebf2;
}

.rank-fill {
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, var(--report-teal), var(--report-blue));
}

.insight-grid,
.snapshot-grid {
  display: grid;
  gap: 10px;
}

.insight-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.insight-item,
.snapshot-item {
  padding: 14px;
  border: 1px solid #e6ebf2;
  border-radius: 8px;
  background: #fbfcfe;
}

.insight-item strong,
.snapshot-item strong {
  display: block;
  margin-top: 8px;
  font-size: 20px;
  line-height: 1.2;
}

.insight-item small {
  margin-top: 6px;
}

.project-snapshot {
  margin-top: 12px;
}

.snapshot-grid {
  grid-template-columns: 1.4fr repeat(4, minmax(0, 1fr));
}

@media (max-width: 1180px) {
  .metric-grid,
  .analysis-grid,
  .snapshot-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 760px) {
  .reports-page {
    padding: 12px;
  }

  .report-header,
  .report-actions,
  .panel-head,
  .rank-title {
    align-items: stretch;
    flex-direction: column;
  }

  .metric-grid,
  .analysis-grid,
  .insight-grid,
  .snapshot-grid {
    grid-template-columns: 1fr;
  }

  .report-actions {
    width: 100%;
  }

  .quick-actions {
    justify-content: flex-start;
  }
}
</style>
