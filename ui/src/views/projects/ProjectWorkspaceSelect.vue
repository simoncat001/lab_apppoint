<template>
  <div class="project-context-page">
    <el-card class="selector-card" shadow="never">
      <template #header>
        <div class="card-header">
          <span>选择当前项目</span>
          <el-button text @click="loadProjects" :loading="loading">刷新</el-button>
        </div>
      </template>

      <p class="hint">
        进入系统后，预约、仪器启停、使用记录、计费和配置管理都将在当前项目下进行。
      </p>

      <el-form label-width="90px">
        <el-form-item label="当前项目">
          <el-select
            v-model="selectedProjectId"
            placeholder="请选择项目"
            filterable
            clearable
            style="width: 100%"
            :loading="loading"
          >
            <el-option
              v-for="project in projects"
              :key="project.id"
              :label="getProjectDisplayName(project)"
              :value="project.id"
            />
          </el-select>
        </el-form-item>
      </el-form>

      <el-empty
        v-if="!loading && projects.length === 0"
        description="暂无可用项目，请先在个人主页申请项目预约权限或联系管理员"
      />

      <div class="actions">
        <el-button @click="goProfile">去个人主页</el-button>
        <el-button type="primary" :disabled="!selectedProjectId" @click="confirmProject">
          进入项目工作区
        </el-button>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useProjectContextStore } from '@/stores/project-context'
import { getProjectDisplayName } from '@/utils/project'

const router = useRouter()
const route = useRoute()
const projectStore = useProjectContextStore()

const selectedProjectId = ref<number | null>(projectStore.currentProjectId)
const projects = computed(() => projectStore.projects)
const loading = computed(() => projectStore.loading)

const loadProjects = async () => {
  try {
    await projectStore.loadProjects(true)
    if (!selectedProjectId.value && projectStore.currentProjectId) {
      selectedProjectId.value = projectStore.currentProjectId
    }
  } catch (error) {
    console.error(error)
    ElMessage.error('加载项目列表失败')
  }
}

const confirmProject = () => {
  if (!selectedProjectId.value) {
    ElMessage.warning('请选择项目')
    return
  }
  const project = projects.value.find((item) => item.id === selectedProjectId.value)
  if (!project) {
    ElMessage.error('项目不存在或无权限访问')
    return
  }
  projectStore.setCurrentProject(project)
  ElMessage.success(`当前项目已设置为：${getProjectDisplayName(project)}`)
  const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : '/dashboard'
  router.push(redirect)
}

const goProfile = () => {
  router.push('/profile')
}

onMounted(async () => {
  await loadProjects()
  if (!selectedProjectId.value && projectStore.currentProjectId) {
    selectedProjectId.value = projectStore.currentProjectId
  }
})
</script>

<style scoped>
.project-context-page {
  min-height: calc(100vh - 140px);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
}

.selector-card {
  width: min(720px, 100%);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.hint {
  margin: 0 0 16px;
  color: #606266;
  line-height: 1.6;
}

.actions {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
</style>
