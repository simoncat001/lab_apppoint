<template>
  <div class="feed-page">
    <!-- 头部条 -->
    <div class="feed-header">
      <div class="feed-header-inner">
        <div class="feed-title">
          <el-icon class="feed-title-icon"><Bell /></el-icon>
          <h1>公告</h1>
          <span class="feed-count" v-if="total">{{ total }} 条</span>
        </div>
        <div class="feed-actions">
          <el-button v-if="authStore.isStaff()" type="primary" :icon="Plus" round @click="handleCreate">
            发布公告
          </el-button>
          <el-button :icon="Refresh" circle @click="loadAnnouncements" />
        </div>
      </div>
    </div>

    <!-- 信息流 -->
    <div class="feed-body" v-loading="loading">
      <template v-if="cards.length">
        <article
          v-for="card in cards"
          :key="card.id"
          class="feed-card"
          :class="[
            card.published ? 'feed-card-published' : 'feed-card-draft',
            showStatusTag ? 'feed-card-with-status' : 'feed-card-no-status',
          ]"
          @click="handleView(card)"
        >
          <!-- 草稿：右上角斜向"草稿"水印；已发布：无水印 -->
          <div v-if="!card.published" class="card-watermark">DRAFT</div>

          <!-- 卡片头部：作者 + 时间 + 状态 -->
          <header class="card-head">
            <el-avatar class="card-avatar" :size="40">
              {{ avatarLabel(card) }}
            </el-avatar>
            <div class="card-meta">
              <div class="card-meta-line">
                <span class="card-author">{{ card.author_display_name || card.author_username || '系统' }}</span>
                <!-- 状态标签：仅管理员 / 内部员工可见 -->
                <template v-if="showStatusTag">
                  <el-tag
                    v-if="card.published"
                    type="success"
                    effect="dark"
                    round
                    class="card-status card-status-published"
                  >
                    ✓ 已发布
                  </el-tag>
                  <el-tag
                    v-else
                    type="warning"
                    effect="dark"
                    round
                    class="card-status card-status-draft"
                  >
                    ✎ 草稿（仅管理员可见）
                  </el-tag>
                </template>
              </div>
              <div class="card-time">{{ formatRelative(card.created_at) }} · {{ formatDateTime(card.created_at) }}</div>
            </div>
            <div v-if="authStore.isStaff()" class="card-quick-actions" @click.stop>
              <el-dropdown trigger="click" placement="bottom-end">
                <el-button text :icon="MoreFilled" />
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item :icon="Edit" @click="handleEdit(card)">编辑</el-dropdown-item>
                    <el-dropdown-item :icon="Delete" @click="handleDelete(card)" divided>
                      <span style="color: var(--el-color-danger)">删除</span>
                    </el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </div>
          </header>

          <!-- 卡片正文 -->
          <h2 class="card-title">{{ card.title }}</h2>
          <p v-if="card.preview" class="card-preview">{{ card.preview }}</p>

          <!-- 缩略图（最多 4 张，9 宫格风格） -->
          <div v-if="card.images.length" class="card-images" :data-count="Math.min(card.images.length, 4)">
            <div
              v-for="(src, idx) in card.images.slice(0, 4)"
              :key="idx"
              class="card-image"
              :style="{ backgroundImage: `url(${src})` }"
            >
              <span v-if="idx === 3 && card.images.length > 4" class="card-image-more">
                +{{ card.images.length - 4 }}
              </span>
            </div>
          </div>

          <!-- 卡片底部：阅读全文 -->
          <footer class="card-foot">
            <el-button text type="primary" class="card-read-more">
              查看详情
              <el-icon style="margin-left: 4px"><ArrowRight /></el-icon>
            </el-button>
          </footer>
        </article>
      </template>

      <el-empty v-else description="暂无公告" :image-size="120" class="feed-empty" />
    </div>

    <!-- 翻页 -->
    <div class="feed-pagination" v-if="total > pageSize">
      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :total="total"
        :page-sizes="[10, 20, 50]"
        layout="total, sizes, prev, pager, next, jumper"
        @size-change="loadAnnouncements"
        @current-change="loadAnnouncements"
        background
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowRight, Bell, Delete, Edit, MoreFilled, Plus, Refresh } from '@element-plus/icons-vue'
import { getAnnouncements, createAnnouncement, deleteAnnouncement } from '@/api/announcements'
import { useAuthStore } from '@/stores/auth'
import type { Announcement } from '@/types'
import { formatDateTime } from '@/utils/helpers'
import { useRouter } from 'vue-router'

const authStore = useAuthStore()
const router = useRouter()

