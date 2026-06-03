<template>
  <div class="card">
    <div style="display: flex; justify-content: space-between; align-items: center; gap: 12px;">
      <div>
        <h3>用户列表</h3>
        <p style="margin-top: 6px;">仅超级管理员可管理用户。</p>
      </div>
      <button class="button" @click="openCreate">新增用户</button>
    </div>
    <div style="margin-top: 18px; display: flex; gap: 12px; flex-wrap: wrap;">
      <input v-model="keyword" class="input" style="max-width: 220px;" placeholder="搜索用户名" />
      <button class="button ghost" @click="loadUsers">搜索</button>
    </div>
    <table class="table" style="margin-top: 16px;">
      <thead>
        <tr>
          <th>ID</th>
          <th>用户名</th>
          <th>姓名</th>
          <th>邮箱</th>
          <th>状态</th>
          <th>操作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="user in users" :key="user.id">
          <td>{{ user.id }}</td>
          <td>{{ user.username }}</td>
          <td>{{ user.name || '-' }}</td>
          <td>{{ user.email || '-' }}</td>
          <td>{{ userStatusLabel[user.status ?? 1] }}</td>
          <td>
            <div style="display: flex; gap: 8px;">
              <button class="button secondary" @click="openEdit(user)">编辑</button>
              <button class="button" style="background: #c94321;" @click="handleDelete(user)">删除</button>
            </div>
          </td>
        </tr>
        <tr v-if="!users.length">
          <td colspan="6" style="text-align: center; padding: 20px;">暂无用户</td>
        </tr>
      </tbody>
    </table>

    <div style="margin-top: 16px; display: flex; justify-content: space-between; align-items: center;">
      <p>共 {{ total }} 条</p>
      <div style="display: flex; gap: 8px;">
        <button class="button ghost" :disabled="pageNum <= 1" @click="changePage(pageNum - 1)">上一页</button>
        <button class="button ghost" :disabled="pageNum >= totalPages" @click="changePage(pageNum + 1)">下一页</button>
      </div>
    </div>
  </div>

  <ModalShell :open="showCreate" title="新增用户" subtitle="创建系统账号" @close="showCreate = false">
    <label class="field">
      <span>用户名</span>
      <input v-model="form.username" class="input" />
    </label>
    <label class="field">
      <span>密码</span>
      <input v-model="form.password" type="password" class="input" />
    </label>
    <label class="field">
      <span>姓名</span>
      <input v-model="form.name" class="input" />
    </label>
    <label class="field">
      <span>邮箱</span>
      <input v-model="form.email" class="input" />
    </label>
    <label class="field">
      <span>手机号</span>
      <input v-model="form.phone" class="input" />
    </label>
    <label class="field">
      <span>状态</span>
      <select v-model.number="form.status" class="input">
        <option :value="1">正常</option>
        <option :value="0">待审核/禁用</option>
      </select>
    </label>
    <button class="button" @click="submitCreate">保存</button>
  </ModalShell>

  <ModalShell :open="showEdit" title="编辑用户" subtitle="更新用户资料" @close="showEdit = false">
    <label class="field">
      <span>用户名</span>
      <input v-model="form.username" class="input" />
    </label>
    <label class="field">
      <span>新密码（可选）</span>
      <input v-model="form.password" type="password" class="input" />
    </label>
    <label class="field">
      <span>姓名</span>
      <input v-model="form.name" class="input" />
    </label>
    <label class="field">
      <span>邮箱</span>
      <input v-model="form.email" class="input" />
    </label>
    <label class="field">
      <span>手机号</span>
      <input v-model="form.phone" class="input" />
    </label>
    <label class="field">
      <span>状态</span>
      <select v-model.number="form.status" class="input">
        <option :value="1">正常</option>
        <option :value="0">待审核/禁用</option>
      </select>
    </label>
    <button class="button" @click="submitEdit">更新</button>
  </ModalShell>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue';
import type { User } from '@/security/types/models';
import { createUser, deleteUser, fetchUsers, updateUser } from '@/security/api/endpoints';
import { useNotifyStore } from '@/security/stores/notify';
import { userStatusLabel } from '@/security/utils/format';
import ModalShell from '@/security/components/ModalShell.vue';

const notify = useNotifyStore();

const users = ref<User[]>([]);
const total = ref(0);
const totalPages = ref(1);
const pageNum = ref(1);
const pageSize = ref(8);
const keyword = ref('');

const showCreate = ref(false);
const showEdit = ref(false);
const editTarget = ref<User | null>(null);

const form = ref({
  id: 0,
  username: '',
  password: '',
  name: '',
  email: '',
  phone: '',
  status: 1
});

const loadUsers = async () => {
  try {
    const data = await fetchUsers({
      pageNum: pageNum.value,
      size: pageSize.value,
      username: keyword.value || undefined
    });
    const page = data as any;
    users.value = page.records || [];
    total.value = page.total || 0;
    totalPages.value = page.pages || 1;
  } catch (error: any) {
    notify.push(error?.message || '用户加载失败', 'error');
  }
};

const changePage = (page: number) => {
  pageNum.value = page;
  loadUsers();
};

const openCreate = () => {
  form.value = {
    id: 0,
    username: '',
    password: '',
    name: '',
    email: '',
    phone: '',
    status: 1
  };
  showCreate.value = true;
};

const openEdit = (user: User) => {
  editTarget.value = user;
  form.value = {
    id: user.id,
    username: user.username,
    password: '',
    name: user.name || '',
    email: user.email || '',
    phone: user.phone || '',
    status: user.status ?? 1
  };
  showEdit.value = true;
};

const submitCreate = async () => {
  if (!form.value.username || !form.value.password) {
    notify.push('用户名和密码必填', 'error');
    return;
  }
  try {
    await createUser(form.value);
    notify.push('用户已创建', 'success');
    showCreate.value = false;
    await loadUsers();
  } catch (error: any) {
    notify.push(error?.message || '创建失败', 'error');
  }
};

const submitEdit = async () => {
  if (!editTarget.value) return;
  try {
    await updateUser(form.value);
    notify.push('用户已更新', 'success');
    showEdit.value = false;
    await loadUsers();
  } catch (error: any) {
    notify.push(error?.message || '更新失败', 'error');
  }
};

const handleDelete = async (user: User) => {
  if (!confirm(`确认删除用户：${user.username}？`)) return;
  try {
    await deleteUser(user.id);
    notify.push('用户已删除', 'success');
    await loadUsers();
  } catch (error: any) {
    notify.push(error?.message || '删除失败', 'error');
  }
};

onMounted(loadUsers);
</script>

<style scoped>
.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
</style>
