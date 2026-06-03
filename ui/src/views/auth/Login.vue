<template>
  <div class="login-container">
    <el-card class="login-card">
      <h1 class="title">登录</h1>
      <p class="subtitle">实验室预约系统</p>

      <el-radio-group v-model="authSource" class="auth-source-switch">
        <el-radio-button value="internal">内部员工</el-radio-button>
        <el-radio-button value="external">外部用户</el-radio-button>
      </el-radio-group>

      <div class="auth-source-hint">
        {{ authSource === 'internal' ? '内部员工账号由统一认证微服务校验' : '外部用户使用预约系统本地账号登录' }}
      </div>

      <el-form
        ref="formRef"
        :model="loginForm"
        :rules="rules"
        class="login-form"
        @submit.prevent="handleLogin"
      >
        <el-form-item prop="username">
          <el-input
            v-model="loginForm.username"
            :placeholder="authSource === 'internal' ? '工号/用户名' : '用户名'"
            size="large"
            prefix-icon="User"
          />
        </el-form-item>

        <el-form-item prop="password">
          <el-input
            v-model="loginForm.password"
            type="password"
            placeholder="密码"
            size="large"
            prefix-icon="Lock"
            show-password
            @keyup.enter="handleLogin"
          />
        </el-form-item>
      </el-form>

      <el-button
        type="primary"
        size="large"
        class="login-button"
        :loading="loading"
        @click="handleLogin"
      >
        登录
      </el-button>
      <div class="register-link">
        <router-link to="/register">没有账号？立即注册</router-link>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const formRef = ref<FormInstance>()
const loading = ref(false)
const authSource = ref<'internal' | 'external'>('external')

const loginForm = reactive({
  username: '',
  password: '',
})

const rules: FormRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

const handleLogin = async () => {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    loading.value = true
    try {
      await authStore.login({
        ...loginForm,
        auth_source: authSource.value,
      })
      ElMessage.success('登录成功')

      const redirect = (route.query.redirect as string) || '/'
      router.push(redirect)
    } catch (error: any) {
      const status = error?.response?.status
      const detail = error?.response?.data?.detail

      if (status === 502 && authSource.value === 'internal') {
        ElMessage.error('内部认证服务不可用，请先启动 security-server（8299）或切换为外部用户登录')
        return
      }
      if (status === 502) {
        ElMessage.error('预约系统后端不可用，请检查 backend 服务（8000）')
        return
      }

      ElMessage.error(detail || '登录失败')
    } finally {
      loading.value = false
    }
  })
}
</script>

<style scoped>
.login-container {
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(120deg, #a1c4fd 0%, #c2e9fb 100%);
}

.login-card {
  width: 400px;
  padding: 40px;
}

.title {
  text-align: center;
  font-size: 32px;
  font-weight: bold;
  color: #409eff;
  margin-bottom: 8px;
}
.register-link {
  text-align: center;
  margin-top: 10px;
}
.register-link a {
  color: #409eff;
  text-decoration: none;
  font-size: 14px;
}
.subtitle {
  text-align: center;
  color: #909399;
  margin-bottom: 40px;
}

.auth-source-switch {
  display: flex;
  justify-content: center;
  margin-bottom: 12px;
}

.auth-source-hint {
  text-align: center;
  color: #606266;
  font-size: 13px;
  margin-bottom: 8px;
}

.login-form {
  margin-top: 12px;
}

.login-button {
  width: 100%;
  margin-top: 20px;
}

</style>
