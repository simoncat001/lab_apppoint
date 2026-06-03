<template>
  <div class="page-container">
    <el-card class="header-card" shadow="never">
      <el-row :gutter="16" align="middle">
        <el-col :span="12">
          <el-space>
            <el-button :icon="ArrowLeft" @click="goBack">返回</el-button>
            <span class="title">{{ pageTitle }}</span>
          </el-space>
        </el-col>
      </el-row>
    </el-card>

    <el-card class="content-card" shadow="never" v-loading="pageLoading">
      <el-form ref="formRef" :model="formData" :rules="rules" label-width="110px">
        <el-alert
          v-if="balanceOnlyMode"
          class="mode-alert"
          type="info"
          :closable="false"
          title="内部员工组织账户仅可配置余额，成员由系统项目归属自动维护。"
        />

        <el-form-item label="账户名称" prop="name">
          <el-input
            v-model="formData.name"
            class="narrow-control"
            placeholder="例如：XX大学-材料学院"
            :disabled="balanceOnlyMode"
          />
        </el-form-item>

        <el-form-item label="账户类型" prop="type_id">
          <el-select
            v-model="formData.type_id"
            class="narrow-control"
            placeholder="可选"
            clearable
            :disabled="balanceOnlyMode"
          >
            <el-option
              v-for="type in accountTypes"
              :key="type.id"
              :label="type.name"
              :value="type.id"
            />
          </el-select>
          <div v-if="isSharedMembershipAccountType" class="hint">
            外部共享账户不绑定单一用户，请直接在下方添加共享成员；同一成员可加入多个共享账户，预约时再选择结算账户。
          </div>
        </el-form-item>

        <el-form-item v-if="projectBindingLocked" label="默认项目">
          <el-input
            :model-value="lockedProjectName"
            class="narrow-control"
            disabled
          />
          <div class="hint">该账户对应权鉴对外项目的默认预约账户，项目不可编辑。</div>
        </el-form-item>

        <el-form-item v-else-if="requiresProjectBinding" label="关联项目" required>
          <el-select
            v-model="selectedProjectId"
            class="narrow-control"
            placeholder="请选择项目"
            :disabled="balanceOnlyMode"
          >
            <el-option
              v-for="project in availableProjects"
              :key="project.id"
              :label="project.name"
              :value="project.id"
            />
          </el-select>
          <div class="hint">内部组织账户必须绑定一个项目，且每个项目只能绑定一个账户。</div>
        </el-form-item>

        <el-form-item v-if="!requiresProjectBinding" label="共享成员" prop="member_ids">
          <div class="member-panel">
            <div class="member-toolbar">
              <el-button
                type="primary"
                plain
                :icon="Plus"
                @click="memberPickerVisible = true"
              >
                添加成员
              </el-button>
              <span class="member-toolbar-text">共享成员可同时加入多个共享账户，预约时再选择结算账户。</span>
            </div>

            <div v-if="selectedMembers.length" class="member-board">
              <div class="member-board-header">
                <span>已选成员</span>
                <el-tag type="info" size="small">{{ selectedMembers.length }} 人</el-tag>
              </div>
              <ul class="member-list">
                <li v-for="member in selectedMembers" :key="member.id" class="member-item">
                  <div class="member-main">
                    <el-avatar class="member-avatar" :size="24">
                      {{ member.username.slice(0, 1).toUpperCase() }}
                    </el-avatar>
                    <div class="member-meta">
                      <span class="member-name">{{ member.username }}</span>
                      <span class="member-email">{{ member.email }}</span>
                    </div>
                  </div>
                  <el-button link type="danger" class="member-remove" @click="removeMember(member.id)">移除</el-button>
                </li>
              </ul>
            </div>
            <div v-else class="member-empty">
              暂无共享成员，请点击“添加成员”
            </div>
          </div>
        </el-form-item>

        <el-form-item label="状态" prop="active">
          <el-switch v-model="formData.active" :disabled="balanceOnlyMode" />
        </el-form-item>

        <el-form-item label="账户余额" prop="balance">
          <el-input-number
            v-model="formData.balance"
            class="narrow-control"
            :min="0"
            :precision="2"
            :step="100"
            controls-position="right"
          />
        </el-form-item>

        <el-form-item label="信用额度" prop="credit_limit">
          <el-input-number
            v-model="formData.credit_limit"
            class="narrow-control"
            :min="0"
            :precision="2"
            :step="100"
            controls-position="right"
            :disabled="balanceOnlyMode"
          />
          <div class="hint">
            余额不足时会消耗信用额度；信用额度耗尽（&lt;= 0）后将无法创建预约。
          </div>
        </el-form-item>

        <el-form-item label="备注" prop="note">
          <el-input
            v-model="formData.note"
            class="narrow-control"
            type="textarea"
            :rows="3"
            placeholder="可选"
            :disabled="balanceOnlyMode"
          />
        </el-form-item>
      </el-form>

      <el-dialog v-model="memberPickerVisible" title="添加共享成员" width="560px">
        <div class="member-picker-toolbar">
          <el-input
            v-model.trim="memberSearchKeyword"
            class="member-search-input"
            clearable
            placeholder="搜索用户名 / 邮箱 / 用户ID"
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>
          <span class="member-picker-count">共 {{ filteredAvailableMembers.length }} 条</span>
        </div>

        <el-table v-if="filteredAvailableMembers.length" :data="filteredAvailableMembers" border max-height="360">
          <el-table-column label="用户名" min-width="150">
            <template #default="{ row }">
              <span>{{ row.username }}</span>
            </template>
          </el-table-column>
          <el-table-column label="邮箱" min-width="220">
            <template #default="{ row }">
              <span class="picker-email">{{ row.email }}</span>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="90" align="center">
            <template #default="{ row }">
              <el-button type="primary" link @click="addMember(row.id)">添加</el-button>
            </template>
          </el-table-column>
        </el-table>
        <el-empty v-else :description="memberSearchKeyword ? '没有匹配成员' : '暂无可添加成员'" />
        <template #footer>
          <el-button @click="memberPickerVisible = false">关闭</el-button>
        </template>
      </el-dialog>

      <div class="action-bar">
        <el-space>
          <el-button @click="goBack">取消</el-button>
          <el-button type="primary" :loading="submitting" @click="handleSubmit">保存</el-button>
        </el-space>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { ArrowLeft, Plus, Search } from '@element-plus/icons-vue'

