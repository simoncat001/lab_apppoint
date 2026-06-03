<template>
  <div class="page-grid">
    <div class="card">
      <div class="toolbar-row">
        <div>
          <h3>项目列表</h3>
          <p class="muted" style="margin-top: 6px;">按部门筛选项目。</p>
        </div>
        <div class="toolbar-actions">
          <button class="button ghost" @click="loadProjects">刷新</button>
          <button class="button" @click="openCreate">新增项目</button>
        </div>
      </div>

      <div class="filter-row">
        <label class="field">
          <span>所属部门</span>
          <select v-model.number="selectedDepartmentId" class="input" @change="loadProjects">
            <option :value="0">全部部门</option>
            <option v-for="dept in departments" :key="dept.id" :value="dept.id">
              {{ dept.name }}
            </option>
          </select>
        </label>
      </div>

      <table class="table" style="margin-top: 16px;">
        <thead>
          <tr>
            <th>名称</th>
            <th>部门</th>
            <th>对外展示</th>
            <th>描述</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="project in projects" :key="project.id" class="row-click" @click="selectProject(project.id)">
            <td>{{ project.name }}</td>
            <td>{{ project.departmentId }}</td>
            <td>
              <span :class="['badge', project.externalVisible ? 'cool' : '']">
                {{ project.externalVisible ? (project.externalDisplayName || project.name) : '未开放' }}
              </span>
            </td>
            <td class="cell-muted"><span class="text-ellipsis">{{ project.description || '-' }}</span></td>
            <td>
              <div class="table-actions">
                <button class="button ghost" @click.stop="openApply(project)">申请</button>
                <button class="button ghost" @click.stop="openAddMembers(project)">添加成员</button>
                <button class="button ghost" @click.stop="openSetAdmin(project)">设管理员</button>
                <button class="button ghost" @click.stop="openRemoveAdmin(project)">取消管理员</button>
                <button class="button secondary" @click.stop="openEdit(project)">编辑</button>
                <button class="button" style="background: #c94321;" @click.stop="handleDelete(project)">删除</button>
              </div>
            </td>
          </tr>
          <tr v-if="!projects.length">
            <td colspan="5" style="text-align: center; padding: 20px;">暂无项目</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="detail-panel">
      <h3>项目详情</h3>
      <p class="muted" style="margin-top: 6px;">点击左侧项目查看详情。</p>
      <div v-if="detail" style="margin-top: 16px; display: grid; gap: 10px;">
        <div class="pill">名称：{{ detail.name }}</div>
        <div class="pill">成员数：{{ detail.memberCount ?? '-' }}</div>
        <div class="pill">小组数：{{ detail.groupCount ?? '-' }}</div>
        <div class="pill">所属部门：{{ detail.departmentId }}</div>
        <div class="pill">对外展示：{{ detail.externalVisible ? '已开放' : '未开放' }}</div>
        <div v-if="detail.externalVisible" class="pill">对外名称：{{ detail.externalDisplayName || detail.name }}</div>
        <div class="pill">创建时间：{{ formatDateTime(detail.createdTime) }}</div>
        <p class="cell-muted">{{ detail.description || '暂无描述' }}</p>
      </div>
    </div>
  </div>

  <ModalShell :open="showCreate" title="新增项目" subtitle="创建新的部门项目" @close="showCreate = false">
    <label class="field">
      <span>项目名称</span>
      <input v-model="form.name" class="input" />
    </label>
    <label class="field">
      <span>所属部门</span>
      <select v-model.number="form.departmentId" class="input">
        <option disabled :value="0">选择部门</option>
        <option v-for="dept in departments" :key="dept.id" :value="dept.id">
          {{ dept.name }}
        </option>
      </select>
    </label>
    <label class="field">
      <span>描述</span>
      <textarea v-model="form.description" class="input" rows="3" />
    </label>
    <label class="field">
      <span>对外开放</span>
      <select v-model="form.externalVisible" class="input">
        <option :value="false">不开放</option>
        <option :value="true">开放项目名称给外部系统</option>
      </select>
    </label>
    <label v-if="form.externalVisible" class="field">
      <span>对外展示名称</span>
      <input v-model="form.externalDisplayName" class="input" placeholder="外部系统看到的项目名称" />
    </label>
    <button class="button" @click="submitCreate">保存</button>
  </ModalShell>

  <ModalShell :open="showEdit" title="编辑项目" subtitle="更新项目信息" @close="showEdit = false">
    <label class="field">
      <span>项目名称</span>
      <input v-model="form.name" class="input" />
    </label>
    <label class="field">
      <span>描述</span>
      <textarea v-model="form.description" class="input" rows="3" />
    </label>
    <label class="field">
      <span>对外开放</span>
      <select v-model="form.externalVisible" class="input">
        <option :value="false">不开放</option>
        <option :value="true">开放项目名称给外部系统</option>
      </select>
    </label>
    <label v-if="form.externalVisible" class="field">
      <span>对外展示名称</span>
      <input v-model="form.externalDisplayName" class="input" placeholder="外部系统看到的项目名称" />
    </label>
    <button class="button" @click="submitEdit">更新</button>
  </ModalShell>

  <ModalShell :open="showApply" title="申请加入项目" subtitle="填写加入理由" @close="showApply = false">
    <label class="field">
      <span>申请理由</span>
      <textarea v-model="applyReason" class="input" rows="3" />
    </label>
    <button class="button" @click="submitApply">提交申请</button>
  </ModalShell>

  <ModalShell :open="showAddMembers" title="添加项目成员" subtitle="输入用户ID，逗号分隔" @close="showAddMembers = false">
    <label class="field">
      <span>用户 ID 列表</span>
      <input v-model="memberUserIds" class="input" placeholder="例如 12,18,25" />
    </label>
    <button class="button" @click="submitAddMembers">确认添加</button>
  </ModalShell>

  <ModalShell :open="showSetAdmin" title="设置项目管理员" subtitle="输入用户 ID" @close="showSetAdmin = false">
    <label class="field">
      <span>用户 ID</span>
      <input v-model="adminUserId" class="input" placeholder="请输入用户ID" />
    </label>
    <button class="button" @click="submitSetAdmin">确认设置</button>
  </ModalShell>

  <ModalShell :open="showRemoveAdmin" title="取消项目管理员" subtitle="输入用户 ID" @close="showRemoveAdmin = false">
    <label class="field">
      <span>用户 ID</span>
      <input v-model="removeAdminUserId" class="input" placeholder="请输入用户ID" />
    </label>
    <button class="button secondary" @click="submitRemoveAdmin">确认取消</button>
  </ModalShell>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue';
