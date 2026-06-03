<template>
  <div class="page-container">
    <el-card shadow="never">
      <template #header>
        <div class="header-row">
          <el-button text @click="goBack">返回培训中心</el-button>
          <el-button :icon="Refresh" @click="loadPage">刷新</el-button>
        </div>
      </template>

      <div v-loading="loading">
        <template v-if="content">
          <div class="title-row">
            <h2 class="title">{{ content.title }}</h2>
            <el-tag :type="content.published ? 'success' : 'info'">
              {{ content.published ? '已发布' : '草稿' }}
            </el-tag>
          </div>

          <div class="meta">
            <span>创建时间：{{ formatDateTime(content.created_at) }}</span>
            <span>更新时间：{{ formatDateTime(content.updated_at) }}</span>
          </div>

          <div class="section">
            <div class="section-title">资料简介</div>
            <div class="section-content">{{ content.description || '暂无简介' }}</div>
          </div>

          <div class="section">
            <div class="section-title">{{ materialLabel }}</div>
            <el-space>
              <el-button
                type="primary"
                :disabled="!content.file_url"
                @click="openMaterial"
              >
                {{ actionLabel }}
              </el-button>
              <span class="muted">{{ content.file_url || emptyMaterialText }}</span>
            </el-space>
          </div>

          <div class="actions">
            <el-button
              type="success"
              :disabled="recording"
              @click="markLearned"
            >
              {{ learned ? '已标记完成' : '标记已学' }}
            </el-button>
            <span v-if="learnedAt" class="learned-time">
              完成时间：{{ formatDateTime(learnedAt) }}
            </span>
          </div>
        </template>
        <el-empty v-else description="学习资料不存在或无权限查看" />
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import { getTrainingContent, getTrainingRecords, markTrainingRecord } from '@/api/training'
import type { TrainingContent, TrainingRecord } from '@/types'
import { formatDateTime } from '@/utils/helpers'

const route = useRoute()
const router = useRouter()

const loading = ref(false)
const recording = ref(false)
const content = ref<TrainingContent | null>(null)
const records = ref<TrainingRecord[]>([])

const contentId = computed(() => Number(route.params.id))
const materialLabel = computed(() => {
  if (content.value?.content_type === 'video') return '视频文件'
  if (content.value?.content_type === 'document') return '文档文件'
  return '资料链接'
})
const actionLabel = computed(() => {
  if (content.value?.content_type === 'video') return '打开视频'
  if (content.value?.content_type === 'document') return '打开文档'
  return '打开资料'
})
const emptyMaterialText = computed(() => {
  if (content.value?.content_type === 'video') return '未上传视频文件'
  if (content.value?.content_type === 'document') return '未上传文档文件'
  return '未配置资料链接'
})

const learnedRecord = computed(() => {
  if (!content.value) return null
  return records.value.find((item) => item.content_id === content.value?.id) || null
})
const learned = computed(() => !!learnedRecord.value)
const learnedAt = computed(() => learnedRecord.value?.completed_at || '')

const normalizeObject = <T>(response: any): T | null => {
  if (!response) return null
  if (response.data && typeof response.data === 'object') return response.data as T
  if (typeof response === 'object') return response as T
  return null
}

const normalizeArray = <T>(response: any): T[] => {
  if (Array.isArray(response)) return response as T[]
  if (Array.isArray(response?.data)) return response.data as T[]
  return []
}

const goBack = () => {
  router.push('/training')
}

const openMaterial = () => {
  if (!content.value?.file_url) {
    ElMessage.info('当前资料未配置链接')
    return
  }
  window.open(content.value.file_url, '_blank')
}

const loadRecords = async () => {
  try {
    const response = await getTrainingRecords()
    records.value = normalizeArray<TrainingRecord>(response)
  } catch (error) {
    console.error(error)
  }
}

const loadContent = async () => {
  if (!Number.isFinite(contentId.value) || contentId.value <= 0) {
    content.value = null
    return
  }
  try {
    const response = await getTrainingContent(contentId.value)
    content.value = normalizeObject<TrainingContent>(response)
  } catch (error: any) {
    content.value = null
    if (error?.response?.status === 404) {
      ElMessage.warning('资料不存在或无权限查看')
    } else {
      ElMessage.error('加载资料失败')
    }
  }
}

const loadPage = async () => {
  loading.value = true
  try {
    await Promise.all([loadContent(), loadRecords()])
  } finally {
    loading.value = false
  }
}

const markLearned = async () => {
  if (!content.value) return
  recording.value = true
  try {
    await markTrainingRecord({ content_id: content.value.id })
    ElMessage.success('已记录学习')
    await loadRecords()
  } catch (error) {
    console.error(error)
    ElMessage.error('记录失败')
  } finally {
    recording.value = false
  }
}

onMounted(() => {
  loadPage()
})

watch(
  () => route.params.id,
  () => {
    loadPage()
  }
)
</script>

<style scoped>
.page-container {
  padding: 20px;
}

.header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.title-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.title {
  margin: 0;
  font-size: 24px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.meta {
  margin-top: 10px;
  display: flex;
  gap: 16px;
  font-size: 13px;
  color: var(--el-text-color-secondary);
}

.section {
  margin-top: 20px;
}

.section-title {
  margin-bottom: 8px;
  font-size: 14px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.section-content {
  line-height: 1.8;
  white-space: pre-wrap;
  word-break: break-word;
}

.actions {
  margin-top: 24px;
  display: flex;
  align-items: center;
  gap: 12px;
}

.learned-time {
  font-size: 13px;
  color: var(--el-text-color-secondary);
}

.muted {
  color: var(--el-text-color-secondary);
  font-size: 13px;
}
</style>