import { createAccount, getAccount, getAccountTypes, updateAccount } from '@/api/accounts'
import { getProjects } from '@/api/projects'
import { getUsers } from '@/api/users'
import type { Account, AccountType, Project, User } from '@/types'

type AccountSubmitPayload = Partial<Account> & { project_id?: number }

const route = useRoute()
const router = useRouter()

const pageLoading = ref(false)
const submitting = ref(false)
const memberPickerVisible = ref(false)
const memberSearchKeyword = ref('')

const accountTypes = ref<AccountType[]>([])
const users = ref<User[]>([])
const projects = ref<Project[]>([])

const formRef = ref<FormInstance>()

const getDefaultFormData = (): Partial<Account> => ({
  name: '',
  type_id: undefined,
  active: true,
  note: '',
  balance: 0,
  credit_limit: 0,
  member_ids: [],
})

const formData = reactive<Partial<Account>>(getDefaultFormData())

const rules: FormRules = {
  name: [{ required: true, message: '请输入账户名称', trigger: 'blur' }],
}

const accountId = computed<number | null>(() => {
  const raw = route.params.id
  if (!raw) return null
  const id = Number(raw)
  return Number.isInteger(id) && id > 0 ? id : null
})

const isEditMode = computed(() => accountId.value !== null)
const pageTitle = computed(() => (isEditMode.value ? '账户配置' : '创建账户'))
const selectedProjectId = ref<number>()
const projectBindingLocked = ref(false)
const lockedProjectName = ref('')
const selectedAccountType = computed(() => {
  if (!formData.type_id) return null
  return accountTypes.value.find((type) => type.id === formData.type_id) || null
})
const isInternalAccountType = computed(() => {
  const name = selectedAccountType.value?.name || ''
  const lowered = name.toLowerCase()
  return lowered.includes('internal') || name.includes('内部')
})
const isSharedMembershipAccountType = computed(() => {
  if (!selectedAccountType.value) return false
  return !isInternalAccountType.value
})
const requiresProjectBinding = computed(() => isInternalAccountType.value)
const balanceOnlyMode = computed(() => isEditMode.value && requiresProjectBinding.value)
const availableProjects = computed(() => {
  return projects.value.filter((project) => {
    if (!project.account_id) return true
    return !!(isEditMode.value && accountId.value && project.account_id === accountId.value)
  })
})
const selectedMembers = computed(() => {
  const idList = formData.member_ids || []
  const userMap = new Map(users.value.map((u) => [u.id, u]))
  return idList.map((id) => {
    const user = userMap.get(id)
    return {
      id,
      username: user?.username || `用户 #${id}`,
      email: user?.email || '-',
    }
  })
})
const availableMembers = computed(() => {
  const selectedSet = new Set(formData.member_ids || [])
  return users.value.filter((u) => !selectedSet.has(u.id))
})
const filteredAvailableMembers = computed(() => {
  const keyword = memberSearchKeyword.value.trim().toLowerCase()
  if (!keyword) {
    return availableMembers.value
  }
  return availableMembers.value.filter((u) => {
    const username = (u.username || '').toLowerCase()
    const email = (u.email || '').toLowerCase()
    const userId = String(u.id)
    return username.includes(keyword) || email.includes(keyword) || userId.includes(keyword)
  })
})

