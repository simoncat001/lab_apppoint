<template>
  <div class="page-container">
    <el-card v-loading="loading" class="detail-card" shadow="never">
      <div class="detail-toolbar">
        <el-button :icon="Back" @click="handleBack">返回</el-button>
        <el-space wrap>
          <el-button type="primary" plain @click="goEditPage">编辑</el-button>
          <el-button v-if="record?.status === 'draft'" type="success" plain @click="handlePublish">
            发布
          </el-button>
          <el-button v-if="record?.status === 'published'" type="warning" plain @click="handleArchive">
            归档
          </el-button>
          <el-button type="danger" plain @click="handleDelete">删除</el-button>
        </el-space>
      </div>

      <template v-if="record">
        <header class="article-header">
          <div class="article-tags">
            <el-tag effect="plain">{{ getRecordTypeLabel(record.record_type) }}</el-tag>
            <el-tag :type="getStatusTagType(record.status)" effect="plain">{{ getStatusLabel(record.status) }}</el-tag>
            <el-tag effect="plain">{{ getVisibilityLabel(record.visibility) }}</el-tag>
            <el-tag v-if="record.pinned" type="warning" effect="plain">置顶</el-tag>
          </div>

          <h1>{{ record.title }}</h1>
          <div class="article-meta">
            <span>{{ getAuthorName(record) }}</span>
            <span>创建于 {{ formatDateTime(record.created_at) }}</span>
            <span>更新于 {{ formatDateTime(record.updated_at || record.created_at) }}</span>
          </div>
        </header>

        <div class="article-divider" />

        <div
          v-if="record.content_format === 'html'"
          class="record-content record-content--html"
          v-html="record.content"
        />
        <pre v-else class="record-content">{{ record.content }}</pre>
      </template>

      <el-empty v-else-if="!loading" description="协作记录不存在或无权限查看" />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Back } from '@element-plus/icons-vue'
import {
  archiveCollaborationRecord,
  deleteCollaborationRecord,
  getCollaborationRecord,
  publishCollaborationRecord,
} from '@/api/collaboration'
import type { CollaborationRecord, CollaborationRecordType } from '@/types'
import { formatDateTime } from '@/utils/helpers'

const route = useRoute()
const router = useRouter()

const loading = ref(false)
const record = ref<CollaborationRecord | null>(null)
const recordId = computed(() => Number(route.params.id))

const recordTypeLabels: Record<CollaborationRecordType, string> = {
  tool_note: '仪器笔记',
  reservation_note: '预约笔记',
  experiment_note: '实验过程',
  maintenance_experience: '维护经验',
  sop: 'SOP',
  faq: 'FAQ',
  case_study: '案例',
  issue: '问题记录',
}

const getRecordTypeLabel = (type: CollaborationRecordType) => recordTypeLabels[type] || type

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

const getAuthorName = (item: CollaborationRecord) => {
  return item.author_display_name || item.author_username || `作者 #${item.author_id}`
}

const queryString = (key: string) => {
  const raw = route.query[key]
  return Array.isArray(raw) ? raw[0] : raw
}

const getBackPath = () => {
  const redirect = queryString('redirect')
  if (redirect) return redirect
  if (record.value?.tool_id) return `/tools/${record.value.tool_id}`
  return '/collaboration-records'
}

const normalizeRecord = (response: unknown) => {
  return (response as any)?.data ? (response as any).data as CollaborationRecord : response as CollaborationRecord
}

const loadRecord = async () => {
  if (!Number.isFinite(recordId.value)) {
    ElMessage.error('协作记录 ID 无效')
    router.replace('/collaboration-records')
    return
  }
  loading.value = true
  try {
    record.value = normalizeRecord(await getCollaborationRecord(recordId.value))
  } catch (error) {
    console.error(error)
    ElMessage.error('加载协作记录失败')
    record.value = null
  } finally {
    loading.value = false
  }
}

const handleBack = () => {
  router.push(getBackPath())
}

const goEditPage = () => {
  if (!record.value) return
  router.push({
    name: 'CollaborationRecordEdit',
    params: { id: record.value.id },
    query: { redirect: route.fullPath },
  })
}

