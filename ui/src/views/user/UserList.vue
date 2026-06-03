<template>
  <div class="page-container">
    <el-card class="header-card" shadow="never">
      <el-row :gutter="16" align="middle">
        <el-col :span="12">
          <el-button :icon="Refresh" @click="loadUsers">刷新</el-button>
        </el-col>
        <el-col :span="12" style="text-align: right">
          <!-- 预留搜索框 -->
        </el-col>
      </el-row>
    </el-card>

    <el-card class="table-card" shadow="never">
      <el-table
        v-loading="loading"
        :data="tableData"
        stripe
        border
        style="width: 100%"
      >
        <el-table-column prop="username" label="用户名" min-width="120" />
        <el-table-column label="姓名" width="140">
          <template #default="{ row }">{{ getUserDisplayName(row) }}</template>
        </el-table-column>
        <el-table-column prop="last_name" label="姓" width="90" />
        <el-table-column prop="first_name" label="名" width="90" />
        <el-table-column prop="email" label="邮箱" min-width="180" />
        <el-table-column label="角色" width="150">
          <template #default="{ row }">
            <el-tag v-if="row.is_superuser" type="danger" effect="plain" style="margin-right: 5px">超级管理员</el-tag>
            <el-tag v-else-if="row.is_staff" type="primary" effect="plain">管理员</el-tag>
            <el-tag v-else type="info" effect="plain">普通用户</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="权限" width="180">
          <template #default="{ row }">
            <div class="permission-tags">
              <el-tag v-if="row.priority_reservation" type="success" effect="plain">优先预约</el-tag>
              <el-tag v-if="row.special_course_access" type="warning" effect="plain">特殊课程</el-tag>
              <span v-if="!row.priority_reservation && !row.special_course_access">-</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusTagType(row)">
              {{ getStatusLabel(row) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="date_joined" label="注册时间" width="180">
          <template #default="{ row }">
            {{ formatDateTime(row.date_joined) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" min-width="360">
          <template #default="{ row }">
            <div v-if="row.id !== authStore.user?.id" class="user-actions">
                <el-button
                  v-if="!row.is_active"
                  class="action-btn"
                  type="success"
                  size="small"
                  @click="toggleActive(row, true)"
                >
                  通过审核
                </el-button>
                <el-button
                  v-else
                  class="action-btn"
                  type="warning"
                  size="small"
                  @click="toggleActive(row, false)"
                >
                  停用
                </el-button>

                <el-button
                  v-if="!row.is_staff && !row.is_superuser && !row.is_verified"
                  class="action-btn"
                  type="primary"
                  size="small"
                  @click="toggleVerified(row, true)"
                >
                  验证
                </el-button>
                <el-button
                  v-if="!row.is_staff && !row.is_superuser && row.is_verified"
                  class="action-btn"
                  type="info"
                  size="small"
                  @click="toggleVerified(row, false)"
                >
                  取消验证
                </el-button>
                <el-button
                  v-if="!row.is_staff && !row.is_superuser"
                  class="action-btn"
                  type="warning"
                  size="small"
                  @click="toggleSpecialCourse(row)"
                >
                  {{ row.special_course_access ? '取消课程' : '特殊课程' }}
                </el-button>
                <el-button
                  v-if="row.is_staff && !row.is_superuser"
                  class="action-btn"
                  type="info"
                  size="small"
                  @click="setManagedTools(row)"
                >
                  管理设备
                </el-button>
            </div>
            <div v-else class="operation-self">
              <el-tag type="info">当前用户</el-tag>
            </div>
             <!-- 预留编辑按钮 -->
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="managedToolsDialogVisible" title="管理设备范围" width="560px">
      <el-form label-width="90px">
        <el-form-item label="用户">
          <span>{{ editingManagedUser ? getUserDisplayName(editingManagedUser) : '-' }}</span>
        </el-form-item>
        <el-form-item label="可管理仪器">
          <el-select
            v-model="managedToolSelection"
            multiple
            filterable
            clearable
            collapse-tags
            collapse-tags-tooltip
            placeholder="请选择仪器"
            style="width: 100%"
          >
            <el-option
              v-for="tool in tools"
              :key="tool.id"
              :label="tool.name"
              :value="tool.id"
            />
          </el-select>
          <div class="field-helper">不选择任何仪器表示全局管理员，可管理全部仪器。</div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="managedToolsDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="savingManagedTools" @click="saveManagedTools">
          保存
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { Refresh } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getUsers, updateUser } from '@/api/users'
import { getTools } from '@/api/tools'
import type { Tool, User } from '@/types'
import { formatDateTime } from '@/utils/date'
import { getUserDisplayName } from '@/utils/user'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()
const loading = ref(false)
const tableData = ref<User[]>([])
const tools = ref<Tool[]>([])
const managedToolsDialogVisible = ref(false)
const savingManagedTools = ref(false)
const editingManagedUser = ref<User | null>(null)
const managedToolSelection = ref<number[]>([])

const loadUsers = async () => {
  loading.value = true
  try {
    const res = await getUsers({ skip: 0, limit: 100 })
    // Assume res is array or wrap
    tableData.value = (res as any) || []
  } catch (error) {
    console.error(error)
    ElMessage.error('加载用户列表失败')
  } finally {
    loading.value = false
  }
}

const loadTools = async () => {
  try {
    tools.value = await getTools({ skip: 0, limit: 1000 })
  } catch (error) {
    console.error(error)
    ElMessage.error('加载仪器列表失败')
  }
}

const getStatusLabel = (row: User): string => {
  const status = row.status || (!row.is_active ? 'INACTIVE' : row.is_verified ? 'VERIFIED' : 'ACTIVE')
  if (status === 'VERIFIED') return '已验证'
  if (status === 'ACTIVE') return '已激活'
  return '未激活'
}

const getStatusTagType = (row: User): 'success' | 'warning' | 'danger' | 'info' => {
  const status = row.status || (!row.is_active ? 'INACTIVE' : row.is_verified ? 'VERIFIED' : 'ACTIVE')
  if (status === 'VERIFIED') return 'success'
  if (status === 'ACTIVE') return 'warning'
  return 'danger'
}

const toggleActive = async (user: User, isActive: boolean) => {
  const actionText = isActive ? '激活(通过审核)' : '停用'
  try {
    await ElMessageBox.confirm(
      `确定要${actionText}用户 "${user.username}" 吗?`,
      '提示',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: isActive ? 'success' : 'warning'
      }
    )
    
    await updateUser(user.id, { is_active: isActive })
    ElMessage.success(`用户已${actionText}`)
    
    // Update local state or reload
    user.is_active = isActive
  } catch (e) {
    // Cancelled or error
    if (e !== 'cancel') {
        console.error(e)
        ElMessage.error('操作失败')
    }
  }
}

const toggleVerified = async (user: User, isVerified: boolean) => {
  const actionText = isVerified ? '验证' : '取消验证'
  try {
    await ElMessageBox.confirm(
      `确定要${actionText}用户 "${user.username}" 吗?`,
      '提示',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: isVerified ? 'success' : 'warning'
      }
    )

    await updateUser(user.id, { is_verified: isVerified })
    ElMessage.success(`用户已${actionText}`)
    user.is_verified = isVerified
  } catch (e) {
    if (e !== 'cancel') {
      console.error(e)
      ElMessage.error('操作失败')
    }
  }
}

const toggleSpecialCourse = async (user: User) => {
  try {
    await updateUser(user.id, { special_course_access: !user.special_course_access })
    user.special_course_access = !user.special_course_access
    ElMessage.success('已更新课程权限')
  } catch (e) {
    console.error(e)
    ElMessage.error('操作失败')
  }
}

const setManagedTools = async (user: User) => {
  editingManagedUser.value = user
  managedToolSelection.value = [...(user.managed_tool_ids || [])]
  managedToolsDialogVisible.value = true
}

const saveManagedTools = async () => {
  if (!editingManagedUser.value) return
  savingManagedTools.value = true
  try {
    const value = [...managedToolSelection.value]
    await updateUser(editingManagedUser.value.id, { managed_tool_ids: value })
    editingManagedUser.value.managed_tool_ids = value
    ElMessage.success('已更新管理范围')
    managedToolsDialogVisible.value = false
  } catch (e) {
    console.error(e)
    ElMessage.error('操作失败')
  } finally {
    savingManagedTools.value = false
  }
}

onMounted(() => {
  loadUsers()
  loadTools()
})
</script>

<style scoped>
.header-card {
  margin-bottom: 16px;
}
.page-container {
  padding: 20px;
}

.field-helper {
  margin-top: 6px;
  color: #909399;
  font-size: 12px;
  line-height: 1.4;
}

.permission-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
  min-height: 28px;
}

.user-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  white-space: nowrap;
}

.action-btn {
  flex: 0 0 auto;
  margin: 0;
  padding-inline: 12px;
}

.operation-self {
  display: flex;
  align-items: center;
  min-height: 40px;
}
</style>
