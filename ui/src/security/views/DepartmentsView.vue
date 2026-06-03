<template>
  <div class="page-grid">
    <div class="card">
      <div class="toolbar-row">
        <div>
          <h3>部门列表</h3>
          <p class="muted" style="margin-top: 6px;">点击行查看详情。</p>
        </div>
        <div class="toolbar-actions">
          <button class="button ghost" @click="loadDepartments">刷新</button>
          <button class="button" @click="openCreate">新增部门</button>
        </div>
      </div>

      <table class="table" style="margin-top: 16px;">
        <thead>
          <tr>
            <th>名称</th>
            <th>描述</th>
            <th>ID</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="dept in departments" :key="dept.id" class="row-click" @click="selectDepartment(dept.id)">
            <td>{{ dept.name }}</td>
            <td class="cell-muted">
              <span class="text-ellipsis">{{ dept.description || '-' }}</span>
            </td>
            <td>{{ dept.id }}</td>
            <td>
              <div class="table-actions">
                <button class="button ghost" @click.stop="openApply(dept)">申请</button>
                <button class="button ghost" @click.stop="openAddMembers(dept)">添加成员</button>
                <button class="button ghost" @click.stop="openSetAdmin(dept)">设管理员</button>
                <button class="button ghost" @click.stop="openRemoveAdmin(dept)">取消管理员</button>
                <button class="button secondary" @click.stop="openEdit(dept)">编辑</button>
                <button class="button" style="background: #c94321;" @click.stop="handleDelete(dept)">删除</button>
              </div>
            </td>
          </tr>
          <tr v-if="!departments.length">
            <td colspan="4" style="text-align: center; padding: 20px;">暂无部门</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="detail-panel">
      <h3>部门详情</h3>
      <p class="muted" style="margin-top: 6px;">选择左侧部门查看。</p>
      <div v-if="detail" style="margin-top: 16px; display: grid; gap: 10px;">
        <div class="pill">名称：{{ detail.name }}</div>
        <div class="pill">成员数：{{ detail.memberCount ?? '-' }}</div>
        <div class="pill">项目数：{{ detail.projectCount ?? '-' }}</div>
        <div class="pill">创建时间：{{ formatDateTime(detail.createdTime) }}</div>
        <p class="cell-muted">{{ detail.description || '暂无描述' }}</p>
      </div>
    </div>
  </div>

  <ModalShell :open="showCreate" title="新增部门" subtitle="创建新的组织部门" @close="showCreate = false">
    <label class="field">
      <span>部门名称</span>
      <input v-model="form.name" class="input" />
    </label>
    <label class="field">
      <span>描述</span>
      <textarea v-model="form.description" class="input" rows="3" />
    </label>
    <button class="button" @click="submitCreate">保存</button>
  </ModalShell>

  <ModalShell :open="showEdit" title="编辑部门" subtitle="更新部门信息" @close="showEdit = false">
    <label class="field">
      <span>部门名称</span>
      <input v-model="form.name" class="input" />
    </label>
    <label class="field">
      <span>描述</span>
      <textarea v-model="form.description" class="input" rows="3" />
    </label>
    <button class="button" @click="submitEdit">更新</button>
  </ModalShell>

  <ModalShell :open="showApply" title="申请加入部门" subtitle="填写加入理由" @close="showApply = false">
    <label class="field">
      <span>申请理由</span>
      <textarea v-model="applyReason" class="input" rows="3" />
    </label>
    <button class="button" @click="submitApply">提交申请</button>
  </ModalShell>

  <ModalShell :open="showAddMembers" title="添加部门成员" subtitle="输入用户ID，逗号分隔" @close="showAddMembers = false">
    <label class="field">
      <span>用户 ID 列表</span>
      <input v-model="memberUserIds" class="input" placeholder="例如 12,18,25" />
    </label>
    <button class="button" @click="submitAddMembers">确认添加</button>
  </ModalShell>

  <ModalShell :open="showSetAdmin" title="设置部门管理员" subtitle="输入用户 ID" @close="showSetAdmin = false">
    <label class="field">
      <span>用户 ID</span>
      <input v-model="adminUserId" class="input" placeholder="请输入用户ID" />
    </label>
    <button class="button" @click="submitSetAdmin">确认设置</button>
  </ModalShell>

  <ModalShell :open="showRemoveAdmin" title="取消部门管理员" subtitle="输入用户 ID" @close="showRemoveAdmin = false">
    <label class="field">
      <span>用户 ID</span>
      <input v-model="removeAdminUserId" class="input" placeholder="请输入用户ID" />
    </label>
    <button class="button secondary" @click="submitRemoveAdmin">确认取消</button>
  </ModalShell>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue';
