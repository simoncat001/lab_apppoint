<template>
  <div class="page-container">
    <el-card shadow="never" class="header-card">
      <el-row :gutter="16" align="middle">
        <el-col :span="12">
          <el-space>
            <el-button :icon="ArrowLeft" @click="router.back()">返回</el-button>
            <el-text tag="b">任务详情</el-text>
          </el-space>
        </el-col>
        <el-col :span="12" style="text-align:right">
          <el-space>
            <el-button :icon="Refresh" @click="load" :loading="loading">刷新</el-button>
          </el-space>
        </el-col>
      </el-row>
    </el-card>

    <el-card shadow="never" class="content-card" v-loading="loading">
      <el-descriptions v-if="task" :column="2" border>
        <el-descriptions-item label="ID">{{ task.id }}</el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag v-if="task.resolved" type="success">已解决</el-tag>
          <el-tag v-else-if="task.cancelled" type="info">已取消</el-tag>
          <el-tag v-else type="warning">待处理</el-tag>
        </el-descriptions-item>

        <el-descriptions-item label="紧急程度">{{ task.urgency }}</el-descriptions-item>
  <el-descriptions-item label="仪器">{{ task.tool?.name || '-' }}</el-descriptions-item>

        <el-descriptions-item label="创建者">{{ task.creator?.username || '-' }}</el-descriptions-item>
        <el-descriptions-item label="创建时间">{{ formatDateTime(task.creation_time) }}</el-descriptions-item>

        <el-descriptions-item label="问题描述" :span="2">
          <div style="white-space: pre-wrap">{{ task.problem_description || '-' }}</div>
        </el-descriptions-item>

        <el-descriptions-item label="进展说明" :span="2">
          <div style="white-space: pre-wrap">{{ task.progress_description || '-' }}</div>
        </el-descriptions-item>

        <el-descriptions-item label="解决说明" :span="2">
          <div style="white-space: pre-wrap">{{ task.resolution_description || '-' }}</div>
        </el-descriptions-item>
      </el-descriptions>

      <el-empty v-else description="未找到任务或尚未加载" />

      <div style="margin-top: 12px">
        <el-alert
          type="info"
          show-icon
          :closable="false"
          title="说明"
          description="当前仓库前端路由引用了 TaskDetail.vue，但文件缺失会导致 Vite 启动报错。此页面为最小可用实现，用于解除构建阻塞并支持后续完善。"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft, Refresh } from '@element-plus/icons-vue'

import { getTask } from '@/api/tasks'
import type { Task } from '@/types'
import { formatDateTime } from '@/utils/helpers'

const route = useRoute()
const router = useRouter()

const loading = ref(false)
const task = ref<Task | null>(null)

async function load() {
  const id = Number(route.params.id)
  if (!id || Number.isNaN(id)) {
    task.value = null
    return
  }

  loading.value = true
  try {
    // Backend may not support this endpoint in all envs; fallback to empty state.
    const res = await getTask(id)
    task.value = (res as any)?.data ?? null
  } catch (e) {
    task.value = null
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.page-container {
  padding: 16px;
}
.header-card {
  margin-bottom: 16px;
}
</style>
