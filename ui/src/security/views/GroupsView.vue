<template>
  <div class="page-grid">
    <div class="card">
      <div class="toolbar-row">
        <div>
          <h3>小组列表</h3>
          <p class="muted" style="margin-top: 6px;">选择项目后查看小组。</p>
        </div>
        <div class="toolbar-actions">
          <button class="button ghost" @click="loadGroups" :disabled="!selectedProjectId">刷新</button>
          <button class="button" @click="openCreate" :disabled="!selectedProjectId">新增小组</button>
        </div>
      </div>

      <div class="filter-row">
        <label class="field">
          <span>所属项目</span>
          <select v-model.number="selectedProjectId" class="input" @change="loadGroups">
            <option :value="0">请选择项目</option>
            <option v-for="project in projects" :key="project.id" :value="project.id">
              {{ project.name }}
            </option>
          </select>
        </label>
      </div>

      <table class="table" style="margin-top: 16px;">
        <thead>
          <tr>
            <th>名称</th>
            <th>项目</th>
            <th>描述</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="group in groups" :key="group.id" class="row-click" @click="selectGroup(group.id)">
            <td>{{ group.name }}</td>
            <td>{{ group.projectId }}</td>
            <td class="cell-muted"><span class="text-ellipsis">{{ group.description || '-' }}</span></td>
            <td>
              <div class="table-actions">
                <button class="button ghost" @click.stop="openApply(group)">申请</button>
                <button class="button ghost" @click.stop="openAddMembers(group)">添加成员</button>
                <button class="button ghost" @click.stop="openSetAdmin(group)">设管理员</button>
                <button class="button ghost" @click.stop="openRemoveAdmin(group)">取消管理员</button>
                <button class="button secondary" @click.stop="openEdit(group)">编辑</button>
                <button class="button" style="background: #c94321;" @click.stop="handleDelete(group)">删除</button>
              </div>
            </td>
          </tr>
          <tr v-if="!groups.length">
            <td colspan="4" style="text-align: center; padding: 20px;">暂无小组</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="detail-panel">
      <h3>小组详情</h3>
      <p class="muted" style="margin-top: 6px;">点击左侧小组查看详情。</p>
      <div v-if="detail" style="margin-top: 16px; display: grid; gap: 10px;">
        <div class="pill">名称：{{ detail.name }}</div>
        <div class="pill">成员数：{{ detail.memberCount ?? '-' }}</div>
        <div class="pill">管理员：{{ detail.adminId ?? '-' }}</div>
        <div class="pill">创建时间：{{ formatDateTime(detail.createdTime) }}</div>
        <p class="cell-muted">{{ detail.description || '暂无描述' }}</p>
      </div>
    </div>
  </div>

  <ModalShell :open="showCreate" title="新增小组" subtitle="在项目下创建小组" @close="showCreate = false">
    <label class="field">
      <span>小组名称</span>
      <input v-model="form.name" class="input" />
    </label>
    <label class="field">
      <span>所属项目</span>
      <select v-model.number="form.projectId" class="input">
        <option disabled :value="0">选择项目</option>
        <option v-for="project in projects" :key="project.id" :value="project.id">
          {{ project.name }}
        </option>
      </select>
    </label>
    <label class="field">
      <span>描述</span>
      <textarea v-model="form.description" class="input" rows="3" />
    </label>
    <button class="button" @click="submitCreate">保存</button>
  </ModalShell>

  <ModalShell :open="showEdit" title="编辑小组" subtitle="更新小组信息" @close="showEdit = false">
    <label class="field">
      <span>小组名称</span>
      <input v-model="form.name" class="input" />
    </label>
    <label class="field">
      <span>描述</span>
      <textarea v-model="form.description" class="input" rows="3" />
    </label>
    <button class="button" @click="submitEdit">更新</button>
  </ModalShell>

  <ModalShell :open="showApply" title="申请加入小组" subtitle="填写加入理由" @close="showApply = false">
    <label class="field">
      <span>申请理由</span>
      <textarea v-model="applyReason" class="input" rows="3" />
    </label>
    <button class="button" @click="submitApply">提交申请</button>
  </ModalShell>

  <ModalShell :open="showAddMembers" title="添加小组成员" subtitle="输入用户ID，逗号分隔" @close="showAddMembers = false">
    <label class="field">
      <span>用户 ID 列表</span>
      <input v-model="memberUserIds" class="input" placeholder="例如 12,18,25" />
    </label>
    <button class="button" @click="submitAddMembers">确认添加</button>
  </ModalShell>

  <ModalShell :open="showSetAdmin" title="设置小组管理员" subtitle="输入用户 ID" @close="showSetAdmin = false">
    <label class="field">
      <span>用户 ID</span>
      <input v-model="adminUserId" class="input" placeholder="请输入用户ID" />
    </label>
    <button class="button" @click="submitSetAdmin">确认设置</button>
  </ModalShell>

  <ModalShell :open="showRemoveAdmin" title="取消小组管理员" subtitle="输入用户 ID" @close="showRemoveAdmin = false">
    <label class="field">
      <span>用户 ID</span>
      <input v-model="removeAdminUserId" class="input" placeholder="请输入用户ID" />
    </label>
    <button class="button secondary" @click="submitRemoveAdmin">确认取消</button>
  </ModalShell>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue';