import type { Department, Project, ProjectDetail } from '@/security/types/models';
import {
  addProjectMembers,
  applyProject,
  createProject,
  deleteProject,
  fetchDepartments,
  fetchProjectDetail,
  fetchProjects,
  removeProjectAdmin,
  setProjectAdmin,
  updateProject
} from '@/security/api/endpoints';
import { useNotifyStore } from '@/security/stores/notify';
import { formatDateTime } from '@/security/utils/format';
import ModalShell from '@/security/components/ModalShell.vue';

const notify = useNotifyStore();
const departments = ref<Department[]>([]);
const projects = ref<Project[]>([]);
const detail = ref<ProjectDetail | null>(null);

const selectedDepartmentId = ref(0);
const showCreate = ref(false);
const showEdit = ref(false);
const showApply = ref(false);
const showAddMembers = ref(false);
const showSetAdmin = ref(false);
const showRemoveAdmin = ref(false);
const applyTarget = ref<Project | null>(null);
const editTarget = ref<Project | null>(null);
const applyReason = ref('');
const memberUserIds = ref('');
const adminUserId = ref('');
const removeAdminUserId = ref('');
const adminTarget = ref<Project | null>(null);

const form = ref({
  name: '',
  description: '',
  departmentId: 0,
  externalVisible: false,
  externalDisplayName: ''
});

const loadDepartments = async () => {
  try {
    departments.value = (await fetchDepartments()) as Department[];
  } catch (error: any) {
    notify.push(error?.message || '部门加载失败', 'error');
  }
};

const loadProjects = async () => {
  try {
    const deptId = selectedDepartmentId.value || undefined;
    projects.value = (await fetchProjects(deptId)) as Project[];
  } catch (error: any) {
    notify.push(error?.message || '项目列表加载失败', 'error');
  }
};

