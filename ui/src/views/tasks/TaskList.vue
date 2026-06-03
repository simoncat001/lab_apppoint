<template>
  <div class="page-container">
    <!-- 顶部操作栏 -->
    <el-card class="header-card" shadow="never">
      <el-row :gutter="16" align="middle">
        <el-col :span="12">
          <el-space>
            <el-button type="primary" :icon="Plus" @click="handleCreate">
              创建任务
            </el-button>
            <el-button :icon="Refresh" @click="loadTasks">
              刷新
            </el-button>
            <el-button type="danger" :icon="Warning" @click="loadUrgentTasks">
              紧急任务
            </el-button>
          </el-space>
        </el-col>
        <el-col :span="12" style="text-align: right">
          <el-space>
            <el-select
              v-model="filterUrgency"
              placeholder="紧急程度"
              clearable
              style="width: 120px"
              @change="loadTasks"
            >
              <el-option label="高" :value="1" />
              <el-option label="正常" :value="0" />
              <el-option label="低" :value="-1" />
            </el-select>
            <el-select
              v-model="filterResolved"
              placeholder="状态"
              clearable
              style="width: 120px"
              @change="loadTasks"
            >
              <el-option label="未解决" :value="false" />
              <el-option label="已解决" :value="true" />
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
        <el-table-column label="紧急程度" width="100">
          <template #default="{ row }">
            <el-tag :type="getTaskUrgencyType(row.urgency)">
              {{ getTaskUrgencyLabel(row.urgency) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="problem_description" label="问题描述" min-width="200" show-overflow-tooltip />
        <el-table-column label="仪器" width="150">
          <template #default="{ row }">
            {{ row.tool?.name || '-' }}
          </template>
        </el-table-column>
        <el-table-column label="分类" width="120">
          <template #default="{ row }">
            <el-tag v-if="row.problem_category_id">{{ getCategoryName(row.problem_category_id) }}</el-tag>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column label="创建者" width="100">
          <template #default="{ row }">
            {{ row.creator?.username || '-' }}
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag v-if="row.resolved" type="success">已解决</el-tag>
            <el-tag v-else-if="row.cancelled" type="info">已取消</el-tag>
            <el-tag v-else type="warning">待处理</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="creation_time" label="创建时间" width="180">
          <template #default="{ row }">
            {{ formatDateTime(row.creation_time) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="320" fixed="right">
          <template #default="{ row }">
            <el-space>
              <el-button
                v-if="!row.resolved && !row.cancelled"
                type="success"
                size="small"
                :icon="Check"
                @click="handleResolve(row)"
              >
                解决
              </el-button>
              <el-button
                v-if="!row.resolved && !row.cancelled"
                type="warning"
                size="small"
                :icon="Close"
                @click="handleCancel(row)"
              >
                取消
              </el-button>
              <el-button
                type="info"
                size="small"
                :icon="View"
                @click="handleViewHistory(row)"
              >
                历史
              </el-button>
              <el-button
                type="primary"
                size="small"
                :icon="Edit"
                @click="handleEdit(row)"
              >
                编辑
              </el-button>
              <el-button
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
          @size-change="loadTasks"
          @current-change="loadTasks"
        />
      </div>
    </el-card>

    <!-- 创建/编辑对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogTitle"
      width="600px"
      @close="resetForm"
    >
      <el-form
        ref="formRef"
        :model="formData"
        :rules="formRules"
        label-width="100px"
      >
        <el-form-item label="问题描述" prop="problem_description">
          <el-input
            v-model="formData.problem_description"
            type="textarea"
            :rows="4"
            placeholder="请描述问题"
          />
        </el-form-item>
        <el-form-item label="紧急程度" prop="urgency">
          <el-select v-model="formData.urgency" placeholder="请选择紧急程度" style="width: 100%">
            <el-option label="高" :value="1" />
            <el-option label="正常" :value="0" />
            <el-option label="低" :value="-1" />
          </el-select>
        </el-form-item>
        <el-form-item label="仪器" prop="tool_id">
          <el-select v-model="formData.tool_id" placeholder="请选择仪器" filterable style="width: 100%">
            <el-option v-for="tool in tools" :key="tool.id" :label="tool.name" :value="tool.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="问题分类">
          <el-select v-model="formData.category_id" placeholder="请选择问题分类（可选）" clearable style="width: 100%">
            <el-option v-for="category in categories" :key="category.id" :label="category.name" :value="category.id" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">
          确定
        </el-button>
      </template>
    </el-dialog>

    <!-- 解决任务对话框 -->
    <el-dialog v-model="resolveDialogVisible" title="解决任务" width="500px">
      <el-form :model="resolveForm" label-width="100px">
        <el-form-item label="解决说明" required>
          <el-input
            v-model="resolveForm.resolution_description"
            type="textarea"
            :rows="4"
            placeholder="请输入解决说明"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="resolveDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submitResolve">
          确定
        </el-button>
      </template>
    </el-dialog>

    <!-- 取消任务对话框 -->
    <el-dialog v-model="cancelDialogVisible" title="取消任务" width="500px">
      <el-form :model="cancelForm" label-width="100px">
        <el-form-item label="取消原因">
          <el-input
            v-model="cancelForm.resolution_description"
            type="textarea"
            :rows="4"
            placeholder="请输入取消原因（可选）"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="cancelDialogVisible = false">取消</el-button>
        <el-button type="warning" :loading="submitting" @click="submitCancel">
          确定
        </el-button>
      </template>
    </el-dialog>

    <!-- 历史记录对话框 -->
    <el-dialog v-model="historyDialogVisible" title="任务历史" width="800px">
      <el-timeline>
        <el-timeline-item
          v-for="item in historyData"
          :key="item.id"
          :timestamp="formatDateTime(item.time)"
          placement="top"
        >
          <el-card>
            <p><strong>操作:</strong> {{ item.status }}</p>
            <p v-if="item.description"><strong>说明:</strong> {{ item.description }}</p>
          </el-card>
        </el-timeline-item>
      </el-timeline>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import {
  Plus,
  Refresh,
  Edit,
  Delete,
  Check,
  Close,
  Warning,
  View
} from '@element-plus/icons-vue'
import {
  getTasks,
  createTask,
  updateTask,
  deleteTask,
  resolveTask,
  cancelTask,
  getTaskHistory,
  getUrgentTasks,
  getTaskCategories
} from '@/api/tasks'
import { getTools } from '@/api/tools'
import type { Task, TaskCategory, Tool } from '@/types'
import { formatDateTime, getTaskUrgencyLabel, getTaskUrgencyType } from '@/utils/helpers'

// 数据列表
const loading = ref(false)
const tableData = ref<Task[]>([])

// 过滤器
const filterUrgency = ref<number>()
const filterResolved = ref<boolean>()
const tools = ref<Tool[]>([])
const categories = ref<TaskCategory[]>([])

// 分页
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)

// 对话框
const dialogVisible = ref(false)
const dialogMode = ref<'create' | 'edit'>('create')
const dialogTitle = computed(() => (dialogMode.value === 'create' ? '创建任务' : '编辑任务'))
const submitting = ref(false)

// 解决对话框
const resolveDialogVisible = ref(false)
const resolveForm = reactive({
  taskId: 0,
  resolution_description: ''
})

// 取消对话框
const cancelDialogVisible = ref(false)
const cancelForm = reactive({
  taskId: 0,
  resolution_description: ''
})

// 历史对话框
const historyDialogVisible = ref(false)
const historyData = ref<any[]>([])

// 表单
const formRef = ref<FormInstance>()
const formData = reactive<Partial<Task>>({
  problem_description: '',
  urgency: 0,
  tool_id: undefined,
  category_id: undefined
})

const formRules: FormRules = {
  problem_description: [{ required: true, message: '请输入问题描述', trigger: 'blur' }],
  urgency: [{ required: true, message: '请选择紧急程度', trigger: 'change' }],
  tool_id: [{ required: true, message: '请选择仪器', trigger: 'change' }]
}

const loadTools = async () => {
  try {
    const response = await getTools({ skip: 0, limit: 1000 })
    tools.value = Array.isArray(response) ? response : []
  } catch (error) {
    console.error('加载仪器列表失败:', error)
  }
}

const loadCategories = async () => {
  try {
    const response = await getTaskCategories()
    categories.value = Array.isArray(response) ? response : (response as any)?.data || []
  } catch (error) {
    console.error('加载任务分类失败:', error)
  }
}

const getCategoryName = (categoryId?: number) => {
  return categories.value.find((item) => item.id === categoryId)?.name || `#${categoryId}`
}

// 加载任务列表
const loadTasks = async () => {
  loading.value = true
  try {
    const params = {
      skip: (currentPage.value - 1) * pageSize.value,
      limit: pageSize.value,
      ...(filterUrgency.value && { urgency: filterUrgency.value }),
      ...(filterResolved.value !== undefined && { resolved: filterResolved.value })
    }
    const response = await getTasks(params)
    tableData.value = Array.isArray(response) ? response : (response as any).data || []
    const serverTotal = (response as any)?._total
    total.value = typeof serverTotal === 'number' ? serverTotal : tableData.value.length
  } catch (error) {
    ElMessage.error('加载任务列表失败')
    console.error(error)
  } finally {
    loading.value = false
  }
}

// 加载紧急任务
const loadUrgentTasks = async () => {
  loading.value = true
  try {
    const response = await getUrgentTasks()
    tableData.value = Array.isArray(response) ? response : (response as any).data || []
    total.value = tableData.value.length
    ElMessage.success(`找到 ${total.value} 个紧急任务`)
  } catch (error) {
    ElMessage.error('加载紧急任务失败')
    console.error(error)
  } finally {
    loading.value = false
  }
}

// 打开创建对话框
const handleCreate = () => {
  dialogMode.value = 'create'
  resetForm()
  dialogVisible.value = true
}

// 打开编辑对话框
const handleEdit = (row: Task) => {
  dialogMode.value = 'edit'
  Object.assign(formData, {
    id: row.id,
    problem_description: row.problem_description,
    urgency: row.urgency,
    tool_id: row.tool_id,
    category_id: row.problem_category_id ?? row.category_id
  })
  dialogVisible.value = true
}

// 解决任务
const handleResolve = (row: Task) => {
  resolveForm.taskId = row.id
  resolveForm.resolution_description = ''
  resolveDialogVisible.value = true
}

const submitResolve = async () => {
  if (!resolveForm.resolution_description.trim()) {
    ElMessage.warning('请输入解决说明')
    return
  }

  submitting.value = true
  try {
    await resolveTask(resolveForm.taskId, {
      resolution_description: resolveForm.resolution_description
    })
    ElMessage.success('任务已解决')
    resolveDialogVisible.value = false
    await loadTasks()
  } catch (error) {
    ElMessage.error('解决任务失败')
    console.error(error)
  } finally {
    submitting.value = false
  }
}

// 取消任务
const handleCancel = (row: Task) => {
  cancelForm.taskId = row.id
  cancelForm.resolution_description = ''
  cancelDialogVisible.value = true
}

const submitCancel = async () => {
  submitting.value = true
  try {
    await cancelTask(cancelForm.taskId, {
      resolution_description: cancelForm.resolution_description || undefined
    })
    ElMessage.success('任务已取消')
    cancelDialogVisible.value = false
    await loadTasks()
  } catch (error) {
    ElMessage.error('取消任务失败')
    console.error(error)
  } finally {
    submitting.value = false
  }
}

// 查看历史
const handleViewHistory = async (row: Task) => {
  try {
    const response = await getTaskHistory(row.id)
    historyData.value = Array.isArray(response) ? response : (response as any).data || []
    historyDialogVisible.value = true
  } catch (error) {
    ElMessage.error('加载历史记录失败')
    console.error(error)
  }
}

// 删除任务
const handleDelete = async (row: Task) => {
  try {
    await ElMessageBox.confirm('确定要删除该任务吗？此操作不可恢复！', '警告', {
      type: 'error',
      confirmButtonText: '确定删除'
    })
    await deleteTask(row.id)
    ElMessage.success('删除成功')
    await loadTasks()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
      console.error(error)
    }
  }
}

// 提交表单
const handleSubmit = async () => {
  if (!formRef.value) return

  await formRef.value.validate(async (valid) => {
    if (!valid) return

    submitting.value = true
    try {
      if (dialogMode.value === 'create') {
        await createTask(formData)
        ElMessage.success('创建成功')
      } else {
        await updateTask(formData.id!, formData)
        ElMessage.success('更新成功')
      }
      dialogVisible.value = false
      await loadTasks()
    } catch (error) {
      ElMessage.error(dialogMode.value === 'create' ? '创建失败' : '更新失败')
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
    problem_description: '',
    urgency: 0,
    tool_id: undefined,
    category_id: undefined
  })
}

// 初始化
onMounted(async () => {
  await Promise.all([loadTools(), loadCategories()])
  await loadTasks()
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
</style>