import type { Group, GroupDetail, Project } from '@/security/types/models';
import {
  addGroupMembers,
  applyGroup,
  createGroup,
  deleteGroup,
  fetchGroupDetail,
  fetchGroups,
  fetchProjects,
  removeGroupAdmin,
  setGroupAdmin,
  updateGroup
} from '@/security/api/endpoints';
import { useNotifyStore } from '@/security/stores/notify';
import { formatDateTime } from '@/security/utils/format';
import ModalShell from '@/security/components/ModalShell.vue';

const notify = useNotifyStore();
const projects = ref<Project[]>([]);
const groups = ref<Group[]>([]);
const detail = ref<GroupDetail | null>(null);

const selectedProjectId = ref(0);
const showCreate = ref(false);
const showEdit = ref(false);
const showApply = ref(false);
const showAddMembers = ref(false);
const showSetAdmin = ref(false);
const showRemoveAdmin = ref(false);
const applyTarget = ref<Group | null>(null);
const editTarget = ref<Group | null>(null);
const applyReason = ref('');
const memberUserIds = ref('');
const adminUserId = ref('');
const removeAdminUserId = ref('');
const adminTarget = ref<Group | null>(null);

const form = ref({
  name: '',
  description: '',
  projectId: 0
});

const loadProjects = async () => {
  try {
    projects.value = (await fetchProjects()) as Project[];
  } catch (error: any) {
    notify.push(error?.message || '项目加载失败', 'error');
  }
};

const loadGroups = async () => {
  if (!selectedProjectId.value) {
    groups.value = [];
    detail.value = null;
    return;
  }
  try {
    groups.value = (await fetchGroups(selectedProjectId.value)) as Group[];
  } catch (error: any) {
    notify.push(error?.message || '小组列表加载失败', 'error');
  }
};

const selectGroup = async (id: number) => {
  try {
    detail.value = (await fetchGroupDetail(id)) as GroupDetail;
  } catch (error: any) {
    notify.push(error?.message || '小组详情加载失败', 'error');
  }
};

const openCreate = () => {
  form.value = { name: '', description: '', projectId: selectedProjectId.value || 0 };
  showCreate.value = true;
};

const openEdit = (group: Group) => {
  form.value = { name: group.name, description: group.description || '', projectId: group.projectId };
  editTarget.value = group;
  showEdit.value = true;
};

const openApply = (group: Group) => {
  applyTarget.value = group;
  applyReason.value = '';
  showApply.value = true;
};

