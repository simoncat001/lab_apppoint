<template>
  <div class="page-container">
    <el-card class="hero-card" shadow="never">
      <div class="hero-card__content">
        <div>
          <div class="hero-kicker">Research Collaboration</div>
          <h2>科研协作记录</h2>
          <p>围绕当前项目内的仪器、预约和实验过程沉淀运行笔记、SOP、FAQ、案例和问题记录。</p>
        </div>
        <el-select
          v-model="selectedToolId"
          placeholder="按仪器筛选"
          clearable
          filterable
          style="width: 260px"
        >
          <el-option v-for="tool in tools" :key="tool.id" :label="tool.name" :value="tool.id" />
        </el-select>
      </div>
    </el-card>

    <el-card class="records-card" shadow="never">
      <el-alert
        v-if="!selectedToolId"
        title="请选择具体仪器后新增记录；当前列表展示项目内已有协作记录。"
        type="info"
        :closable="false"
        show-icon
        class="records-card__alert"
      />
      <CollaborationRecordPanel
        :key="selectedToolId || 'all'"
        :tool-id="selectedToolId || undefined"
        :allow-create="!!selectedToolId"
      />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { getTools } from '@/api/tools'
import CollaborationRecordPanel from '@/components/collaboration/CollaborationRecordPanel.vue'
import type { Tool } from '@/types'

const tools = ref<Tool[]>([])
const selectedToolId = ref<number>()

const loadTools = async () => {
  try {
    const result = await getTools({ skip: 0, limit: 1000 })
    tools.value = Array.isArray(result) ? result : []
  } catch (error) {
    ElMessage.error('加载仪器列表失败')
    console.error(error)
  }
}

onMounted(loadTools)
</script>

<style scoped>
.page-container {
  padding: 20px;
}

.hero-card {
  margin-bottom: 16px;
  border: none;
  background:
    radial-gradient(circle at 8% 20%, rgba(20, 184, 166, 0.18), transparent 28%),
    linear-gradient(135deg, #0f172a 0%, #1e3a5f 58%, #0f766e 100%);
  color: #ffffff;
}

.hero-card__content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
}

.hero-kicker {
  margin-bottom: 8px;
  color: rgba(255, 255, 255, 0.68);
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.18em;
  text-transform: uppercase;
}

.hero-card h2 {
  margin: 0;
  font-size: 28px;
}

.hero-card p {
  margin: 10px 0 0;
  color: rgba(255, 255, 255, 0.76);
}

.records-card {
  border: 1px solid #e2e8f0;
}

.records-card__alert {
  margin-bottom: 14px;
}

@media (max-width: 768px) {
  .hero-card__content {
    align-items: stretch;
    flex-direction: column;
  }
}
</style>
