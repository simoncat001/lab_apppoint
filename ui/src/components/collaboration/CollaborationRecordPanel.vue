<template>
  <div class="collaboration-panel">
    <div class="collaboration-toolbar">
      <div class="collaboration-toolbar__filters">
        <el-select
          v-model="filters.record_type"
          placeholder="记录类型"
          clearable
          style="width: 160px"
          @change="handleFilterChange"
        >
          <el-option v-for="item in recordTypeOptions" :key="item.value" :label="item.label" :value="item.value" />
        </el-select>
        <el-select
          v-model="filters.status"
          placeholder="状态"
          clearable
          style="width: 120px"
          @change="handleFilterChange"
        >
          <el-option label="草稿" value="draft" />
          <el-option label="已发布" value="published" />
          <el-option label="已归档" value="archived" />
        </el-select>
        <el-input
          v-model="filters.keyword"
          placeholder="搜索标题或内容"
          clearable
          style="width: 220px"
          @keyup.enter="handleFilterChange"
          @clear="handleFilterChange"
        />
        <el-checkbox v-model="filters.mine" @change="handleFilterChange">我发布的</el-checkbox>
      </div>
      <el-space>
        <el-button :icon="Refresh" @click="loadRecords">刷新</el-button>
        <el-button type="primary" :icon="Plus" :disabled="!allowCreate" @click="goCreatePage">新增记录</el-button>
      </el-space>
    </div>

    <div v-loading="loading" class="record-feed" :class="{ 'record-feed--compact': compact }">
      <article v-for="record in records" :key="record.id" class="record-card">
        <div class="record-card__avatar">
          {{ getRecordInitial(record) }}
        </div>
        <div class="record-card__main">
          <div class="record-card__head">
            <div class="record-card__title-group">
              <div class="record-card__title">
                <span>{{ record.title }}</span>
                <el-tag v-if="record.pinned" size="small" type="warning" effect="plain">置顶</el-tag>
              </div>
              <div class="record-card__meta">
                <span>{{ getRecordTypeLabel(record.record_type) }}</span>
                <span>{{ getAuthorName(record) }}</span>
                <span>{{ formatDateTime(record.updated_at || record.created_at) }}</span>
              </div>
            </div>
            <div class="record-card__tags">
              <el-tag size="small" effect="plain">{{ getVisibilityLabel(record.visibility) }}</el-tag>
              <el-tag size="small" :type="getStatusTagType(record.status)">
                {{ getStatusLabel(record.status) }}
              </el-tag>
            </div>
          </div>

          <div class="record-card__preview" @click="goDetailPage(record)">
            {{ getContentPreview(record) || '暂无内容摘要' }}
          </div>

          <div class="record-card__actions">
            <el-button text size="small" @click="goDetailPage(record)">查看</el-button>
            <el-button text size="small" type="primary" @click="goEditPage(record)">编辑</el-button>
            <el-button v-if="record.status === 'draft'" text size="small" type="success" @click="handlePublish(record)">
              发布
            </el-button>
            <el-button v-if="record.status === 'published'" text size="small" type="warning" @click="handleArchive(record)">
              归档
            </el-button>
            <el-button text size="small" type="danger" @click="handleDelete(record)">删除</el-button>
          </div>
        </div>
      </article>
    </div>

    <el-empty v-if="!records.length && !loading" description="暂无协作记录" />

    <div class="pagination-container">
      <el-pagination
        v-model:current-page="page"
        v-model:page-size="pageSize"
        :total="total"
        :page-sizes="[5, 10, 20, 50]"
        layout="total, sizes, prev, pager, next"
        @size-change="loadRecords"
        @current-change="loadRecords"
      />
    </div>

  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Refresh } from '@element-plus/icons-vue'
import {
  archiveCollaborationRecord,
  deleteCollaborationRecord,
  getCollaborationRecords,
  publishCollaborationRecord,
} from '@/api/collaboration'
import type {
  CollaborationRecord,
  CollaborationRecordType,
  CollaborationStatus,
} from '@/types'
import { formatDateTime } from '@/utils/helpers'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const props = withDefaults(
  defineProps<{
    toolId?: number
    reservationId?: number
    compact?: boolean
    defaultRecordType?: CollaborationRecordType
    allowCreate?: boolean
  }>(),
  {
    compact: false,
    defaultRecordType: 'tool_note',
    allowCreate: true,
  },
)