const loading = ref(false)
const tableData = ref<Announcement[]>([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(10)

// 状态标签（已发布 / 草稿）仅管理员或内部员工可见，外部用户不展示
const showStatusTag = computed(() => authStore.isStaff() || authStore.isInternalUser())

interface Card extends Announcement {
  preview: string
  images: string[]
}

const cards = computed<Card[]>(() =>
  tableData.value.map((a) => ({
    ...a,
    preview: extractPreview(a.content, 160),
    images: extractImages(a.content),
  }))
)

const loadAnnouncements = async () => {
  loading.value = true
  try {
    const response = await getAnnouncements({
      include_unpublished: authStore.isStaff(),
      skip: (currentPage.value - 1) * pageSize.value,
      limit: pageSize.value,
    })
    const data = Array.isArray(response) ? response : ((response as any)?.data ?? [])
    tableData.value = data
    const serverTotal = (response as any)?._total
    total.value = typeof serverTotal === 'number' ? serverTotal : data.length
  } catch (error) {
    console.error(error)
    ElMessage.error('加载公告失败')
  } finally {
    loading.value = false
  }
}

const handleCreate = async () => {
  try {
    const response: any = await createAnnouncement({
      title: '未命名公告',
      content: '',
      published: false,
    })
    const draft = response?.data ? response.data : response
    if (!draft?.id) throw new Error('创建草稿失败')
    router.push(`/announcements/${draft.id}/edit?draft=1`)
  } catch (error) {
    console.error(error)
    ElMessage.error('创建草稿失败')
  }
}

const handleView = (row: Announcement) => {
  router.push(`/announcements/${row.id}`)
}

const handleEdit = (row: Announcement) => {
  router.push(`/announcements/${row.id}/edit`)
}

const handleDelete = async (row: Announcement) => {
  try {
    await ElMessageBox.confirm(`确定删除公告 "${row.title}" 吗？`, '提示', {
      type: 'warning',
      confirmButtonText: '确定',
      cancelButtonText: '取消',
    })
    await deleteAnnouncement(row.id)
    ElMessage.success('删除成功')
    loadAnnouncements()
  } catch (error) {
    if (error !== 'cancel') {
      console.error(error)
      ElMessage.error('删除失败')
    }
  }
}

// ============ 富文本工具 ============

function extractPreview(content?: string, max = 160): string {
  if (!content) return ''
  const text = String(content)
    .replace(/<style[^>]*>[\s\S]*?<\/style>/gi, '')
    .replace(/<script[^>]*>[\s\S]*?<\/script>/gi, '')
    .replace(/<img[^>]*>/gi, ' ')
    .replace(/<[^>]+>/g, ' ')
    .replace(/&nbsp;/g, ' ')
    .replace(/&amp;/g, '&')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .replace(/\s+/g, ' ')
    .trim()
  if (text.length <= max) return text
  return `${text.slice(0, max)}…`
}

function extractImages(content?: string): string[] {
  if (!content) return []
  const out: string[] = []
  const re = /<img[^>]*\bsrc=["']([^"']+)["']/gi
  let m: RegExpExecArray | null
  while ((m = re.exec(content)) && out.length < 9) {
    if (m[1]) out.push(m[1])
  }
  return out
}

function avatarLabel(card: Card) {
  const name = card.author_display_name || card.author_username || '系'
  return name.slice(0, 1).toUpperCase()
}

function formatRelative(iso?: string) {
  if (!iso) return ''
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return ''
  const sec = Math.floor((Date.now() - d.getTime()) / 1000)
  if (sec < 60) return '刚刚'
  if (sec < 3600) return `${Math.floor(sec / 60)} 分钟前`
  if (sec < 86400) return `${Math.floor(sec / 3600)} 小时前`
  if (sec < 7 * 86400) return `${Math.floor(sec / 86400)} 天前`
  return formatDateTime(iso).replace(/:\d{2}$/, '')
}

onMounted(loadAnnouncements)
</script>

<style scoped>
.feed-page {
  max-width: 760px;
  margin: 0 auto;
  padding: 24px 16px 48px;
}

/* ===== Header ===== */
.feed-header {
  position: sticky;
  top: 0;
  z-index: 10;
  background: var(--el-bg-color-page);
  margin-bottom: 16px;
  padding: 8px 0;
}

.feed-header-inner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: var(--el-bg-color);
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 12px;
  padding: 12px 20px;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.03);
}

.feed-title {
  display: flex;
  align-items: center;
  gap: 10px;
}

.feed-title h1 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.feed-title-icon {
  font-size: 22px;
  color: var(--el-color-primary);
}

.feed-count {
  font-size: 13px;
  color: var(--el-text-color-secondary);
  padding: 2px 10px;
  background: var(--el-fill-color-light);
  border-radius: 12px;
}

.feed-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

/* ===== Body ===== */
.feed-body {
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-height: 200px;
}

.feed-empty {
  background: var(--el-bg-color);
  border-radius: 12px;
  padding: 40px 0;
  border: 1px dashed var(--el-border-color);
}

/* ===== Card ===== */
.feed-card {
  position: relative;
  background: var(--el-bg-color);
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 12px;
  padding: 16px 20px 12px;
  cursor: pointer;
  transition: box-shadow 0.18s ease, transform 0.18s ease, border-color 0.18s ease;
  overflow: hidden;
}

