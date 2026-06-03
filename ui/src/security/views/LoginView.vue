<template>
  <div class="login-container">
    <div class="login-form-wrapper">
      <h2 class="login-title">{{ mode === 'login' ? '安全组织登录' : '安全组织注册' }}</h2>
      <p class="muted" style="text-align: center; margin-bottom: 20px;">
        {{ mode === 'login' ? '使用账号进入系统' : '提交账号注册申请' }}
      </p>

      <form class="login-form" @submit.prevent="mode === 'login' ? handleLogin() : handleRegister()">
        <div class="login-form-group">
          <label>用户名</label>
          <input v-model="form.username" class="login-input" placeholder="请输入用户名" />
        </div>
        <div class="login-form-group">
          <label>密码</label>
          <input v-model="form.password" type="password" class="login-input" placeholder="请输入密码" />
        </div>
        <template v-if="mode === 'register'">
          <div class="login-form-group">
            <label>姓名</label>
            <input v-model="form.name" class="login-input" placeholder="可选" />
          </div>
          <div class="login-form-group">
            <label>邮箱</label>
            <input v-model="form.email" class="login-input" placeholder="可选" />
          </div>
          <div class="login-form-group">
            <label>手机号</label>
            <input v-model="form.phone" class="login-input" placeholder="可选" />
          </div>
        </template>

        <button class="login-button" type="submit" :disabled="loading">
          {{ loading ? (mode === 'login' ? '登录中...' : '注册中...') : (mode === 'login' ? '登录' : '注册') }}
        </button>
      </form>

      <div class="login-switch">
        <a href="#" @click.prevent="toggleMode">
          {{ mode === 'login' ? '没有账号？去注册' : '已有账号？去登录' }}
        </a>
      </div>

      <div style="margin-top: 16px; text-align: center; font-size: 12px; color: #6b7280;">
        当前 API：{{ baseUrl }}
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue';
import { useRouter } from 'vue-router';
import { useStaffAuthStore } from '@/security/stores/auth';
import { useNotifyStore } from '@/security/stores/notify';
import { register as registerApi } from '@/security/api/endpoints';

const router = useRouter();
const auth = useStaffAuthStore();
const notify = useNotifyStore();
const loading = ref(false);
const mode = ref<'login' | 'register'>('login');

const baseUrl = import.meta.env.VITE_API_BASE || 'http://localhost:8299';

const form = reactive({
  username: '',
  password: '',
  name: '',
  email: '',
  phone: ''
});

const handleLogin = async () => {
  if (!form.username || !form.password) {
    notify.push('请输入用户名和密码', 'error');
    return;
  }
  loading.value = true;
  try {
    await auth.login({
      username: form.username.trim(),
      password: form.password
    });
    notify.push('登录成功', 'success');
    router.push('/security/dashboard');
  } catch (error: any) {
    notify.push(error?.message || '登录失败', 'error');
  } finally {
    loading.value = false;
  }
};

const handleRegister = async () => {
  if (!form.username || !form.password) {
    notify.push('用户名和密码必填', 'error');
    return;
  }
  loading.value = true;
  try {
    await registerApi({
      username: form.username,
      password: form.password,
      name: form.name || undefined,
      email: form.email || undefined,
      phone: form.phone || undefined
    });
    notify.push('注册申请已提交，请等待管理员审核', 'success');
    mode.value = 'login';
  } catch (error: any) {
    notify.push(error?.message || '注册失败', 'error');
  } finally {
    loading.value = false;
  }
};

const toggleMode = () => {
  mode.value = mode.value === 'login' ? 'register' : 'login';
};
</script>