const canCreateKnowledgeRecords = computed(() => authStore.isStaff() || authStore.isSuperuser())

const recordTypeOptions = computed(() => {
  if (props.reservationId) {
    return [
      { label: '预约笔记', value: 'reservation_note' },
      { label: '实验过程', value: 'experiment_note' },
      { label: '问题记录', value: 'issue' },
    ] as Array<{ label: string; value: CollaborationRecordType }>
  }
  if (!props.toolId) {
    const options = [
      { label: '仪器笔记', value: 'tool_note' },
      { label: '预约笔记', value: 'reservation_note' },
      { label: '实验过程', value: 'experiment_note' },
      { label: '问题记录', value: 'issue' },
    ] as Array<{ label: string; value: CollaborationRecordType }>
    if (canCreateKnowledgeRecords.value) {
      options.splice(
        3,
        0,
        { label: '维护经验', value: 'maintenance_experience' },
        { label: 'SOP', value: 'sop' },
        { label: 'FAQ', value: 'faq' },
        { label: '案例', value: 'case_study' },
      )
    }
    return options
  }
  const options = [
    { label: '仪器笔记', value: 'tool_note' },
    { label: '问题记录', value: 'issue' },
  ] as Array<{ label: string; value: CollaborationRecordType }>
  if (canCreateKnowledgeRecords.value) {
    options.splice(
      1,
      0,
      { label: '维护经验', value: 'maintenance_experience' },
      { label: 'SOP', value: 'sop' },
      { label: 'FAQ', value: 'faq' },
      { label: '案例', value: 'case_study' },
    )
  }
  return options
})

const loading = ref(false)
const records = ref<CollaborationRecord[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(props.compact ? 5 : 10)
const filters = reactive<{
  record_type?: CollaborationRecordType
  status?: CollaborationStatus
  keyword?: string
  mine?: boolean
}>({})

const getRecordTypeLabel = (type: CollaborationRecordType) => {
  return recordTypeOptions.value.find(item => item.value === type)?.label || type
}

const getVisibilityLabel = (visibility: string) => {
  const map: Record<string, string> = {
    project: '项目可见',
    staff: '管理员',
    tool_managers: '仪器管理员',
    author_private: '仅作者',
  }
  return map[visibility] || visibility
}

const getStatusLabel = (status: string) => {
  const map: Record<string, string> = {
    draft: '草稿',
    published: '已发布',
    archived: '已归档',
  }
  return map[status] || status
}

const getStatusTagType = (status: string) => {
  if (status === 'published') return 'success'
  if (status === 'archived') return 'info'
  return 'warning'
}

const stripHtml = (value: string) => {
  return value
    .replace(/<style[\s\S]*?<\/style>/gi, ' ')
    .replace(/<script[\s\S]*?<\/script>/gi, ' ')
    .replace(/<[^>]+>/g, ' ')
    .replace(/&nbsp;/g, ' ')
    .replace(/&amp;/g, '&')
    .replace(/\s+/g, ' ')
    .trim()
}

const getContentPreview = (record: CollaborationRecord) => {
  return record.content_format === 'html' ? stripHtml(record.content) : record.content
}

const getAuthorName = (record: CollaborationRecord) => {
  return record.author_display_name || record.author_username || `作者 #${record.author_id}`
}

const getRecordInitial = (record: CollaborationRecord) => {
  return getAuthorName(record).slice(0, 1).toUpperCase() || '作'
}

const loadRecords = async () => {
  loading.value = true
  try {
    const result = await getCollaborationRecords({
      tool_id: props.toolId,
      reservation_id: props.reservationId,
      record_type: filters.record_type,
      status: filters.status,
      keyword: filters.keyword || undefined,
      mine: filters.mine || undefined,
      page: page.value,
      page_size: pageSize.value,
    })
    records.value = Array.isArray(result) ? result : []
    total.value = Number((result as any)._total ?? records.value.length)
  } catch (error) {
    ElMessage.error('加载协作记录失败')
    console.error(error)
  } finally {
    loading.value = false
  }
}

const handleFilterChange = () => {
  page.value = 1
  loadRecords()
}

const getRedirectPath = () => route.fullPath || '/collaboration-records'

const goCreatePage = () => {
  router.push({
    name: 'CollaborationRecordCreate',
    query: {
      ...(props.toolId ? { tool_id: String(props.toolId) } : {}),
      ...(props.reservationId ? { reservation_id: String(props.reservationId) } : {}),
      record_type: props.reservationId ? 'reservation_note' : props.defaultRecordType,
      redirect: getRedirectPath(),
    },
  })
}

const goEditPage = (record: CollaborationRecord) => {
  router.push({
    name: 'CollaborationRecordEdit',
    params: { id: record.id },
    query: { redirect: getRedirectPath() },
  })
}

const goDetailPage = (record: CollaborationRecord) => {
  router.push({
    name: 'CollaborationRecordDetail',
    params: { id: record.id },
    query: { redirect: getRedirectPath() },
  })
}

const handlePublish = async (record: CollaborationRecord) => {
  try {
    await publishCollaborationRecord(record.id)
    ElMessage.success('已发布')
    await loadRecords()
  } catch (error) {
    ElMessage.error('发布失败，请确认当前账号有权限')
    console.error(error)
  }
}

const handleArchive = async (record: CollaborationRecord) => {
  try {
    await archiveCollaborationRecord(record.id)
    ElMessage.success('已归档')
    await loadRecords()
  } catch (error) {
    ElMessage.error('归档失败')
    console.error(error)
  }
}

const handleDelete = async (record: CollaborationRecord) => {
  try {
    await ElMessageBox.confirm(`确定删除“${record.title}”吗？`, '删除协作记录')
    await deleteCollaborationRecord(record.id)
    ElMessage.success('已删除')
    await loadRecords()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
      console.error(error)
    }
  }
}