const handlePublish = async () => {
  if (!record.value) return
  try {
    record.value = normalizeRecord(await publishCollaborationRecord(record.value.id))
    ElMessage.success('已发布')
  } catch (error) {
    console.error(error)
    ElMessage.error('发布失败，请确认当前账号有权限')
  }
}

const handleArchive = async () => {
  if (!record.value) return
  try {
    record.value = normalizeRecord(await archiveCollaborationRecord(record.value.id))
    ElMessage.success('已归档')
  } catch (error) {
    console.error(error)
    ElMessage.error('归档失败')
  }
}

const handleDelete = async () => {
  if (!record.value) return
  try {
    await ElMessageBox.confirm(`确定删除“${record.value.title}”吗？`, '删除协作记录')
    await deleteCollaborationRecord(record.value.id)
    ElMessage.success('已删除')
    router.push(getBackPath())
  } catch (error) {
    if (error !== 'cancel') {
      console.error(error)
      ElMessage.error('删除失败')
    }
  }
}

onMounted(loadRecord)
</script>

<style scoped>
.page-container {
  min-height: calc(100vh - 60px);
  padding: 24px;
  background: #f6f7f9;
}

.detail-card {
  max-width: 1040px;
  margin: 0 auto;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  background: #ffffff;
}

.detail-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
  padding-bottom: 18px;
  border-bottom: 1px solid #eef0f3;
}

.article-header {
  padding: 26px 0 8px;
}

.article-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 16px;
}

.article-header h1 {
  margin: 0;
  color: #111827;
  font-size: 32px;
  font-weight: 700;
  line-height: 1.35;
  letter-spacing: -0.02em;
}

.article-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 14px;
  margin-top: 12px;
  color: #6b7280;
  font-size: 13px;
}

.article-meta span + span::before {
  content: "·";
  margin-right: 14px;
  color: #c0c4cc;
}

.article-divider {
  margin: 24px 0;
  border-top: 1px solid #eef0f3;
}

.record-content {
  margin: 0;
  min-height: 260px;
  white-space: pre-wrap;
  word-break: break-word;
  color: #1f2937;
  font-family: inherit;
  font-size: 15px;
  line-height: 1.85;
}

.record-content--html {
  white-space: normal;
}

.record-content--html :deep(p) {
  margin: 0 0 14px;
}

.record-content--html :deep(img),
.record-content--html :deep(video) {
  display: block;
  max-width: 100%;
  margin: 16px auto;
  border-radius: 8px;
}

.record-content--html :deep(h1),
.record-content--html :deep(h2),
.record-content--html :deep(h3) {
  margin: 24px 0 10px;
  color: #111827;
  line-height: 1.35;
}

.record-content--html :deep(blockquote) {
  margin: 18px 0;
  padding: 10px 14px;
  border-left: 3px solid #d1d5db;
  color: #4b5563;
  background: #f9fafb;
}

.record-content--html :deep(pre) {
  overflow-x: auto;
  padding: 14px;
  border-radius: 8px;
  color: #e5e7eb;
  background: #1f2937;
}

.record-content--html :deep(code) {
  padding: 2px 5px;
  border-radius: 4px;
  color: #374151;
  background: #f3f4f6;
}

.record-content--html :deep(pre code) {
  padding: 0;
  color: inherit;
  background: transparent;
}

.record-content--html :deep(table) {
  width: 100%;
  border-collapse: collapse;
  margin: 18px 0;
}

.record-content--html :deep(th),
.record-content--html :deep(td) {
  padding: 9px 10px;
  border: 1px solid #e5e7eb;
}

.record-content--html :deep(th) {
  background: #f9fafb;
}

.record-content--html :deep(ul),
.record-content--html :deep(ol) {
  padding-left: 22px;
}

@media (max-width: 768px) {
  .page-container {
    padding: 12px;
  }

  .detail-card {
    border-radius: 10px;
  }

  .article-header h1 {
    font-size: 24px;
  }
}
</style>
