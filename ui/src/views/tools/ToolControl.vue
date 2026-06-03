<template>
    <div class="tool-control-container">
        <el-row :gutter="20">
            <!-- 左侧仪器列表 -->
            <el-col :span="6">
                <el-card class="tool-list-card">
                    <template #header>
                        <div class="card-header">
                            <div class="current-project">
                                <span class="project-label">当前项目</span>
                                <el-tag type="info" effect="plain">{{ currentProjectDisplayName }}</el-tag>
                            </div>
                            <span>仪器列表</span>
                            <el-input
                                v-model="searchQuery"
                                placeholder="搜索仪器..."
                                :prefix-icon="Search"
                                clearable
                                class="search-input"
                                :disabled="!currentProjectId"
                            />
                        </div>
                    </template>
                    <div class="tool-list" v-if="currentProjectId">
                        <div
                            v-for="tool in filteredTools"
                            :key="tool.id"
                            class="tool-item"
                            :class="{ active: selectedTool?.id === tool.id }"
                            @click="selectTool(tool)"
                        >
                            <div class="tool-name">{{ tool.name }}</div>
                            <div class="tool-status">
                                <el-tag size="small" :type="tool.operational ? 'success' : 'danger'">
                                    {{ tool.operational ? '正常' : '维护中' }}
                                </el-tag>
                            </div>
                        </div>
                    </div>
                    <el-empty v-else description="请先在页面顶部选择当前项目" />
                </el-card>
            </el-col>

            <!-- 右侧控制面板 -->
            <el-col :span="18">
                <el-card v-if="selectedTool" class="control-panel-card">
                    <template #header>
                        <div class="panel-header">
                            <h2>{{ selectedTool.name }}</h2>
                            <el-tag :type="isToolInUse ? 'warning' : 'success'" size="large">
                                {{ isToolInUse ? '使用中' : '空闲' }}
                            </el-tag>
                        </div>
                    </template>

                    <div class="tool-info">
                        <el-descriptions :column="2" border>
                            <el-descriptions-item label="位置">{{
                                selectedTool.location || '未设置'
                            }}</el-descriptions-item>
                            <el-descriptions-item label="联系电话">{{
                                selectedTool.phone_number || '未设置'
                            }}</el-descriptions-item>
                            <el-descriptions-item label="描述" :span="2">{{
                                selectedTool.description || '暂无描述'
                            }}</el-descriptions-item>
                        </el-descriptions>
                    </div>

                    <div class="control-actions">
                        <div v-if="!isToolInUse" class="enable-section">
                            <h3>开始使用</h3>
                            <el-form :model="enableForm" label-width="100px">
                                <el-form-item label="当前项目">
                                    <el-tag>{{ currentProjectDisplayName }}</el-tag>
                                </el-form-item>
                                <el-form-item label="备注">
                                    <el-input v-model="enableForm.note" type="textarea" :rows="3" />
                                </el-form-item>
                                <el-form-item>
                                    <el-button type="primary" @click="handleEnableTool" :loading="loading">
                                        启用仪器
                                    </el-button>
                                </el-form-item>
                            </el-form>
                        </div>

                        <div v-else class="disable-section">
                            <h3>结束使用</h3>
                            <el-form :model="disableForm" label-width="100px">
                                <el-form-item label="备注">
                                    <el-input v-model="disableForm.note" type="textarea" :rows="3" />
                                </el-form-item>
                                <el-form-item>
                                    <el-button type="danger" @click="handleDisableTool" :loading="loading">
                                        结束使用
                                    </el-button>
                                </el-form-item>
                            </el-form>
                        </div>
                    </div>
                </el-card>
                <el-empty v-else :description="emptyDescription" />
            </el-col>
        </el-row>
    </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Search } from '@element-plus/icons-vue'
import { getTools, getToolStatus, enableTool, disableTool } from '@/api/tools'
import { getCurrentUser } from '@/api/users'
import { useProjectContextStore } from '@/stores/project-context'
import type { Tool, User } from '@/types'

const projectContextStore = useProjectContextStore()
const tools = ref<Tool[]>([])
const currentUser = ref<User | null>(null)
const selectedTool = ref<Tool | null>(null)
const searchQuery = ref('')
const isToolInUse = ref(false)
const loading = ref(false)

const enableForm = ref({
    note: '',
})

const disableForm = ref({
    note: '',
})

const currentProjectId = computed(() => projectContextStore.currentProjectId)