watch(
  () => formData.type_id,
  () => {
    if (!requiresProjectBinding.value && !projectBindingLocked.value) {
      selectedProjectId.value = undefined
    }
  }
)
watch(
  () => memberPickerVisible.value,
  (visible) => {
    if (visible) {
      memberSearchKeyword.value = ''
    }
  }
)

const addMember = (memberId: number) => {
  const ids = formData.member_ids || []
  if (ids.includes(memberId)) return
  formData.member_ids = [...ids, memberId]
}

const removeMember = (memberId: number) => {
  formData.member_ids = (formData.member_ids || []).filter((id) => id !== memberId)
}

const goBack = () => {
  router.push({ name: 'Accounts' })
}

const loadAccountTypes = async () => {
  const res = await getAccountTypes()
  accountTypes.value = Array.isArray(res) ? res : (res as any).data || []
}

const loadUsers = async () => {
  const res = await getUsers({ skip: 0, limit: 1000 })
  users.value = Array.isArray(res) ? res : (res as any).data || []
}

const loadProjects = async () => {
  const res = await getProjects({ skip: 0, limit: 1000 })
  projects.value = Array.isArray(res) ? res : (res as any).data || []
}

const loadAccountDetail = async () => {
  if (!accountId.value) {
    ElMessage.error('账户ID无效')
    goBack()
    return
  }

  const res = await getAccount(accountId.value)
  const row = ((res as any).data || res) as Account

  Object.assign(formData, {
    id: row.id,
    name: row.name,
    type_id: row.type_id ?? undefined,
    active: row.active,
    note: row.note || '',
    balance: Number(row.balance || 0),
    credit_limit: Number(row.credit_limit || 0),
    member_ids: row.member_ids || (row.members ? row.members.map((m) => m.id) : []),
  })
  projectBindingLocked.value = Boolean(row.project_binding_locked)
  const defaultProjectId = row.default_project_id || undefined
  const defaultProjectName = (row.default_project_name || '').trim()
  const boundProject = projects.value.find((project) => project.account_id === row.id)
  if (projectBindingLocked.value) {
    selectedProjectId.value = defaultProjectId || boundProject?.id
    const fallbackName = (boundProject?.external_display_name || boundProject?.name || '').trim()
    lockedProjectName.value =
      defaultProjectName ||
      fallbackName ||
      (selectedProjectId.value ? `#${selectedProjectId.value}` : '')
  } else {
    selectedProjectId.value = boundProject?.id
    lockedProjectName.value = ''
  }
}

const initialize = async () => {
  pageLoading.value = true
  try {
    await Promise.all([loadAccountTypes(), loadUsers(), loadProjects()])
    if (isEditMode.value) {
      await loadAccountDetail()
    } else {
      Object.assign(formData, getDefaultFormData())
      selectedProjectId.value = undefined
      projectBindingLocked.value = false
      lockedProjectName.value = ''
    }
  } catch (e) {
    console.error(e)
    ElMessage.error('加载账户配置失败')
  } finally {
    pageLoading.value = false
  }
}