const openAddMembers = (group: Group) => {
  adminTarget.value = group;
  memberUserIds.value = '';
  showAddMembers.value = true;
};

const openSetAdmin = (group: Group) => {
  adminTarget.value = group;
  adminUserId.value = '';
  showSetAdmin.value = true;
};

const openRemoveAdmin = (group: Group) => {
  adminTarget.value = group;
  removeAdminUserId.value = '';
  showRemoveAdmin.value = true;
};

const submitCreate = async () => {
  if (!form.value.name || !form.value.projectId) {
    notify.push('请完善小组信息', 'error');
    return;
  }
  try {
    await createGroup({
      name: form.value.name,
      description: form.value.description,
      projectId: form.value.projectId
    });
    notify.push('小组已创建', 'success');
    showCreate.value = false;
    await loadGroups();
  } catch (error: any) {
    notify.push(error?.message || '创建失败', 'error');
  }
};

const submitEdit = async () => {
  if (!editTarget.value) return;
  try {
    await updateGroup(editTarget.value.id, {
      name: form.value.name,
      description: form.value.description
    });
    notify.push('小组已更新', 'success');
    showEdit.value = false;
    await loadGroups();
    if (detail.value?.id === editTarget.value.id) {
      await selectGroup(editTarget.value.id);
    }
  } catch (error: any) {
    notify.push(error?.message || '更新失败', 'error');
  }
};

const handleDelete = async (group: Group) => {
  if (!confirm(`确认删除小组：${group.name}？`)) return;
  try {
    await deleteGroup(group.id);
    notify.push('小组已删除', 'success');
    await loadGroups();
    if (detail.value?.id === group.id) {
      detail.value = null;
    }
  } catch (error: any) {
    notify.push(error?.message || '删除失败', 'error');
  }
};

const submitApply = async () => {
  if (!applyTarget.value) return;
  try {
    await applyGroup(applyTarget.value.id, { reason: applyReason.value });
    notify.push('申请已提交', 'success');
    showApply.value = false;
  } catch (error: any) {
    notify.push(error?.message || '申请失败', 'error');
  }
};

const submitAddMembers = async () => {
  if (!adminTarget.value || !memberUserIds.value) {
    notify.push('请输入用户 ID', 'error');
    return;
  }
  const userIds = memberUserIds.value
    .split(',')
    .map((v) => Number(v.trim()))
    .filter((v) => Number.isFinite(v) && v > 0);
  if (!userIds.length) {
    notify.push('用户 ID 格式不正确', 'error');
    return;
  }
  try {
    await addGroupMembers(adminTarget.value.id, userIds);
    notify.push('成员已添加', 'success');
    showAddMembers.value = false;
    if (detail.value?.id === adminTarget.value.id) {
      await selectGroup(adminTarget.value.id);
    }
  } catch (error: any) {
    notify.push(error?.message || '添加失败', 'error');
  }
};

const submitSetAdmin = async () => {
  if (!adminTarget.value || !adminUserId.value) {
    notify.push('请输入用户 ID', 'error');
    return;
  }
  try {
    await setGroupAdmin(adminTarget.value.id, Number(adminUserId.value));
    notify.push('管理员已设置', 'success');
    showSetAdmin.value = false;
  } catch (error: any) {
    notify.push(error?.message || '设置失败', 'error');
  }
};

const submitRemoveAdmin = async () => {
  if (!adminTarget.value || !removeAdminUserId.value) {
    notify.push('请输入用户 ID', 'error');
    return;
  }
  try {
    await removeGroupAdmin(adminTarget.value.id, Number(removeAdminUserId.value));
    notify.push('管理员已取消', 'success');
    showRemoveAdmin.value = false;
  } catch (error: any) {
    notify.push(error?.message || '取消失败', 'error');
  }
};

onMounted(async () => {
  await loadProjects();
});
</script>
