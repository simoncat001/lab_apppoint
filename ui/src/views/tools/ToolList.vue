<template>
  <div class="page-container">
    <!-- 顶部操作栏 -->
    <el-card class="header-card" shadow="never">
      <el-row :gutter="16" align="middle">
        <el-col :span="12">
          <el-space>
            <el-button v-if="canManageTools" type="primary" :icon="Plus" @click="handleCreate">
              创建仪器
            </el-button>
            <el-button :icon="Refresh" @click="loadTools">
              刷新
            </el-button>
            <el-button v-if="canManageTools" @click="openCategoryDialog">管理分类</el-button>
            <el-button v-if="canManageTools" @click="openTagDialog">管理标签</el-button>
          </el-space>
        </el-col>
        <el-col :span="12" style="text-align: right">
          <el-space>
            <el-select
              v-model="filterCategoryId"
              placeholder="分类"
              clearable
              style="width: 160px"
              @change="loadTools"
            >
              <el-option v-for="c in categories" :key="c.id" :label="c.name" :value="c.id" />
            </el-select>
            <el-select
              v-model="filterTagIds"
              multiple
              collapse-tags
              collapse-tags-tooltip
              clearable
              placeholder="标签"
              style="width: 220px"
              @change="loadTools"
            >
              <el-option v-for="t in tags" :key="t.id" :label="t.name" :value="t.id" />
            </el-select>
            <el-input
              v-model="filterName"
              placeholder="搜索仪器名称"
              clearable
              style="width: 200px"
              @change="loadTools"
            >
              <template #prefix>
                <el-icon><Search /></el-icon>
              </template>
            </el-input>
            <el-select
              v-if="canManageTools"
              v-model="filterVisible"
              placeholder="可见性"
              clearable
              style="width: 120px"
              @change="loadTools"
            >
              <el-option label="可见" :value="true" />
              <el-option label="隐藏" :value="false" />
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
        <el-table-column label="图片" width="80">
          <template #default="{ row }">
            <el-image
              v-if="getToolCoverImageUrl(row)"
              :src="getToolCoverImageUrl(row) ?? undefined"
              fit="cover"
              style="width: 50px; height: 50px; border-radius: 4px;"
              :preview-src-list="getToolImagePreviewUrls(row)"
            />
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column prop="name" label="仪器名称" min-width="180">
          <template #default="{ row }">
            <el-link type="primary" @click="handleViewDetail(row)">
              {{ row.name }}
            </el-link>
            <el-tag
              v-if="(row.images?.length || 0) > 1"
              type="info"
              size="small"
              style="margin-left: 6px"
            >
              {{ row.images?.length }} 图
            </el-tag>
            <el-tag v-if="row.restrict_external_access" type="warning" size="small" style="margin-left: 6px">
              <el-icon style="vertical-align: -2px"><Lock /></el-icon> 受限
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="分类" width="120">
          <template #default="{ row }">
            <el-tag v-if="row.category">{{ row.category.name }}</el-tag>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column label="所属项目" min-width="160">
          <template #default="{ row }">
            {{ row.project?.name || '-' }}
          </template>
        </el-table-column>
        <el-table-column label="标签" min-width="200">
          <template #default="{ row }">
            <el-space wrap>
              <el-tag v-for="tag in row.tags || []" :key="tag.id" size="small">
                {{ tag.name }}
              </el-tag>
              <span v-if="!row.tags || row.tags.length === 0">-</span>
            </el-space>
          </template>
        </el-table-column>
        <el-table-column label="位置" width="150">
          <template #default="{ row }">
            {{ row.location || '-' }}
          </template>
        </el-table-column>
        <el-table-column label="运行状态" width="120">
          <template #default="{ row }">
            <el-tag v-if="row.operational" type="success">
              <el-icon><CircleCheck /></el-icon> 正常
            </el-tag>
            <el-tag v-else type="danger">
              <el-icon><CircleClose /></el-icon> 故障
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column v-if="canManageTools" label="可见性" width="100">
          <template #default="{ row }">
            <el-tag :type="row.visible ? 'success' : 'info'">
              {{ row.visible ? '可见' : '隐藏' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="需要预约" width="100">
          <template #default="{ row }">
            <el-tag :type="row.requires_reservation ? 'warning' : 'info'">
              {{ row.requires_reservation ? '需要' : '不需要' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="180">
          <template #default="{ row }">
            {{ row.created_at ? formatDateTime(row.created_at) : '-' }}
          </template>
        </el-table-column>
        <el-table-column :label="canManageTools ? '操作' : '查看'" :width="canManageTools ? 240 : 110" fixed="right">
          <template #default="{ row }">
            <el-space>
              <el-button
                type="info"
                size="small"
                :icon="View"
                @click="handleViewDetail(row)"
              >
                详情
              </el-button>
              <el-button
                v-if="canManageTools"
                type="warning"
                size="small"
                :icon="Money"
                @click="loadRates(row.id)"
              >
                费率
              </el-button>
              <el-button
                v-if="canManageTools"
                type="primary"
                size="small"
                :icon="Edit"
                @click="handleEdit(row)"
              >
                编辑
              </el-button>
              <el-button
                v-if="canManageTools"
                type="danger"
                size="small"
                :icon="Delete"
                @click="handleDelete(row)"
              >
                删除
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
          @size-change="loadTools"
          @current-change="loadTools"
        />
      </div>
    </el-card>

    <!-- 费率管理对话框 -->
    <el-dialog
      v-model="rateDialogVisible"
      title="分时费率配置"
      width="600px"
    >
      <el-card shadow="never" style="margin-bottom: 20px">
        <template #header>添加时段</template>
        <el-form :inline="true" :model="rateForm">
          <el-form-item label="开始">
            <el-time-picker v-model="rateForm.start_time" value-format="HH:mm:ss" placeholder="Start" style="width: 120px"/>
          </el-form-item>
          <el-form-item label="结束">
            <el-time-picker v-model="rateForm.end_time" value-format="HH:mm:ss" placeholder="End" style="width: 120px"/>
          </el-form-item>
          <el-form-item label="价格">
            <el-input-number v-model="rateForm.price" :min="0" style="width: 100px"/>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="handleAddRate">添加</el-button>
          </el-form-item>
        </el-form>
      </el-card>

      <el-table :data="rateList" border stripe>
        <el-table-column prop="start_time" label="开始时间" />
        <el-table-column prop="end_time" label="结束时间" />
        <el-table-column prop="price" label="费率" />
        <el-table-column label="操作" width="100">
            <template #default="{ row }">
                <el-button type="danger" icon="Delete" circle size="small" @click="handleDeleteRate(row.id)"/>
            </template>
        </el-table-column>
      </el-table>
    </el-dialog>

    <!-- 分类管理对话框 -->
    <el-dialog v-model="categoryDialogVisible" title="仪器分类" width="560px" align-center>
      <div class="category-dialog-panel">
        <div class="category-dialog-panel__intro">
          统一维护仪器分类。新增后可直接用于仪器筛选和仪器详情配置。
        </div>

        <div class="category-create-box">
          <div class="category-create-box__meta">
            <div class="category-create-box__title">新增分类</div>
            <div class="category-create-box__hint">分类名称建议简短明确，便于筛选和统计。</div>
          </div>
          <div class="category-create-box__form">
            <el-input
              v-model="newCategoryName"
              placeholder="输入新的分类名称"
              size="large"
              clearable
              @keyup.enter="addCategory"
            />
            <el-button type="primary" size="large" :disabled="!newCategoryName.trim()" @click="addCategory">
              新增分类
            </el-button>
          </div>
        </div>

        <div class="category-list-header">
          <div class="category-list-header__title">现有分类</div>
          <el-tag effect="plain" type="info">{{ categories.length }} 个</el-tag>
        </div>

        <div v-if="categories.length" class="category-list">
          <div v-for="row in categories" :key="row.id" class="category-list-item">
            <div class="category-list-item__name">{{ row.name }}</div>
            <div class="category-list-item__actions">
              <el-button size="small" @click="editCategory(row)">编辑</el-button>
              <el-button size="small" type="danger" plain @click="deleteCategory(row)">删除</el-button>
            </div>
          </div>
        </div>
        <el-empty v-else description="暂无分类，先创建一个分类" />
      </div>
    </el-dialog>

    <!-- 标签管理对话框 -->
    <el-dialog v-model="tagDialogVisible" title="仪器标签" width="560px" align-center>
      <div class="category-dialog-panel">
        <div class="category-dialog-panel__intro">
          统一维护仪器标签。标签可用于列表筛选、详情展示和后续统计维度。
        </div>

        <div class="category-create-box">
          <div class="category-create-box__meta">
            <div class="category-create-box__title">新增标签</div>
            <div class="category-create-box__hint">标签名称建议简短明确，例如“高通量”“精密测试”。</div>
          </div>
          <div class="category-create-box__form">
            <el-input
              v-model="newTagName"
              placeholder="输入新的标签名称"
              size="large"
              clearable
              @keyup.enter="addTag"
            />
            <el-button type="primary" size="large" :disabled="!newTagName.trim()" @click="addTag">
              新增标签
            </el-button>
          </div>
        </div>

        <div class="category-list-header">
          <div class="category-list-header__title">现有标签</div>
          <el-tag effect="plain" type="info">{{ tags.length }} 个</el-tag>
        </div>

        <div v-if="tags.length" class="category-list">
          <div v-for="row in tags" :key="row.id" class="category-list-item">
            <div class="category-list-item__name">{{ row.name }}</div>
            <div class="category-list-item__actions">
              <el-button size="small" @click="editTag(row)">编辑</el-button>
              <el-button size="small" type="danger" plain @click="deleteTag(row)">删除</el-button>
            </div>
          </div>
        </div>
        <el-empty v-else description="暂无标签，先创建一个标签" />
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, reactive, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Plus,
  Refresh,
  Edit,
  Delete,
  View,
  Search,
  CircleCheck,
  CircleClose,
  Money,
  Lock,
} from '@element-plus/icons-vue'
import {
  getTools,
  deleteTool,
  getToolRates,
  createToolRate,
  deleteToolRate,
  getToolCategories,
  createToolCategory,
  updateToolCategory,
  deleteToolCategory,
  getToolTags,
  createToolTag,
  updateToolTag,
  deleteToolTag,
  type ToolRate,
  getToolCoverImageUrl,
  getToolImagePreviewUrls,
} from '@/api/tools'
import type { Tool, ToolCategory, ToolTag } from '@/types'
import { formatDateTime } from '@/utils/helpers'
import { useAuthStore } from '@/stores/auth'
import { useProjectContextStore } from '@/stores/project-context'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()
const projectContextStore = useProjectContextStore()
const canManageTools = computed(() => authStore.isStaff())

// 费率管理
const rateDialogVisible = ref(false)
const currentRateToolId = ref<number>(0)
const rateList = ref<ToolRate[]>([])
const rateForm = reactive({
    start_time: '',
    end_time: '',
    price: 0
})

const loadRates = async (toolId: number) => {
    currentRateToolId.value = toolId
    rateList.value = await getToolRates(toolId)
    rateDialogVisible.value = true
}

const handleAddRate = async () => {
    try {
        await createToolRate(currentRateToolId.value, {
            ...rateForm,
            tool_id: currentRateToolId.value
        })
        ElMessage.success('添加成功')
        rateList.value = await getToolRates(currentRateToolId.value)
        rateForm.start_time = ''
        rateForm.end_time = ''
        rateForm.price = 0
    } catch (e) {
        ElMessage.error('添加失败')
    }
}

const handleDeleteRate = async (rateId: number) => {
    try {
        await deleteToolRate(currentRateToolId.value, rateId)
        ElMessage.success('删除成功')
        rateList.value = await getToolRates(currentRateToolId.value)
    } catch (e) {
        ElMessage.error('删除失败')
    }
}

// 数据列表
const loading = ref(false)
const tableData = ref<Tool[]>([])
const categories = ref<ToolCategory[]>([])
const tags = ref<ToolTag[]>([])

// 过滤器
const filterName = ref('')
const filterVisible = ref<boolean>()
const filterCategoryId = ref<number | undefined>()
const filterTagIds = ref<number[]>([])

// 分页
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)

const ensureCurrentProjectSelected = () => {
  const currentProjectId = projectContextStore.currentProjectId
  if (!currentProjectId) {
    ElMessage.warning('请先在页面顶部选择当前项目')
    return false
  }
  return true
}

// 加载仪器列表
const loadTools = async () => {
  loading.value = true
  try {
    const params: Record<string, any> = {
      skip: (currentPage.value - 1) * pageSize.value,
      limit: pageSize.value,
      name: filterName.value || undefined,
      category_id: filterCategoryId.value || undefined,
      tag_ids: filterTagIds.value.length ? filterTagIds.value.join(',') : undefined,
    }
    if (!canManageTools.value) {
      params.visible = true
    }
    if (filterVisible.value !== undefined) {
      params.visible = filterVisible.value
    }
    const response = await getTools(params)
    const data = Array.isArray(response) ? response : (response as any).data || []
    const serverTotal = (response as any)?._total

    tableData.value = data
    total.value = typeof serverTotal === 'number' ? serverTotal : data.length
  } catch (error) {
    ElMessage.error('加载仪器列表失败')
    console.error(error)
  } finally {
    loading.value = false
  }
}

const loadCategories = async () => {
  try {
    categories.value = await getToolCategories()
  } catch (error) {
    console.error(error)
  }
}

const loadTags = async () => {
  try {
    tags.value = await getToolTags()
  } catch (error) {
    console.error(error)
  }
}

// 打开创建对话框
const handleCreate = () => {
  if (!ensureCurrentProjectSelected()) return
  router.push({ name: 'ToolCreate', query: { redirect: route.fullPath } })
}

// 打开编辑对话框
const handleEdit = (row: Tool) => {
  if (!ensureCurrentProjectSelected()) return
  router.push({
    name: 'ToolEdit',
    params: { id: row.id },
    query: { redirect: route.fullPath },
  })
}

// 查看详情
const handleViewDetail = (row: Tool) => {
  router.push(`/tools/${row.id}`)
}

// 删除仪器
const handleDelete = async (row: Tool) => {
  try {
    await ElMessageBox.confirm('确定要删除该仪器吗？此操作不可恢复！', '警告', {
      type: 'error',
      confirmButtonText: '确定删除'
    })
    await deleteTool(row.id)
    ElMessage.success('删除成功')
    await loadTools()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
      console.error(error)
    }
  }
}

// 分类管理
const categoryDialogVisible = ref(false)
const newCategoryName = ref('')

const openCategoryDialog = () => {
  categoryDialogVisible.value = true
}

const addCategory = async () => {
  if (!newCategoryName.value) return
  try {
    await createToolCategory({ name: newCategoryName.value })
    newCategoryName.value = ''
    loadCategories()
    ElMessage.success('新增分类成功')
  } catch (error) {
    console.error(error)
    ElMessage.error('新增失败')
  }
}

const editCategory = async (row: ToolCategory) => {
  try {
    const res = await ElMessageBox.prompt('修改分类名称', '编辑分类', {
      inputValue: row.name,
      confirmButtonText: '确定',
      cancelButtonText: '取消',
    })
    await updateToolCategory(row.id, { name: res.value })
    loadCategories()
    ElMessage.success('更新成功')
  } catch (error) {
    if (error !== 'cancel') {
      console.error(error)
      ElMessage.error('更新失败')
    }
  }
}

const deleteCategory = async (row: ToolCategory) => {
  try {
    await deleteToolCategory(row.id)
    loadCategories()
    ElMessage.success('删除成功')
  } catch (error) {
    console.error(error)
    ElMessage.error('删除失败')
  }
}

// 标签管理
const tagDialogVisible = ref(false)
const newTagName = ref('')

const openTagDialog = () => {
  tagDialogVisible.value = true
}

const addTag = async () => {
  if (!newTagName.value) return
  try {
    await createToolTag({ name: newTagName.value })
    newTagName.value = ''
    loadTags()
    ElMessage.success('新增标签成功')
  } catch (error) {
    console.error(error)
    ElMessage.error('新增失败')
  }
}

const editTag = async (row: ToolTag) => {
  try {
    const res = await ElMessageBox.prompt('修改标签名称', '编辑标签', {
      inputValue: row.name,
      confirmButtonText: '确定',
      cancelButtonText: '取消',
    })
    await updateToolTag(row.id, { name: res.value })
    loadTags()
    ElMessage.success('更新成功')
  } catch (error) {
    if (error !== 'cancel') {
      console.error(error)
      ElMessage.error('更新失败')
    }
  }
}

const deleteTag = async (row: ToolTag) => {
  try {
    await deleteToolTag(row.id)
    loadTags()
    ElMessage.success('删除成功')
  } catch (error) {
    console.error(error)
    ElMessage.error('删除失败')
  }
}

// 初始化
onMounted(() => {
  projectContextStore.hydrate()
  loadTools()
  loadCategories()
  loadTags()
})
</script>

<style scoped>
.page-container {
  padding: 20px;
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

.current-project-display {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  min-height: 44px;
  padding: 0 14px;
  border-radius: 12px;
  background: #f8fafc;
  border: 1px solid #dbe4ef;
}

.current-project-display__label {
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #64748b;
}

.current-project-display__value {
  font-size: 14px;
  font-weight: 600;
  color: #0f172a;
}

.field-helper {
  margin-top: 8px;
  font-size: 12px;
  line-height: 1.6;
  color: #64748b;
}

.form-section-block {
  margin-top: 4px;
  margin-bottom: 18px;
}

.pricing-grid {
  align-items: end;
}

.field-stack {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.field-stack__label {
  line-height: 1.4;
  font-weight: 600;
  font-size: 14px;
  color: #334155;
}

.field-stack :deep(.el-input-number) {
  width: 100%;
}

.count-based-hint {
  margin-top: 4px;
  padding: 10px 12px;
  border-radius: 12px;
  background: #f0f9eb;
  border: 1px solid #d9f0c7;
  color: #3f6212;
  font-size: 13px;
  line-height: 1.6;
}

.toggle-grid {
  margin-top: 2px;
}

.toggle-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  min-height: 68px;
  padding: 14px 16px;
  border-radius: 16px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
}

.toggle-card__label {
  font-size: 14px;
  font-weight: 600;
  color: #334155;
}

.toggle-card :deep(.el-switch__label) {
  white-space: nowrap;
}

.category-dialog-panel {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.category-dialog-panel__intro {
  font-size: 13px;
  line-height: 1.7;
  color: #64748b;
}

.category-create-box {
  padding: 18px;
  border-radius: 18px;
  background: linear-gradient(180deg, #f8fafc 0%, #eef6ff 100%);
  border: 1px solid rgba(191, 219, 254, 0.8);
}

.category-create-box__meta {
  margin-bottom: 12px;
}

.category-create-box__title {
  font-size: 16px;
  font-weight: 700;
  color: #0f172a;
}

.category-create-box__hint {
  margin-top: 6px;
  font-size: 12px;
  color: #64748b;
}

.category-create-box__form {
  display: flex;
  align-items: center;
  gap: 12px;
}

.category-list-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.category-list-header__title {
  font-size: 15px;
  font-weight: 700;
  color: #0f172a;
}

.category-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.category-list-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  padding: 14px 16px;
  border-radius: 16px;
  background: #ffffff;
  border: 1px solid #e2e8f0;
}

.category-list-item__name {
  font-size: 15px;
  font-weight: 600;
  color: #1e293b;
}

.category-list-item__actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

@media (max-width: 768px) {
  .category-create-box__form,
  .category-list-item {
    align-items: stretch;
    flex-direction: column;
  }

  .category-list-item__actions {
    justify-content: flex-end;
  }

  .toggle-card {
    align-items: stretch;
    flex-direction: column;
  }
}
</style>
