<template>
  <div class="page-container">
    <el-card shadow="never">
      <template #header>
        <div class="header-row">
          <el-button text @click="goBack">返回列表</el-button>
          <el-space>
            <el-button
              v-if="authStore.isStaff() && announcement"
              type="primary"
              :icon="Edit"
              @click="goEdit"
            >
              编辑
            </el-button>
            <el-button :icon="Refresh" @click="loadAnnouncement">刷新</el-button>
          </el-space>
        </div>
      </template>

      <div v-loading="loading">
        <template v-if="announcement">
          <h2 class="title">{{ announcement.title }}</h2>
          <div class="meta-row">
            <el-tag :type="announcement.published ? 'success' : 'info'" size="small">
              {{ announcement.published ? '已发布' : '草稿' }}
            </el-tag>
            <span class="time">发布时间：{{ formatDateTime(announcement.created_at) }}</span>
          </div>
          <div class="content" v-html="announcement.content"></div>
        </template>
        <el-empty v-else description="公告不存在或无权限查看" />
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Refresh, Edit } from '@element-plus/icons-vue'
import { getAnnouncement } from '@/api/announcements'
import { useAuthStore } from '@/stores/auth'
import type { Announcement } from '@/types'
import { formatDateTime } from '@/utils/helpers'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const loading = ref(false)
const announcement = ref<Announcement | null>(null)

const announcementId = () => Number(route.params.id)

const goBack = () => {
  router.push('/announcements')
}

const goEdit = () => {
  if (announcement.value) {
    router.push(`/announcements/${announcement.value.id}/edit`)
  }
}

const loadAnnouncement = async () => {
  const id = announcementId()
  if (!Number.isFinite(id) || id <= 0) {
    announcement.value = null
    ElMessage.error('公告ID无效')
    return
  }

  loading.value = true
  try {
    const response = await getAnnouncement(id)
    announcement.value = (response as any)?.data ? (response as any).data : (response as Announcement)
  } catch (error: any) {
    announcement.value = null
    if (error?.response?.status === 404) {
      ElMessage.warning('公告不存在或无权限查看')
    } else {
      ElMessage.error('加载公告失败')
    }
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadAnnouncement()
})

watch(
  () => route.params.id,
  () => {
    loadAnnouncement()
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

.title {
  margin: 0 0 12px;
  font-size: 24px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.meta-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
}

.time {
  font-size: 13px;
  color: var(--el-text-color-secondary);
}

.content {
  font-size: 15px;
  line-height: 1.9;
  color: var(--el-text-color-regular);
  word-break: break-word;
}

.content :deep(img) {
  max-width: 100%;
  height: auto;
  border-radius: 4px;
  margin: 8px 0;
}

.content :deep(p) {
  margin: 0.5em 0;
}

.content :deep(table) {
  border-collapse: collapse;
  width: 100%;
  margin: 8px 0;
}

.content :deep(td),
.content :deep(th) {
  border: 1px solid #dcdfe6;
  padding: 6px 10px;
}
</style>