const currentProjectDisplayName = computed(() => {
    if (projectContextStore.currentProjectName) return projectContextStore.currentProjectName
    if (projectContextStore.currentProjectId) return `项目 #${projectContextStore.currentProjectId}`
    return '未选择当前项目'
})

const emptyDescription = computed(() => (currentProjectId.value ? '请选择一个仪器' : '请先在页面顶部选择当前项目'))

const resetSelectedTool = () => {
    selectedTool.value = null
    isToolInUse.value = false
}

const loadTools = async () => {
    if (!currentProjectId.value) {
        tools.value = []
        resetSelectedTool()
        return
    }

    tools.value = await getTools({ limit: 1000, visible_only: true })
}

watch(currentProjectId, async () => {
    resetSelectedTool()
    await loadTools()
})

// 过滤仪器列表
const filteredTools = computed(() => {
    if (!searchQuery.value) return tools.value
    const query = searchQuery.value.toLowerCase()
    return tools.value.filter(
        (tool) =>
            tool.name.toLowerCase().includes(query) ||
            (tool.description && tool.description.toLowerCase().includes(query)),
    )
})

// 初始化数据
onMounted(async () => {
    try {
        projectContextStore.hydrate()
        await projectContextStore.ensureProjectSelected()

        const [toolsRes, userRes] = await Promise.all([
            currentProjectId.value ? getTools({ limit: 1000, visible_only: true }) : Promise.resolve([]),
            getCurrentUser(),
        ])
        tools.value = toolsRes
        currentUser.value = userRes as unknown as User
    } catch (error) {
        console.error('Failed to load initial data:', error)
        ElMessage.error('加载数据失败')
    }
})

// 选择仪器
const selectTool = async (tool: Tool) => {
    selectedTool.value = tool
    await checkToolStatus()
}

// 检查仪器状态
const checkToolStatus = async () => {
    if (!selectedTool.value) return
    try {
        isToolInUse.value = await getToolStatus(selectedTool.value.id)
    } catch (error) {
        console.error('Failed to check tool status:', error)
    }
}

// 启用仪器
const handleEnableTool = async () => {
    if (!selectedTool.value || !currentUser.value) return
    const projectId = currentProjectId.value
    if (!projectId) {
        ElMessage.warning('请先在页面顶部选择当前项目')
        return
    }

    loading.value = true
    try {
        await enableTool(selectedTool.value.id, {
            user_id: currentUser.value.id,
            project_id: projectId,
            note: enableForm.value.note,
        })
        ElMessage.success('仪器已启用')
        enableForm.value.note = '' // 清空备注
        await checkToolStatus()
    } catch (error: any) {
        ElMessage.error(error.response?.data?.detail || '启用失败')
    } finally {
        loading.value = false
    }
}

// 禁用仪器
const handleDisableTool = async () => {
    if (!selectedTool.value) return

    loading.value = true
    try {
        await disableTool(selectedTool.value.id, {
            note: disableForm.value.note,
        })
        ElMessage.success('仪器使用已结束')
        disableForm.value.note = '' // 清空备注
        await checkToolStatus()
    } catch (error: any) {
        ElMessage.error(error.response?.data?.detail || '操作失败')
    } finally {
        loading.value = false
    }
}
</script>

<style scoped>
.tool-control-container {
    padding: 20px;
    height: calc(100vh - 84px);
}

.tool-list-card {
    height: 100%;
    display: flex;
    flex-direction: column;
}

.tool-list-card :deep(.el-card__body) {
    flex: 1;
    overflow-y: auto;
    padding: 0;
}

.card-header {
    display: flex;
    flex-direction: column;
    gap: 10px;
}

.current-project {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
}

.project-label {
    color: #606266;
    font-size: 14px;
    white-space: nowrap;
}

.search-input {
    width: 100%;
}

.tool-list {
    display: flex;
    flex-direction: column;
}

.tool-item {
    padding: 15px;
    border-bottom: 1px solid #eee;
    cursor: pointer;
    transition: background-color 0.3s;
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.tool-item:hover {
    background-color: #f5f7fa;
}

.tool-item.active {
    background-color: #e6f7ff;
    border-right: 3px solid #409eff;
}

.tool-name {
    font-weight: 500;
}

.control-panel-card {
    height: 100%;
}

.panel-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.tool-info {
    margin-bottom: 30px;
}

.control-actions {
    padding: 20px;
    background-color: #f8f9fa;
    border-radius: 4px;
}

.enable-section,
.disable-section {
    max-width: 600px;
    margin: 0 auto;
}

h3 {
    margin-bottom: 20px;
    color: #303133;
    text-align: center;
}
</style>