import type { Department, DepartmentDetail } from '@/security/types/models';
import { addDepartmentMembers, applyDepartment, createDepartment, deleteDepartment, fetchDepartmentDetail, fetchDepartments, removeDepartmentAdmin, setDepartmentAdmin, updateDepartment } from '@/security/api/endpoints';
import { useNotifyStore } from '@/security/stores/notify';
import { formatDateTime } from '@/security/utils/format';
import ModalShell from '@/security/components/ModalShell.vue';

const notify = useNotifyStore();

const departments = ref<Department[]>([]);
const detail = ref<DepartmentDetail | null>(null);

const showCreate = ref(false);
const showEdit = ref(false);
const showApply = ref(false);
const showAddMembers = ref(false);
const showSetAdmin = ref(false);
const showRemoveAdmin = ref(false);
const applyTarget = ref<Department | null>(null);
const editTarget = ref<Department | null>(null);
const applyReason = ref('');
const memberUserIds = ref('');
const adminUserId = ref('');
const removeAdminUserId = ref('');
const adminTarget = ref<Department | null>(null);

const form = ref({
  name: '',
  description: ''
});

const loadDepartments = async () => {
  try {
    departments.value = (await fetchDepartments()) as Department[];
  } catch (error: any) {
    notify.push(error?.message || '部门列表加载失败', 'error');
  }
};

const selectDepartment = async (id: number) => {
  try {
    detail.value = (await fetchDepartmentDetail(id)) as DepartmentDetail;
  } catch (error: any) {
    notify.push(error?.message || '部门详情加载失败', 'error');
  }
};

const openCreate = () => {
  form.value = { name: '', description: '' };
  showCreate.value = true;
};

const openEdit = (dept: Department) => {
  form.value = { name: dept.name, description: dept.description || '' };
  showEdit.value = true;
  editTarget.value = dept;
};

const openApply = (dept: Department) => {
  applyTarget.value = dept;
  applyReason.value = '';
  showApply.value = true;
};

const openAddMembers = (dept: Department) => {
  adminTarget.value = dept;
  memberUserIds.value = '';
  showAddMembers.value = true;
};

const openSetAdmin = (dept: Department) => {
  adminTarget.value = dept;
  adminUserId.value = '';
  showSetAdmin.value = true;
};

const openRemoveAdmin = (dept: Department) => {
  adminTarget.value = dept;
  removeAdminUserId.value = '';
  showRemoveAdmin.value = true;
};

const submitCreate = async () => {
  if (!form.value.name) {
    notify.push('请输入部门名称', 'error');
    return;
  }
  try {
    await createDepartment(form.value);
    notify.push('部门已创建', 'success');
    showCreate.value = false;
    await loadDepartments();
  } catch (error: any) {
    notify.push(error?.message || '创建失败', 'error');
  }
};

const submitEdit = async () => {
  if (!editTarget.value) return;
  try {
    await updateDepartment(editTarget.value.id, form.value);
    notify.push('部门已更新', 'success');
    showEdit.value = false;
    await loadDepartments();
    if (detail.value?.id === editTarget.value.id) {
      await selectDepartment(editTarget.value.id);
    }
  } catch (error: any) {
    notify.push(error?.message || '更新失败', 'error');
  }
};

const handleDelete = async (dept: Department) => {
  if (!confirm(`确认删除部门：${dept.name}？`)) return;
  try {
    await deleteDepartment(dept.id);
    notify.push('部门已删除', 'success');
    await loadDepartments();
    if (detail.value?.id === dept.id) {
      detail.value = null;
    }
  } catch (error: any) {
    notify.push(error?.message || '删除失败', 'error');
  }
};

const submitApply = async () => {
  if (!applyTarget.value) return;
  try {
    await applyDepartment(applyTarget.value.id, { reason: applyReason.value });
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
    await addDepartmentMembers(adminTarget.value.id, userIds);
    notify.push('成员已添加', 'success');
    showAddMembers.value = false;
    if (detail.value?.id === adminTarget.value.id) {
      await selectDepartment(adminTarget.value.id);
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
    await setDepartmentAdmin(adminTarget.value.id, Number(adminUserId.value));
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
    await removeDepartmentAdmin(adminTarget.value.id, Number(removeAdminUserId.value));
    notify.push('管理员已取消', 'success');
    showRemoveAdmin.value = false;
  } catch (error: any) {
    notify.push(error?.message || '取消失败', 'error');
  }
};

onMounted(loadDepartments);
</script>
