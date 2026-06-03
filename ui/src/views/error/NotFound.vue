<template>
  <div class="page-container">
    <h2>404 - 页面不存在</h2>
    <p>抱歉，您访问的页面不存在。</p>
    <el-button type="primary" @click="goHome">返回首页</el-button>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'

const router = useRouter()

const goHome = () => {
  router.push('/')
}
</script>

<style scoped>
.page-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  padding: 40px;
}

h2 {
  font-size: 48px;
  color: #909399;
  margin-bottom: 20px;
}

p {
  font-size: 18px;
  color: #606266;
  margin-bottom: 30px;
}
</style>