const handleSubmit = async () => {
  if (!formRef.value) return

  const valid = await formRef.value
    .validate()
    .then(() => true)
    .catch(() => false)
  if (!valid) return

  submitting.value = true
  try {
    if ((requiresProjectBinding.value || projectBindingLocked.value) && !selectedProjectId.value) {
      ElMessage.warning(projectBindingLocked.value ? '该账户缺少默认项目关联' : '内部组织账户必须关联一个项目')
      submitting.value = false
      return
    }

    let payload: AccountSubmitPayload
    if (balanceOnlyMode.value) {
      payload = {
        balance: formData.balance,
      }
    } else {
      payload = {
        name: formData.name,
        type_id: formData.type_id,
        active: formData.active,
        note: formData.note || undefined,
        balance: formData.balance,
        credit_limit: formData.credit_limit,
        member_ids: requiresProjectBinding.value ? undefined : (formData.member_ids || []),
        project_id:
          (requiresProjectBinding.value || projectBindingLocked.value)
            ? selectedProjectId.value
            : undefined,
      }
    }

    if (isEditMode.value && accountId.value) {
      await updateAccount(accountId.value, payload)
      ElMessage.success('更新成功')
    } else {
      await createAccount(payload)
      ElMessage.success('创建成功')
    }

    goBack()
  } catch (e: any) {
    console.error(e)
    ElMessage.error(e?.response?.data?.detail || (isEditMode.value ? '更新失败' : '创建失败'))
  } finally {
    submitting.value = false
  }
}

onMounted(() => {
  initialize()
})
</script>

<style scoped>
.page-container {
  padding: 20px;
}

.header-card {
  margin-bottom: 16px;
}

.title {
  font-size: 16px;
  font-weight: 600;
}

.action-bar {
  margin-top: 20px;
  text-align: right;
}

.mode-alert {
  margin-bottom: 14px;
}

.hint {
  margin-top: 6px;
  font-size: 12px;
  color: #909399;
}

.member-panel {
  width: min(100%, 460px);
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.member-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.member-toolbar-text {
  color: #8a9099;
  font-size: 12px;
}

.picker-email {
  color: #8a9099;
}

.member-picker-toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 10px;
}

.member-search-input {
  flex: 1;
}

.member-picker-count {
  flex: 0 0 auto;
  color: #8a9099;
  font-size: 12px;
}

.member-board {
  border: 1px solid #dfe7f3;
  border-radius: 10px;
  overflow: hidden;
  background: linear-gradient(180deg, #fafcff 0%, #f7f9fc 100%);
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.05);
}

.member-board-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  border-bottom: 1px solid #e8edf5;
  color: #606266;
  font-size: 13px;
}

.member-list {
  margin: 0;
  padding: 0;
  list-style: none;
}

.member-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 8px 12px;
  transition: background-color 0.2s ease;
}

.member-item + .member-item {
  border-top: 1px solid #ecf1f7;
}

.member-item:hover {
  background: #ffffff;
}

.member-avatar {
  flex: 0 0 auto;
  background: #4e82f5;
  color: #fff;
  font-size: 12px;
}

.member-main {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}

.member-meta {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.member-name {
  font-weight: 600;
  color: #303133;
  line-height: 1.2;
}

.member-email {
  color: #8a9099;
  font-size: 12px;
  line-height: 1.2;
  margin-top: 2px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 260px;
}

.member-empty {
  padding: 8px 12px;
  border: 1px dashed #d8e0ec;
  border-radius: 10px;
  background: #fafbfd;
  color: #909399;
  font-size: 13px;
}

.member-remove {
  font-weight: 500;
}

.narrow-control {
  width: min(100%, 460px);
}

@media (max-width: 768px) {
  .member-panel {
    width: 100%;
  }

  .member-toolbar {
    flex-direction: column;
    align-items: flex-start;
  }

  .member-picker-toolbar {
    flex-direction: column;
    align-items: stretch;
  }

  .member-email {
    max-width: 170px;
  }
}
</style>