watch(
  () => [props.toolId, props.reservationId],
  () => {
    page.value = 1
    loadRecords()
  },
)

onMounted(loadRecords)
</script>

<style scoped>
.collaboration-panel {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.collaboration-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.collaboration-toolbar__filters {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
}

.pagination-container {
  display: flex;
  justify-content: flex-end;
}

.record-feed {
  display: flex;
  flex-direction: column;
  gap: 14px;
  min-height: 120px;
}

.record-card {
  display: grid;
  grid-template-columns: 46px minmax(0, 1fr);
  gap: 14px;
  padding: 18px;
  border: 1px solid #e2e8f0;
  border-radius: 18px;
  background:
    radial-gradient(circle at 4% 8%, rgba(59, 130, 246, 0.08), transparent 24%),
    #ffffff;
  box-shadow: 0 16px 40px rgba(15, 23, 42, 0.06);
}

.record-feed--compact .record-card {
  padding: 14px;
  border-radius: 14px;
}

.record-card__avatar {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 44px;
  height: 44px;
  border-radius: 50%;
  color: #ffffff;
  font-size: 18px;
  font-weight: 800;
  background: linear-gradient(135deg, #0f766e, #2563eb);
  box-shadow: 0 10px 24px rgba(37, 99, 235, 0.22);
}

.record-card__main {
  min-width: 0;
}

.record-card__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 14px;
}

.record-card__title-group {
  min-width: 0;
}

.record-card__title {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #0f172a;
  font-size: 16px;
  font-weight: 800;
  line-height: 1.35;
}

.record-card__title span:first-child {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.record-card__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 6px 10px;
  margin-top: 6px;
  color: #64748b;
  font-size: 12px;
}

.record-card__meta span + span::before {
  content: "·";
  margin-right: 10px;
  color: #cbd5e1;
}

.record-card__tags {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  flex-wrap: wrap;
  gap: 6px;
  flex-shrink: 0;
}

.record-card__preview {
  display: -webkit-box;
  margin-top: 14px;
  overflow: hidden;
  color: #334155;
  font-size: 14px;
  line-height: 1.75;
  word-break: break-word;
  cursor: pointer;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 4;
}

.record-feed--compact .record-card__preview {
  -webkit-line-clamp: 3;
}

.record-card__actions {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 4px;
  margin-top: 12px;
  padding-top: 10px;
  border-top: 1px solid #f1f5f9;
}

@media (max-width: 768px) {
  .collaboration-toolbar {
    align-items: stretch;
    flex-direction: column;
  }

  .record-card {
    grid-template-columns: 38px minmax(0, 1fr);
    padding: 14px;
  }

  .record-card__avatar {
    width: 38px;
    height: 38px;
    font-size: 16px;
  }

  .record-card__head {
    flex-direction: column;
  }

  .record-card__tags {
    justify-content: flex-start;
  }
}
</style>