.feed-card:hover {
  box-shadow: 0 6px 18px rgba(0, 0, 0, 0.06);
  border-color: var(--el-border-color);
  transform: translateY(-1px);
}

/* 已发布：左侧细绿色色条（仅状态可见角色：管理员/内部员工） */
.feed-card-published.feed-card-with-status::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 3px;
  background: var(--el-color-success);
  opacity: 0.55;
}

/* 草稿：左侧粗黄色色条 + 暖色斜纹背景 + 整张稍微去饱和 */
.feed-card-draft {
  background:
    repeating-linear-gradient(
      45deg,
      rgba(230, 162, 60, 0.04) 0,
      rgba(230, 162, 60, 0.04) 12px,
      transparent 12px,
      transparent 24px
    ),
    var(--el-bg-color);
  border-color: rgba(230, 162, 60, 0.5);
}

.feed-card-draft::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 5px;
  background: var(--el-color-warning);
}

.feed-card-draft .card-title,
.feed-card-draft .card-preview,
.feed-card-draft .card-images {
  filter: saturate(0.7);
}

/* 草稿水印：右上角"DRAFT"斜向贴标 */
.card-watermark {
  position: absolute;
  top: 14px;
  right: -38px;
  background: var(--el-color-warning);
  color: #fff;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 2px;
  padding: 3px 44px;
  transform: rotate(38deg);
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.15);
  pointer-events: none;
}

.card-head {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
}

.card-avatar {
  background: linear-gradient(135deg, #46a0ff, #7c4dff);
  color: #fff;
  font-weight: 600;
  flex: 0 0 auto;
}

.card-meta {
  flex: 1;
  min-width: 0;
}

.card-meta-line {
  display: flex;
  align-items: center;
  gap: 8px;
}

.card-author {
  font-weight: 600;
  color: var(--el-text-color-primary);
  font-size: 14px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.card-status {
  flex: 0 0 auto;
  font-weight: 600;
  letter-spacing: 0.5px;
  padding: 4px 12px;
  height: auto;
  line-height: 1.4;
}

.card-status-published {
  /* el-tag dark + success 已经够醒目，加一点轻投影 */
  box-shadow: 0 1px 3px rgba(103, 194, 58, 0.35);
}

.card-status-draft {
  /* 草稿：脉动呼吸感 + 警告色阴影 */
  box-shadow: 0 1px 3px rgba(230, 162, 60, 0.5);
  animation: card-status-pulse 2.4s ease-in-out infinite;
}

@keyframes card-status-pulse {
  0%, 100% {
    box-shadow: 0 1px 3px rgba(230, 162, 60, 0.5);
  }
  50% {
    box-shadow: 0 0 0 4px rgba(230, 162, 60, 0.18), 0 1px 3px rgba(230, 162, 60, 0.6);
  }
}

.card-time {
  margin-top: 2px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.card-quick-actions {
  flex: 0 0 auto;
}

.card-title {
  margin: 6px 0 6px;
  font-size: 17px;
  font-weight: 600;
  color: var(--el-text-color-primary);
  line-height: 1.4;
}

.card-preview {
  margin: 0 0 10px;
  color: var(--el-text-color-regular);
  font-size: 14px;
  line-height: 1.6;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
  word-break: break-word;
}

/* 9 宫格图（1-4 张自适应） */
.card-images {
  display: grid;
  gap: 4px;
  margin: 8px 0 10px;
  border-radius: 8px;
  overflow: hidden;
}

.card-images[data-count="1"] {
  grid-template-columns: 1fr;
  max-height: 360px;
}

.card-images[data-count="1"] .card-image {
  aspect-ratio: 16 / 9;
}

.card-images[data-count="2"] {
  grid-template-columns: 1fr 1fr;
}

.card-images[data-count="3"] {
  grid-template-columns: 1fr 1fr 1fr;
}

.card-images[data-count="4"] {
  grid-template-columns: 1fr 1fr;
}

.card-image {
  position: relative;
  aspect-ratio: 1 / 1;
  background-size: cover;
  background-position: center;
  background-color: var(--el-fill-color-lighter);
  border-radius: 4px;
}

.card-image-more {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.45);
  color: #fff;
  font-size: 18px;
  font-weight: 600;
  border-radius: 4px;
}

.card-foot {
  display: flex;
  justify-content: flex-end;
  border-top: 1px solid var(--el-border-color-lighter);
  margin-top: 8px;
  padding-top: 6px;
}

.card-read-more {
  font-size: 13px;
}

/* ===== Pagination ===== */
.feed-pagination {
  display: flex;
  justify-content: center;
  margin-top: 24px;
}

@media (max-width: 600px) {
  .feed-page {
    padding: 12px 8px 32px;
  }
  .feed-card {
    padding: 14px 16px 10px;
  }
  .card-title {
    font-size: 16px;
  }
}
</style>
