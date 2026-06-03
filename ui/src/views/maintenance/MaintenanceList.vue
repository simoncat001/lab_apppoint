<template>
  <div class="page-container">
    <el-card class="header-card" shadow="never">
      <el-row :gutter="16" align="middle">
        <el-col :span="12">
          <el-space>
            <el-button type="primary" :icon="Plus" @click="handleCreate" v-if="authStore.isStaff()">新增维保</el-button>
            <el-button :icon="Refresh" @click="loadRecords">刷新</el-button>
          </el-space>
        </el-col>
      </el-row>
    </el-card>

    <el-card class="table-card" shadow="never">
      <el-table :data="tableData" v-loading="loading" stripe border>
        <el-table-column prop="tool_id" label="仪器ID" width="120" />
        <el-table-column prop="performed_at" label="维保时间" width="180">
          <template #default="{ row }">{{ formatDateTime(row.performed_at) }}</template>
        </el-table-column>
        <el-table-column prop="next_due_at" label="下次维保" width="180">
          <template #default="{ row }">{{ row.next_due_at ? formatDateTime(row.next_due_at) : '-' }}</template>
        </el-table-column>
        <el-table-column prop="description" label="维保说明" min-width="200" />
        <el-table-column label="操作" width="200" v-if="authStore.isStaff()">
          <template #default="{ row }">
            <el-space>
              <el-button size="small" :icon="Edit" @click="handleEdit(row)">编辑</el-button>
              <el-button size="small" type="danger" :icon="Delete" @click="handleDelete(row)">删除</el-button>
            </el-space>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="600px">
      <el-form :model="formData" label-width="120px">
        <el-form-item label="仪器ID">
          <el-input v-model.number="formData.tool_id" />
        </el-form-item>
        <el-form-item label="维保时间">
          <el-date-picker v-model="formData.performed_at" type="datetime" value-format="YYYY-MM-DDTHH:mm:ss" />
        </el-form-item>
        <el-form-item label="下次维保">
          <el-date-picker v-model="formData.next_due_at" type="datetime" value-format="YYYY-MM-DDTHH:mm:ss" />
        </el-form-item>
        <el-form-item label="说明">
          <el-input v-model="formData.description" type="textarea" :rows="3" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Refresh, Edit, Delete } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'
import { getMaintenanceRecords, createMaintenanceRecord, updateMaintenanceRecord, deleteMaintenanceRecord } from '@/api/maintenance'
import type { MaintenanceRecord } from '@/types'
import { formatDateTime } from '@/utils/helpers'

const authStore = useAuthStore()
const loading = ref(false)
const submitting = ref(false)
const tableData = ref<MaintenanceRecord[]>([])

const dialogVisible = ref(false)
const dialogMode = ref<'create' | 'edit'>('create')
const dialogTitle = ref('新增维保')

const formData = reactive<Partial<MaintenanceRecord>>({
  id: undefined,
  tool_id: undefined,
  performed_at: '',
  next_due_at: '',
  description: '',
})

const loadRecords = async () => {
  loading.value = true
  try {
    tableData.value = await getMaintenanceRecords()
  } catch (error) {
    console.error(error)
    ElMessage.error('加载维保记录失败')
  } finally {
    loading.value = false
  }
}

const handleCreate = () => {
  dialogMode.value = 'create'
  dialogTitle.value = '新增维保'
  Object.assign(formData, { id: undefined, tool_id: undefined, performed_at: '', next_due_at: '', description: '' })
  dialogVisible.value = true
}

const handleEdit = (row: MaintenanceRecord) => {
  dialogMode.value = 'edit'
  dialogTitle.value = '编辑维保'
  Object.assign(formData, row)
  dialogVisible.value = true
}

const handleDelete = async (row: MaintenanceRecord) => {
  try {
    await ElMessageBox.confirm('确定删除该记录吗？', '提示', { type: 'warning' })
    await deleteMaintenanceRecord(row.id)
    ElMessage.success('删除成功')
    loadRecords()
  } catch (error) {
    if (error !== 'cancel') {
      console.error(error)
      ElMessage.error('删除失败')
    }
  }
}

const handleSubmit = async () => {
  submitting.value = true
  try {
    if (dialogMode.value === 'create') {
      await createMaintenanceRecord(formData)
    } else {
      await updateMaintenanceRecord(formData.id!, formData)
    }
    ElMessage.success('保存成功')
    dialogVisible.value = false
    loadRecords()
  } catch (error) {
    console.error(error)
    ElMessage.error('保存失败')
  } finally {
    submitting.value = false
  }
}

onMounted(() => {
  loadRecords()
})
</script>

<style scoped>
.page-container {
  padding: 20px;
}
.header-card {
  margin-bottom: 16px;
}
</style>
