<template>
  <div class="page-container">
    <!-- 顶部操作栏 -->
    <el-card class="header-card" shadow="never">
      <el-row :gutter="16" align="middle">
        <el-col :span="12">
          <el-space>
            <el-button type="primary" :icon="Plus" @click="handleCreate">
              创建配置
            </el-button>
            <el-button :icon="Refresh" @click="loadConfigurations">
              刷新
            </el-button>
            <el-button :icon="Histogram" @click="showStats = !showStats">
              {{ showStats ? '隐藏' : '显示' }}统计
            </el-button>
            <el-button type="info" :icon="Clock" @click="showHistory">
              查看历史
            </el-button>
          </el-space>
        </el-col>
        <el-col :span="12" style="text-align: right">
          <el-space>
            <el-input
              v-model="filterName"
              placeholder="搜索配置名称"
              clearable
              style="width: 200px"
              @change="loadConfigurations"
            >
              <template #prefix>
                <el-icon><Search /></el-icon>
              </template>
            </el-input>
            <el-select
              v-model="filterEnabled"
              placeholder="状态"
              clearable
              style="width: 120px"
              @change="loadConfigurations"
            >
              <el-option label="已启用" :value="true" />
              <el-option label="已禁用" :value="false" />
            </el-select>
          </el-space>
        </el-col>
      </el-row>
    </el-card>

    <!-- 统计卡片 -->
    <el-row v-if="showStats" :gutter="16" class="stats-row">
      <el-col :xs="24" :sm="8">
        <el-card shadow="hover">
          <div class="stat-card">
            <div class="stat-icon" style="background: #409eff">
              <el-icon :size="32"><Setting /></el-icon>
            </div>
            <div class="stat-content">
              <div class="stat-value">{{ stats.total_configurations }}</div>
              <div class="stat-label">总配置数</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :xs="24" :sm="8">
        <el-card shadow="hover">
          <div class="stat-card">
            <div class="stat-icon" style="background: #67c23a">
              <el-icon :size="32"><Check /></el-icon>
            </div>
            <div class="stat-content">
              <div class="stat-value">{{ stats.enabled_configurations }}</div>
              <div class="stat-label">已启用</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :xs="24" :sm="8">
        <el-card shadow="hover">
          <div class="stat-card">
            <div class="stat-icon" style="background: #e6a23c">
              <el-icon :size="32"><List /></el-icon>
            </div>
            <div class="stat-content">
              <div class="stat-value">{{ stats.total_settings }}</div>
              <div class="stat-label">总配置项</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 数据表格 -->
    <el-card class="table-card" shadow="never">
      <el-table
        v-loading="loading"
        :data="tableData"
        stripe
        border
        style="width: 100%"
      >
        <el-table-column prop="name" label="配置名称" min-width="180" />
        <el-table-column label="仪器" width="150">
          <template #default="{ row }">
            {{ row.tool?.name || '-' }}
          </template>
        </el-table-column>
        <el-table-column label="配置槽数" width="100">
          <template #default="{ row }">
            <el-tag>{{ row.num_slots || 0 }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="颜色标记" width="120">
          <template #default="{ row }">
            <div v-if="row.calendar_colors && row.calendar_colors.length > 0" style="display: flex; gap: 4px">
              <div
                v-for="(color, index) in row.calendar_colors.slice(0, 3)"
                :key="index"
                :style="{
                  width: '20px',
                  height: '20px',
                  backgroundColor: color,
                  border: '1px solid #ddd',
                  borderRadius: '4px'
                }"
              />
              <span v-if="row.calendar_colors.length > 3">...</span>
            </div>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.enabled ? 'success' : 'danger'">
              {{ row.enabled ? '已启用' : '已禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="180">
          <template #default="{ row }">
            {{ formatDateTime(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="320" fixed="right">
          <template #default="{ row }">
            <el-space>
              <el-button
                type="success"
                size="small"
                :icon="Setting"
                @click="handleChangeSetting(row)"
              >
                修改配置项
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
          @size-change="loadConfigurations"
          @current-change="loadConfigurations"
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
        <el-form-item label="配置名称" prop="name">
          <el-input v-model="formData.name" placeholder="请输入配置名称" />
        </el-form-item>
        <el-form-item label="仪器ID" prop="tool_id">
          <el-input v-model.number="formData.tool_id" placeholder="请输入仪器ID" />
        </el-form-item>
        <el-form-item label="启用状态" prop="enabled">
          <el-switch v-model="formData.enabled" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">
          确定
        </el-button>
      </template>
    </el-dialog>

    <!-- 修改配置项对话框 -->
    <el-dialog v-model="settingDialogVisible" title="修改配置项" width="500px">
      <el-form :model="settingForm" label-width="100px">
        <el-form-item label="配置槽" required>
          <el-input-number
            v-model="settingForm.slot"
            :min="0"
            placeholder="请输入配置槽编号"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="配置值" required>
          <el-select v-model="settingForm.choice" placeholder="请选择配置值" style="width: 100%">
            <el-option
              v-for="item in availableOptions"
              :key="item"
              :label="item"
              :value="item"
            />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="settingDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submitChangeSetting">
          确定
        </el-button>
      </template>
    </el-dialog>

    <!-- 配置历史对话框 -->
    <el-dialog v-model="historyDialogVisible" title="配置历史" width="900px">
      <el-table
        v-loading="historyLoading"
        :data="historyData"
        stripe
        border
        style="width: 100%"
      >
        <el-table-column label="配置" min-width="150">
          <template #default="{ row }">
            {{ row.configuration?.name || '-' }}
          </template>
        </el-table-column>
        <el-table-column label="用户" width="120">
          <template #default="{ row }">
            {{ row.user?.username || '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="slot" label="配置槽" width="100" />
        <el-table-column prop="setting" label="配置值" min-width="150" />
        <el-table-column prop="modification_time" label="修改时间" width="180">
          <template #default="{ row }">
            {{ formatDateTime(row.modification_time) }}
          </template>
        </el-table-column>
      </el-table>
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
  Setting,
  Histogram,
  Clock,
  Check,
  List,
  Search
} from '@element-plus/icons-vue'
import {
  getConfigurations,
  createConfiguration,
  updateConfiguration,
  deleteConfiguration,
  changeConfigurationSetting,
  getConfigurationStats,
  getConfigurationHistory
} from '@/api/configurations'
import type { Configuration } from '@/types'
import { formatDateTime } from '@/utils/helpers'

// 数据列表
const loading = ref(false)
const tableData = ref<Configuration[]>([])

// 统计数据
const showStats = ref(true)
const stats = ref({
  total_configurations: 0,
  enabled_configurations: 0,
  total_settings: 0
})

// 过滤器
const filterName = ref('')
const filterEnabled = ref<boolean>()

// 分页
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)

// 对话框
const dialogVisible = ref(false)
const dialogMode = ref<'create' | 'edit'>('create')
const dialogTitle = computed(() => (dialogMode.value === 'create' ? '创建配置' : '编辑配置'))
const submitting = ref(false)

// 修改配置项对话框
const settingDialogVisible = ref(false)
const availableOptions = ref<string[]>([])
const settingForm = reactive({
  configurationId: 0,
  slot: 0,
  choice: ''
})

// 历史记录对话框
const historyDialogVisible = ref(false)
const historyLoading = ref(false)
const historyData = ref<any[]>([])

// 表单
const formRef = ref<FormInstance>()
const formData = reactive<Partial<Configuration>>({
  name: '',
  tool_id: undefined,
  enabled: true
})

const formRules: FormRules = {
  name: [{ required: true, message: '请输入配置名称', trigger: 'blur' }],
  tool_id: [{ required: true, message: '请输入仪器ID', trigger: 'blur' }]
}

// 加载统计数据
const loadStats = async () => {
  try {
    const response = await getConfigurationStats()
    stats.value = response?.data || stats.value
  } catch (error) {
    console.error('加载统计数据失败:', error)
  }
}

// 加载配置列表
const loadConfigurations = async () => {
  loading.value = true
  try {
    const params = {
      skip: (currentPage.value - 1) * pageSize.value,
      limit: pageSize.value,
      ...(filterName.value && { name: filterName.value }),
      ...(filterEnabled.value !== undefined && { enabled: filterEnabled.value })
    }
    const response = await getConfigurations(params)
    tableData.value = Array.isArray(response) ? response : (response as any).data || []
    const serverTotal = (response as any)?._total
    total.value = typeof serverTotal === 'number' ? serverTotal : tableData.value.length
    await loadStats()
  } catch (error) {
    ElMessage.error('加载配置列表失败')
    console.error(error)
  } finally {
    loading.value = false
  }
}

// 打开创建对话框
const handleCreate = () => {
  dialogMode.value = 'create'
  dialogVisible.value = true
}

// 打开编辑对话框
const handleEdit = (row: Configuration) => {
  dialogMode.value = 'edit'
  Object.assign(formData, {
    id: row.id,
    name: row.name,
    tool_id: row.tool_id,
    enabled: row.enabled
  })
  dialogVisible.value = true
}

// 修改配置项
const handleChangeSetting = (row: Configuration) => {
  settingForm.configurationId = row.id
  settingForm.slot = 0
  settingForm.choice = ''
  
  if (row.available_settings) {
    availableOptions.value = row.available_settings.split(',').map(s => s.trim())
  } else {
    availableOptions.value = []
  }
  
  settingDialogVisible.value = true
}

const submitChangeSetting = async () => {
  if (!settingForm.choice) {
    ElMessage.warning('请选择配置值')
    return
  }

  const choiceIndex = availableOptions.value.indexOf(settingForm.choice)
  if (choiceIndex === -1) {
    ElMessage.error('无效的配置值')
    return
  }

  submitting.value = true
  try {
    await changeConfigurationSetting(settingForm.configurationId, {
      slot: settingForm.slot,
      choice: choiceIndex
    })
    ElMessage.success('修改成功')
    settingDialogVisible.value = false
    await loadConfigurations()
  } catch (error) {
    ElMessage.error('修改失败')
    console.error(error)
  } finally {
    submitting.value = false
  }
}

// 查看历史
const showHistory = async () => {
  historyLoading.value = true
  historyDialogVisible.value = true
  try {
    const response = await getConfigurationHistory()
    historyData.value = Array.isArray(response) ? response : (response as any).data || []
  } catch (error) {
    ElMessage.error('加载历史记录失败')
    console.error(error)
  } finally {
    historyLoading.value = false
  }
}

// 删除配置
const handleDelete = async (row: Configuration) => {
  try {
    await ElMessageBox.confirm('确定要删除该配置吗？此操作不可恢复！', '警告', {
      type: 'error',
      confirmButtonText: '确定删除'
    })
    await deleteConfiguration(row.id)
    ElMessage.success('删除成功')
    await loadConfigurations()
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
        await createConfiguration(formData)
        ElMessage.success('创建成功')
      } else {
        await updateConfiguration(formData.id!, formData)
        ElMessage.success('更新成功')
      }
      dialogVisible.value = false
      await loadConfigurations()
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
    name: '',
    tool_id: undefined,
    enabled: true
  })
}

// 初始化
onMounted(() => {
  loadConfigurations()
})
</script>

<style scoped>
.page-container {
  padding: 20px;
}

.header-card {
  margin-bottom: 16px;
}

.stats-row {
  margin-bottom: 16px;
}

.stat-card {
  display: flex;
  align-items: center;
  gap: 16px;
}

.stat-icon {
  width: 60px;
  height: 60px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
}

.stat-content {
  flex: 1;
}

.stat-value {
  font-size: 24px;
  font-weight: bold;
  color: #303133;
}

.stat-label {
  font-size: 14px;
  color: #909399;
  margin-top: 4px;
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