const selectProject = async (id: number) => {
  try {
    detail.value = (await fetchProjectDetail(id)) as ProjectDetail;
  } catch (error: any) {
    notify.push(error?.message || '项目详情加载失败', 'error');
  }
};

const openCreate = () => {
  form.value = {
    name: '',
    description: '',
    departmentId: departments.value[0]?.id || 0,
    externalVisible: false,
    externalDisplayName: ''
  };
  showCreate.value = true;
};

const openEdit = (project: Project) => {
  form.value = {
    name: project.name,
    description: project.description || '',
    departmentId: project.departmentId,
    externalVisible: Boolean(project.externalVisible),
    externalDisplayName: project.externalDisplayName || ''
  };
  editTarget.value = project;
  showEdit.value = true;
};

const openApply = (project: Project) => {
  applyTarget.value = project;
  applyReason.value = '';
  showApply.value = true;
};

const openAddMembers = (project: Project) => {
  adminTarget.value = project;
  memberUserIds.value = '';
  showAddMembers.value = true;
};

const openSetAdmin = (project: Project) => {
  adminTarget.value = project;
  adminUserId.value = '';
  showSetAdmin.value = true;
};

const openRemoveAdmin = (project: Project) => {
  adminTarget.value = project;
  removeAdminUserId.value = '';
  showRemoveAdmin.value = true;
};

const submitCreate = async () => {
  if (!form.value.name || !form.value.departmentId) {
    notify.push('请完善项目信息', 'error');
    return;
  }
  if (form.value.externalVisible && !form.value.externalDisplayName.trim()) {
    notify.push('开启对外开放时必须填写对外展示名称', 'error');
    return;
  }
  try {
    await createProject({
      name: form.value.name.trim(),
      description: form.value.description,
      departmentId: form.value.departmentId,
      externalVisible: form.value.externalVisible,
      externalDisplayName: form.value.externalVisible ? form.value.externalDisplayName.trim() : undefined
    });
    notify.push('项目已创建', 'success');
    showCreate.value = false;
    await loadProjects();
  } catch (error: any) {
    notify.push(error?.message || '创建失败', 'error');
  }
};

const submitEdit = async () => {
  if (!editTarget.value) return;
  if (form.value.externalVisible && !form.value.externalDisplayName.trim()) {
    notify.push('开启对外开放时必须填写对外展示名称', 'error');
    return;
  }
  try {
    await updateProject(editTarget.value.id, {
      name: form.value.name.trim(),
      description: form.value.description,
      externalVisible: form.value.externalVisible,
      externalDisplayName: form.value.externalVisible ? form.value.externalDisplayName.trim() : ''
    });
    notify.push('项目已更新', 'success');
    showEdit.value = false;
    await loadProjects();
    if (detail.value?.id === editTarget.value.id) {
      await selectProject(editTarget.value.id);
    }
  } catch (error: any) {
    notify.push(error?.message || '更新失败', 'error');
  }
};

const handleDelete = async (project: Project) => {
  if (!confirm(`确认删除项目：${project.name}？`)) return;
  try {
    await deleteProject(project.id);
    notify.push('项目已删除', 'success');
    await loadProjects();
    if (detail.value?.id === project.id) {
      detail.value = null;
    }
  } catch (error: any) {
    notify.push(error?.message || '删除失败', 'error');
  }
};

const submitApply = async () => {
  if (!applyTarget.value) return;
  try {
    await applyProject(applyTarget.value.id, { reason: applyReason.value });
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
    await addProjectMembers(adminTarget.value.id, userIds);
    notify.push('成员已添加', 'success');
    showAddMembers.value = false;
    if (detail.value?.id === adminTarget.value.id) {
      await selectProject(adminTarget.value.id);
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
    await setProjectAdmin(adminTarget.value.id, Number(adminUserId.value));
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
    await removeProjectAdmin(adminTarget.value.id, Number(removeAdminUserId.value));
    notify.push('管理员已取消', 'success');
    showRemoveAdmin.value = false;
  } catch (error: any) {
    notify.push(error?.message || '取消失败', 'error');
  }
};

onMounted(async () => {
  await loadDepartments();
  await loadProjects();
});
</script>
