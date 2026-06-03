<template>
  <div class="page-container">
    <!-- 仪器基本信息 -->
    <el-card v-loading="loading" class="info-card" shadow="never">
      <template #header>
        <div class="card-header">
          <span class="title">
            <el-icon><Tools /></el-icon>
            仪器详情
          </span>
          <el-space>
            <el-button v-if="canManageTools" type="primary" :icon="Edit" @click="handleEdit">
              编辑仪器
            </el-button>
            <el-button v-if="canManageTools" @click="openCategoryDialog">
              管理分类
            </el-button>
            <el-button v-if="canManageTools" @click="openTagDialog">
              管理标签
            </el-button>
            <el-button :icon="Back" @click="handleBack">
              返回列表
            </el-button>
          </el-space>
        </div>
      </template>

      <!-- 仪器图片 -->
      <div class="tool-image-section">
        <div class="tool-image-section__header">
          <span>仪器图片</span>
          <el-tag effect="plain" type="info">{{ toolImages.length }} 张</el-tag>
        </div>
        <div v-if="toolImages.length" class="tool-image-grid">
          <el-image
            v-for="(item, index) in toolImages"
            :key="item.id || item.path"
            :src="getToolImageUrl(item.path) ?? undefined"
            fit="cover"
            :preview-src-list="toolPreviewUrls"
            :initial-index="index"
            class="tool-image"
          />
        </div>
        <el-empty v-else description="暂无图片" :image-size="80" />
      </div>

      <el-descriptions :column="2" border>
        <el-descriptions-item label="仪器ID">
          {{ toolDetail.id }}
        </el-descriptions-item>
        <el-descriptions-item label="仪器名称">
          <el-text tag="b" size="large">{{ toolDetail.name }}</el-text>
        </el-descriptions-item>
        <el-descriptions-item label="分类">
          <el-tag v-if="toolDetail.category">{{ toolDetail.category.name }}</el-tag>
          <span v-else>-</span>
        </el-descriptions-item>
        <el-descriptions-item label="标签">
          <el-space wrap>
            <el-tag v-for="tag in toolDetail.tags || []" :key="tag.id">
              {{ tag.name }}
            </el-tag>
            <span v-if="!toolDetail.tags || toolDetail.tags.length === 0">-</span>
          </el-space>
        </el-descriptions-item>
        <el-descriptions-item label="位置">
          {{ toolDetail.location || '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="运行状态">
          <el-tag v-if="toolDetail.operational" type="success">
            <el-icon><CircleCheck /></el-icon> 正常运行
          </el-tag>
          <el-tag v-else type="danger">
            <el-icon><CircleClose /></el-icon> 故障维修
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="可见性">
          <el-tag :type="toolDetail.visible ? 'success' : 'info'">
            {{ toolDetail.visible ? '用户可见' : '已隐藏' }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="需要预约">
          <el-tag :type="toolDetail.requires_reservation ? 'warning' : 'info'">
            {{ toolDetail.requires_reservation ? '必须预约' : '无需预约' }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="仪器管理员" :span="2">
          <el-space v-if="toolAdmins.length" wrap>
            <el-tag v-for="admin in toolAdmins" :key="admin.id" type="success" effect="plain">
              {{ getUserDisplayName(admin) }}
            </el-tag>
          </el-space>
          <el-text v-else type="info">未单独配置，默认由全局管理员管理</el-text>
        </el-descriptions-item>
        <el-descriptions-item label="创建时间">
          {{ toolDetail.created_at ? formatDateTime(toolDetail.created_at) : '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="描述" :span="2">
          <el-text v-if="toolDetail.description" type="info">
            {{ toolDetail.description }}
          </el-text>
          <el-text v-else type="info">无描述</el-text>
        </el-descriptions-item>
      </el-descriptions>
    </el-card>

    <!-- 科研协作记录 -->
    <el-card class="collaboration-card" shadow="never">
      <template #header>
        <div class="card-header">
          <span class="title">
            <el-icon><Document /></el-icon>
            科研协作记录
          </span>
        </div>
      </template>
      <CollaborationRecordPanel v-if="toolDetail.id" :tool-id="toolId" default-record-type="tool_note" />
    </el-card>

    <!-- 当前使用情况 -->
    <el-card class="usage-card" shadow="never">
      <template #header>
        <div class="card-header">
          <span class="title">
            <el-icon><Clock /></el-icon>
            当前使用情况
          </span>
          <el-button :icon="Refresh" @click="loadActiveUsage">
            刷新
          </el-button>
        </div>
      </template>

      <el-alert
        v-if="activeUsage"
        title="仪器使用中"
        type="warning"
        :closable="false"
      >
        <el-descriptions :column="2" border>
          <el-descriptions-item label="使用者">
            {{ activeUsage.user?.username || '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="开始时间">
            {{ formatDateTime(activeUsage.start) }}
          </el-descriptions-item>
          <el-descriptions-item label="项目">
            {{ activeUsage.project?.name || '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="使用时长">
            {{ calculateDuration(activeUsage.start) }}
          </el-descriptions-item>
        </el-descriptions>
      </el-alert>
      <el-empty v-else description="当前无人使用" />
    </el-card>

    <!-- 外部用户权限管理 -->
    <el-card v-if="canManageTools" class="access-card" shadow="never">
      <template #header>
        <div class="card-header">
          <span class="title">
            <el-icon><Lock /></el-icon>
            外部用户访问权限
          </span>
          <el-space>
            <el-switch
              v-model="restrictAccess"
              active-text="受限"
              inactive-text="开放"
              @change="handleRestrictToggle"
            />
            <el-button :icon="Refresh" @click="loadAccessList">刷新</el-button>
          </el-space>
        </div>
      </template>

      <el-alert
        v-if="!restrictAccess"
        title="当前为开放模式，所有已验证的外部用户均可使用此仪器"
        type="info"
        :closable="false"
        show-icon
        style="margin-bottom: 12px"
      />
      <template v-else>
        <el-alert
          title="已开启访问限制，仅下方列表中的用户可以查看和预约此仪器"
          type="warning"
          :closable="false"
          show-icon
          style="margin-bottom: 12px"
        />

        <!-- 添加用户 -->
        <div class="access-add-row">
          <el-select
            v-model="selectedUserId"
            filterable
            remote
            placeholder="搜索用户名..."
            :remote-method="searchUsers"
            :loading="userSearchLoading"
            style="width: 300px"
          >
            <el-option
              v-for="u in userSearchResults"
              :key="u.id"
              :label="`${u.username} (${getUserDisplayName(u)})`"
              :value="u.id"
            />
          </el-select>
          <el-button type="primary" :disabled="!selectedUserId" @click="handleGrantAccess">
            授权
          </el-button>
        </div>

        <!-- 已授权用户列表 -->
        <el-table :data="accessList" v-loading="accessLoading" stripe border style="margin-top: 12px">
          <el-table-column prop="username" label="用户名" width="150" />
          <el-table-column label="姓名" min-width="150">
            <template #default="{ row }">{{ getUserDisplayName(row) }}</template>
          </el-table-column>
          <el-table-column prop="granted_at" label="授权时间" width="180">
            <template #default="{ row }">{{ row.granted_at ? formatDateTime(row.granted_at) : '-' }}</template>
          </el-table-column>
          <el-table-column label="操作" width="100">
            <template #default="{ row }">
              <el-button size="small" type="danger" plain @click="handleRevokeAccess(row)">撤销</el-button>
            </template>
          </el-table-column>
        </el-table>
        <el-empty v-if="!accessList.length && !accessLoading" description="暂无授权用户" />
      </template>
    </el-card>

    <!-- 配置列表 -->
    <el-card class="config-card" shadow="never">
      <template #header>
        <div class="card-header">
          <span class="title">
            <el-icon><Setting /></el-icon>
            仪器配置
          </span>
          <el-button :icon="Refresh" @click="loadConfigurations">
            刷新
          </el-button>
        </div>
      </template>

      <el-table
        v-loading="configLoading"
        :data="configurations"
        stripe
        border
      >
        <el-table-column prop="name" label="配置名称" min-width="150" />
        <el-table-column label="当前设置" min-width="150">
          <template #default="{ row }">
            {{ row.current_setting || '-' }}
          </template>
        </el-table-column>
        <el-table-column label="可用选项" min-width="200">
          <template #default="{ row }">
            <el-tag
              v-for="option in row.configuration_options"
              :key="option.id"
              style="margin-right: 5px"
            >
              {{ option.name }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="颜色标识" width="120">
          <template #default="{ row }">
            <div v-if="row.current_setting_color" class="color-display">
              <div
                class="color-block"
                :style="{ backgroundColor: row.current_setting_color }"
              />
              {{ row.current_setting_color }}
            </div>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column prop="display_order" label="排序" width="80" />
      </el-table>
      <el-empty v-if="!configurations.length && !configLoading" description="暂无配置" />
    </el-card>

    <!-- 相关任务 -->
    <el-card class="task-card" shadow="never">
      <template #header>
        <div class="card-header">
          <span class="title">
            <el-icon><Document /></el-icon>
            相关任务
          </span>
          <el-button :icon="Refresh" @click="loadRelatedTasks">
            刷新
          </el-button>
        </div>
      </template>

      <el-table
        v-loading="taskLoading"
        :data="relatedTasks"
        stripe
        border
      >
        <el-table-column prop="problem_description" label="问题描述" min-width="200" />
        <el-table-column label="紧急程度" width="120">
          <template #default="{ row }">
            <el-tag
              :type="
                row.urgency === 'high'
                  ? 'danger'
                  : row.urgency === 'medium'
                  ? 'warning'
                  : 'info'
              "
            >
              {{ row.urgency === 'high' ? '高' : row.urgency === 'medium' ? '中' : '低' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="120">
          <template #default="{ row }">
            <el-tag
              :type="
                row.status === 'pending'
                  ? 'warning'
                  : row.status === 'in_progress'
                  ? 'primary'
                  : row.status === 'resolved'
                  ? 'success'
                  : 'info'
              "
            >
              {{
                row.status === 'pending'
                  ? '待处理'
                  : row.status === 'in_progress'
                  ? '处理中'
                  : row.status === 'resolved'
                  ? '已解决'
                  : '已取消'
              }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="creator.username" label="创建人" width="120" />
        <el-table-column prop="created_at" label="创建时间" width="180">
          <template #default="{ row }">
            {{ formatDateTime(row.created_at) }}
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-if="!relatedTasks.length && !taskLoading" description="暂无相关任务" />
    </el-card>

    <!-- 编辑对话框 -->
    <el-dialog
      v-model="editDialogVisible"
      title="编辑仪器"
      width="840px"
      @close="resetForm"
    >
      <el-form
        ref="formRef"
        :model="formData"
        :rules="formRules"
        label-width="120px"
      >
        <el-form-item label="仪器名称" prop="name">
          <el-input v-model="formData.name" placeholder="请输入仪器名称" />
        </el-form-item>
        <el-form-item label="分类" prop="category_id">
          <el-select v-model="formData.category_id" placeholder="请选择分类" style="width: 100%">
            <el-option v-for="c in categories" :key="c.id" :label="c.name" :value="c.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="所属项目" prop="project_id">
          <div class="current-project-display">
            <span class="current-project-display__label">当前项目</span>
            <span class="current-project-display__value">{{ currentProjectDisplayName }}</span>
          </div>
          <div class="field-helper">仪器所属项目固定为当前页面所在项目，编辑时不能切换到其他项目。</div>
        </el-form-item>
        <el-form-item label="标签">
          <el-select
            v-model="formData.tag_ids"
            multiple
            collapse-tags
            collapse-tags-tooltip
            clearable
            placeholder="请选择标签"
            style="width: 100%"
          >
            <el-option v-for="t in tags" :key="t.id" :label="t.name" :value="t.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="位置">
          <el-input v-model="formData.location" placeholder="请输入位置" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input
            v-model="formData.description"
            type="textarea"
            :rows="4"
            placeholder="请输入仪器描述"
          />
        </el-form-item>
        <el-form-item label="仪器图片">
          <div class="image-upload-section">
            <el-image
              v-if="toolDetail.image"
              :src="getToolImageUrl(toolDetail.image) ?? undefined"
              fit="contain"
              class="upload-preview-image"
            />
            <div class="image-upload-actions">
              <el-upload
                :auto-upload="true"
                :show-file-list="false"
                :disabled="imageUploading"
                :before-upload="beforeImageUpload"
                :http-request="handleImageUpload"
                accept=".jpg,.jpeg,.png,.gif,.webp"
              >
                <el-button type="primary" size="small" :loading="imageUploading">
                  {{ toolDetail.image ? '更换图片' : '上传图片' }}
                </el-button>
              </el-upload>
              <el-button
                v-if="toolDetail.image"
                type="danger"
                size="small"
                plain
                @click="handleDeleteImage"
              >
                删除图片
              </el-button>
            </div>
          </div>
        </el-form-item>

        <el-divider content-position="left">收费设置</el-divider>
        <div class="form-section-block">
          <el-row :gutter="16" class="pricing-grid">
            <el-col :xs="24" :md="10">
              <div class="field-stack">
                <div class="field-stack__label">收费类型</div>
                <el-select v-model="formData.price_type" placeholder="请选择" style="width: 100%">
                  <el-option label="按次收费（按天限次）" :value="0" />
                  <el-option label="按时收费" :value="1" />
                </el-select>
              </div>
            </el-col>
            <el-col v-if="formData.price_type === 0" :xs="24" :md="7">
              <div class="field-stack">
                <div class="field-stack__label">每次价格</div>
                <el-input-number v-model="formData.price_per_use" :min="0" :precision="2" :step="1" />
              </div>
            </el-col>
            <el-col v-if="formData.price_type === 0" :xs="24" :md="7">
              <div class="field-stack">
                <div class="field-stack__label">每日最多预约次数</div>
                <el-input-number
                  v-model="formData.maximum_reservations_per_day"
                  :min="1"
                  :precision="0"
                  :step="1"
                />
              </div>
            </el-col>
            <el-col v-if="formData.price_type === 1" :xs="24" :md="14">
              <div class="field-stack">
                <div class="field-stack__label">每小时价格</div>
                <el-input-number v-model="formData.price_per_hour" :min="0" :precision="2" :step="1" />
              </div>
            </el-col>
          </el-row>
          <div v-if="formData.price_type === 0" class="count-based-hint">
            按次收费仪器只按日期预约，当天达到上限后，预约日历会直接显示当天不可预约。
          </div>
          <div class="count-based-hint">
            修改收费价格后，该仪器已结束使用记录的费用会自动按新价格重算。
          </div>
        </div>

        <div class="form-section-block">
          <el-row :gutter="16" class="toggle-grid">
            <el-col :xs="24" :md="8">
              <div class="toggle-card">
                <div class="toggle-card__label">运行状态</div>
                <el-switch
                  v-model="formData.operational"
                  active-text="正常"
                  inactive-text="故障"
                />
              </div>
            </el-col>
            <el-col :xs="24" :md="8">
              <div class="toggle-card">
                <div class="toggle-card__label">可见性</div>
                <el-switch
                  v-model="formData.visible"
                  active-text="可见"
                  inactive-text="隐藏"
                />
              </div>
            </el-col>
            <el-col :xs="24" :md="8">
              <div class="toggle-card">
                <div class="toggle-card__label">需要预约</div>
                <el-switch
                  v-model="formData.requires_reservation"
                  active-text="需要"
                  inactive-text="不需要"
                />
              </div>
            </el-col>
            <el-col :xs="24" :md="8">
              <div class="toggle-card">
                <div class="toggle-card__label">外部用户限制</div>
                <el-switch
                  v-model="formData.restrict_external_access"
                  active-text="受限"
                  inactive-text="开放"
                />
              </div>
            </el-col>
          </el-row>
        </div>
      </el-form>
      <template #footer>
        <el-button @click="editDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">
          确定
        </el-button>
      </template>
    </el-dialog>

    <!-- 分类管理对话框 -->
    <el-dialog v-model="categoryDialogVisible" title="仪器分类" width="560px" align-center>
      <div class="category-dialog-panel">
        <div class="category-dialog-panel__intro">
          统一维护仪器分类。新增后可直接用于仪器筛选和仪器详情配置。
        </div>

        <div class="category-create-box">
          <div class="category-create-box__meta">
            <div class="category-create-box__title">新增分类</div>
            <div class="category-create-box__hint">分类名称建议简短明确，便于筛选和统计。</div>
          </div>
          <div class="category-create-box__form">
            <el-input
              v-model="newCategoryName"
              placeholder="输入新的分类名称"
              size="large"
              clearable
              @keyup.enter="addCategory"
            />
            <el-button type="primary" size="large" :disabled="!newCategoryName.trim()" @click="addCategory">
              新增分类
            </el-button>
          </div>
        </div>

        <div class="category-list-header">
          <div class="category-list-header__title">现有分类</div>
          <el-tag effect="plain" type="info">{{ categories.length }} 个</el-tag>
        </div>

        <div v-if="categories.length" class="category-list">
          <div v-for="row in categories" :key="row.id" class="category-list-item">
            <div class="category-list-item__name">{{ row.name }}</div>
            <div class="category-list-item__actions">
              <el-button size="small" @click="editCategory(row)">编辑</el-button>
              <el-button size="small" type="danger" plain @click="deleteCategory(row)">删除</el-button>
            </div>
          </div>
        </div>
        <el-empty v-else description="暂无分类，先创建一个分类" />
      </div>
    </el-dialog>

    <!-- 标签管理对话框 -->
    <el-dialog v-model="tagDialogVisible" title="仪器标签" width="560px" align-center>
      <div class="category-dialog-panel">
        <div class="category-dialog-panel__intro">
          统一维护仪器标签。标签可用于列表筛选、详情展示和后续统计维度。
        </div>

        <div class="category-create-box">
          <div class="category-create-box__meta">
            <div class="category-create-box__title">新增标签</div>
            <div class="category-create-box__hint">标签名称建议简短明确，例如“高通量”“精密测试”。</div>
          </div>
          <div class="category-create-box__form">
            <el-input
              v-model="newTagName"
              placeholder="输入新的标签名称"
              size="large"
              clearable
              @keyup.enter="addTag"
            />
            <el-button type="primary" size="large" :disabled="!newTagName.trim()" @click="addTag">
              新增标签
            </el-button>
          </div>
        </div>

        <div class="category-list-header">
          <div class="category-list-header__title">现有标签</div>
          <el-tag effect="plain" type="info">{{ tags.length }} 个</el-tag>
        </div>

        <div v-if="tags.length" class="category-list">
          <div v-for="row in tags" :key="row.id" class="category-list-item">
            <div class="category-list-item__name">{{ row.name }}</div>
            <div class="category-list-item__actions">
              <el-button size="small" @click="editTag(row)">编辑</el-button>
              <el-button size="small" type="danger" plain @click="deleteTag(row)">删除</el-button>
            </div>
          </div>
        </div>
        <el-empty v-else description="暂无标签，先创建一个标签" />
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules, type UploadRequestOptions } from 'element-plus'
import {
  Tools,
  Edit,
  Back,
  Refresh,
  Clock,
  Setting,
  Document,
  CircleCheck,
  CircleClose,
  Lock,
} from '@element-plus/icons-vue'
import {
  getTool,
  updateTool,
  getToolCategories,
  getToolTags,
  createToolCategory,
  updateToolCategory,
  deleteToolCategory,
  createToolTag,
  updateToolTag,
  deleteToolTag,
  uploadToolImage,
  deleteToolImage,
  getToolImages,
  getToolImageUrl,
  getToolImagePreviewUrls,
  getToolAdmins,
  getToolAccess,
  grantToolAccess,
  revokeToolAccess,
} from '@/api/tools'
import { getUsers } from '@/api/users'
import { getToolActiveUsage } from '@/api/usage-events'
import { getToolConfigurations } from '@/api/configurations'
import { getTasks } from '@/api/tasks'
import type { Tool, User, UsageEvent, Configuration, Task, ToolCategory, ToolTag, ToolUserAccess, ToolAdmin } from '@/types'
import { formatDateTime } from '@/utils/helpers'
import { getUserDisplayName } from '@/utils/user'
import dayjs from 'dayjs'
import { useAuthStore } from '@/stores/auth'
import { useProjectContextStore } from '@/stores/project-context'
import CollaborationRecordPanel from '@/components/collaboration/CollaborationRecordPanel.vue'

const route = useRoute()
const router = useRouter()
const toolId = Number(route.params.id)
const authStore = useAuthStore()
const projectContextStore = useProjectContextStore()
const canManageTools = computed(() => authStore.isStaff())

// 仪器详情
const loading = ref(false)
const toolDetail = ref<Partial<Tool>>({})
const toolImages = computed(() => getToolImages(toolDetail.value))
const toolPreviewUrls = computed(() => getToolImagePreviewUrls(toolDetail.value))
const categories = ref<ToolCategory[]>([])
const tags = ref<ToolTag[]>([])
const toolAdmins = ref<ToolAdmin[]>([])

// 当前使用情况
const activeUsage = ref<UsageEvent | null>(null)

// 配置列表
const configLoading = ref(false)
const configurations = ref<Configuration[]>([])

// 相关任务
const taskLoading = ref(false)
const relatedTasks = ref<Task[]>([])

// 编辑对话框
const editDialogVisible = ref(false)
const submitting = ref(false)
const imageUploading = ref(false)

// 表单
const formRef = ref<FormInstance>()
const formData = reactive<Partial<Tool>>({
  name: '',
  category_id: undefined,
  project_id: projectContextStore.currentProjectId ?? undefined,
  tag_ids: [],
  location: '',
  description: '',
  operational: true,
  visible: true,
  requires_reservation: false,
  price_type: 1,
  price_per_use: 0,
  price_per_hour: 0,
  maximum_reservations_per_day: undefined,
  restrict_external_access: false,
})

const formRules: FormRules = {
  name: [{ required: true, message: '请输入仪器名称', trigger: 'blur' }],
  category_id: [{ required: true, message: '请选择分类', trigger: 'change' }],
  project_id: [{ required: true, message: '请先选择当前项目', trigger: 'change' }]
}

const currentProjectDisplayName = computed(() => {
  if (projectContextStore.currentProjectName) return projectContextStore.currentProjectName
  if (projectContextStore.currentProjectId) return `项目 #${projectContextStore.currentProjectId}`
  return '未选择当前项目'
})

const ensureCurrentProjectSelected = () => {
  const currentProjectId = projectContextStore.currentProjectId
  if (!currentProjectId) {
    ElMessage.warning('请先在页面顶部选择当前项目')
    return false
  }
  formData.project_id = currentProjectId
  return true
}

// 加载仪器详情
const loadToolDetail = async () => {
  loading.value = true
  try {
    const response = await getTool(toolId)
    toolDetail.value = response
  } catch (error) {
    ElMessage.error('加载仪器详情失败')
    console.error(error)
  } finally {
    loading.value = false
  }
}

const loadCategories = async () => {
  try {
    categories.value = await getToolCategories()
  } catch (error) {
    console.error(error)
  }
}

const loadTags = async () => {
  try {
    tags.value = await getToolTags()
  } catch (error) {
    console.error(error)
  }
}

const loadToolAdmins = async () => {
  try {
    toolAdmins.value = await getToolAdmins(toolId)
  } catch (error) {
    console.error(error)
    toolAdmins.value = []
  }
}

// 加载当前使用情况
const loadActiveUsage = async () => {
  try {
    const response = await getToolActiveUsage(toolId)
    // 如果返回数组，取第一个；如果是单个对象，直接使用
    activeUsage.value = Array.isArray(response) ? response[0] : response
  } catch (error) {
    // 没有活动使用记录不算错误
    activeUsage.value = null
  }
}

// 加载配置列表
const loadConfigurations = async () => {
  configLoading.value = true
  try {
    const response = await getToolConfigurations(toolId)
    configurations.value = Array.isArray(response)
      ? response
      : ((response as any)?.data || [])
  } catch (error) {
    ElMessage.error('加载配置列表失败')
    console.error(error)
  } finally {
    configLoading.value = false
  }
}

// 加载相关任务（前端过滤）
const loadRelatedTasks = async () => {
  taskLoading.value = true
  try {
    const response = await getTasks({ skip: 0, limit: 100 })
    const allTasks: Task[] = Array.isArray(response)
      ? response
      : (((response as any)?.data || []) as Task[])
    // 前端过滤与当前工具相关的任务
    relatedTasks.value = allTasks.filter((task: Task) => task.tool?.id === toolId)
  } catch (error) {
    ElMessage.error('加载相关任务失败')
    console.error(error)
  } finally {
    taskLoading.value = false
  }
}

// 计算使用时长
const calculateDuration = (startTime: string | undefined) => {
  if (!startTime) return '-'
  const start = dayjs(startTime)
  const now = dayjs()
  const diffMinutes = now.diff(start, 'minute')
  const hours = Math.floor(diffMinutes / 60)
  const minutes = diffMinutes % 60
  return `${hours}小时${minutes}分钟`
}

// 打开编辑对话框
const handleEdit = () => {
  router.push({
    name: 'ToolEdit',
    params: { id: toolId },
    query: { redirect: route.fullPath },
  })
}

// 提交表单
const handleSubmit = async () => {
  if (!formRef.value) return

  await formRef.value.validate(async (valid) => {
    if (!valid) return

    if (!ensureCurrentProjectSelected()) return

    if (formData.price_type === 0 && (!formData.maximum_reservations_per_day || Number(formData.maximum_reservations_per_day) < 1)) {
      ElMessage.warning('按次收费仪器必须配置每日最多预约次数')
      return
    }

    submitting.value = true
    try {
      await updateTool(toolId, formData)
      ElMessage.success('更新成功')
      editDialogVisible.value = false
      await loadToolDetail()
    } catch (error) {
      ElMessage.error('更新失败')
      console.error(error)
    } finally {
      submitting.value = false
    }
  })
}

// 重置表单
const resetForm = () => {
  formRef.value?.resetFields()
  formData.project_id = projectContextStore.currentProjectId ?? toolDetail.value.project_id ?? toolDetail.value.project?.id
}

// 分类管理
const categoryDialogVisible = ref(false)
const newCategoryName = ref('')

const openCategoryDialog = () => {
  categoryDialogVisible.value = true
}

const addCategory = async () => {
  if (!newCategoryName.value) return
  try {
    await createToolCategory({ name: newCategoryName.value })
    newCategoryName.value = ''
    loadCategories()
    ElMessage.success('新增分类成功')
  } catch (error) {
    console.error(error)
    ElMessage.error('新增失败')
  }
}

const editCategory = async (row: ToolCategory) => {
  try {
    const res = await ElMessageBox.prompt('修改分类名称', '编辑分类', {
      inputValue: row.name,
      confirmButtonText: '确定',
      cancelButtonText: '取消',
    })
    await updateToolCategory(row.id, { name: res.value })
    loadCategories()
    ElMessage.success('更新成功')
  } catch (error) {
    if (error !== 'cancel') {
      console.error(error)
      ElMessage.error('更新失败')
    }
  }
}

const deleteCategory = async (row: ToolCategory) => {
  try {
    await deleteToolCategory(row.id)
    loadCategories()
    ElMessage.success('删除成功')
  } catch (error) {
    console.error(error)
    ElMessage.error('删除失败')
  }
}

// 标签管理
const tagDialogVisible = ref(false)
const newTagName = ref('')

const openTagDialog = () => {
  tagDialogVisible.value = true
}

const addTag = async () => {
  if (!newTagName.value) return
  try {
    await createToolTag({ name: newTagName.value })
    newTagName.value = ''
    loadTags()
    ElMessage.success('新增标签成功')
  } catch (error) {
    console.error(error)
    ElMessage.error('新增失败')
  }
}

const editTag = async (row: ToolTag) => {
  try {
    const res = await ElMessageBox.prompt('修改标签名称', '编辑标签', {
      inputValue: row.name,
      confirmButtonText: '确定',
      cancelButtonText: '取消',
    })
    await updateToolTag(row.id, { name: res.value })
    loadTags()
    ElMessage.success('更新成功')
  } catch (error) {
    if (error !== 'cancel') {
      console.error(error)
      ElMessage.error('更新失败')
    }
  }
}

const deleteTag = async (row: ToolTag) => {
  try {
    await deleteToolTag(row.id)
    loadTags()
    ElMessage.success('删除成功')
  } catch (error) {
    console.error(error)
    ElMessage.error('删除失败')
  }
}

// 图片上传
const beforeImageUpload = (file: File) => {
  const allowedTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
  if (!allowedTypes.includes(file.type)) {
    ElMessage.error('只支持 JPG/PNG/GIF/WEBP 格式')
    return false
  }
  if (file.size > 20 * 1024 * 1024) {
    ElMessage.error('图片大小不能超过 20MB')
    return false
  }
  return true
}

const handleImageUpload = async (options: UploadRequestOptions) => {
  imageUploading.value = true
  try {
    const result = await uploadToolImage(toolId, options.file as File)
    toolDetail.value = result
    options.onSuccess?.(result as any)
    ElMessage.success('图片上传成功')
  } catch (error: any) {
    options.onError?.(error)
    const status = error?.response?.status
    const detail = error?.response?.data?.detail
    if (status === 401) {
      ElMessage.error('上传失败：登录状态无效，请重新登录后再上传')
    } else if (status === 403) {
      ElMessage.error('上传失败：当前账号没有仪器图片管理权限')
    } else {
      ElMessage.error(detail || '图片上传失败')
    }
  } finally {
    imageUploading.value = false
  }
}

const handleDeleteImage = async () => {
  try {
    await ElMessageBox.confirm('确定要删除仪器图片吗？', '提示')
    const result = await deleteToolImage(toolId)
    toolDetail.value = result
    ElMessage.success('图片已删除')
  } catch (error) {
    if (error !== 'cancel') ElMessage.error('删除失败')
  }
}

// 外部用户权限管理
const restrictAccess = ref(false)
const accessList = ref<ToolUserAccess[]>([])
const accessLoading = ref(false)
const selectedUserId = ref<number | undefined>(undefined)
const userSearchLoading = ref(false)
const userSearchResults = ref<User[]>([])

const loadAccessList = async () => {
  accessLoading.value = true
  try {
    accessList.value = await getToolAccess(toolId)
    restrictAccess.value = toolDetail.value.restrict_external_access ?? false
    if (!allUsers.value.length) await loadAllUsers()
  } catch (error) {
    console.error(error)
  } finally {
    accessLoading.value = false
  }
}

const allUsers = ref<User[]>([])
const loadAllUsers = async () => {
  try {
    const users = await getUsers({ limit: 1000 })
    allUsers.value = Array.isArray(users) ? users : []
  } catch (error) {
    console.error(error)
  }
}

const searchUsers = (query: string) => {
  if (!query) {
    userSearchResults.value = []
    return
  }
  const grantedIds = new Set(accessList.value.map(a => a.user_id))
  const q = query.toLowerCase()
  userSearchResults.value = allUsers.value.filter(
    (u: User) =>
      !grantedIds.has(u.id) &&
      (u.username.toLowerCase().includes(q) ||
        u.first_name?.toLowerCase().includes(q) ||
        u.last_name?.toLowerCase().includes(q))
  ).slice(0, 20)
}

const handleGrantAccess = async () => {
  if (!selectedUserId.value) return
  try {
    await grantToolAccess(toolId, selectedUserId.value)
    ElMessage.success('授权成功')
    selectedUserId.value = undefined
    userSearchResults.value = []
    await loadAccessList()
  } catch (error) {
    ElMessage.error('授权失败')
    console.error(error)
  }
}

const handleRevokeAccess = async (row: ToolUserAccess) => {
  try {
    await ElMessageBox.confirm(`确定撤销用户 ${row.username} 的访问权限吗？`, '提示')
    await revokeToolAccess(toolId, row.user_id)
    ElMessage.success('已撤销')
    await loadAccessList()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('操作失败')
      console.error(error)
    }
  }
}

const handleRestrictToggle = async (val: string | number | boolean) => {
  try {
    const boolVal = !!val
    await updateTool(toolId, { restrict_external_access: boolVal })
    toolDetail.value.restrict_external_access = boolVal
    ElMessage.success(boolVal ? '已开启外部用户访问限制' : '已关闭外部用户访问限制')
    if (boolVal) await loadAccessList()
  } catch (error) {
    restrictAccess.value = !val
    ElMessage.error('操作失败')
    console.error(error)
  }
}

// 返回列表
const handleBack = () => {
  router.push('/tools')
}

// 初始化
onMounted(async () => {
  projectContextStore.hydrate()
  await loadToolDetail()
  await loadCategories()
  await loadTags()
  if (canManageTools.value) await loadToolAdmins()
  await loadActiveUsage()
  await loadConfigurations()
  await loadRelatedTasks()
  if (canManageTools.value) await loadAccessList()
})
</script>

<style scoped>
.page-container {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 600;
}

.tool-image-section {
  margin-bottom: 16px;
}

.tool-image-section__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.tool-image-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 14px;
}

.tool-image {
  width: 100%;
  height: 180px;
  border-radius: 10px;
  border: 1px solid #e2e8f0;
  background: #f8fafc;
}

.image-upload-section {
  display: flex;
  align-items: flex-start;
  gap: 16px;
}

.upload-preview-image {
  max-width: 200px;
  max-height: 150px;
  border-radius: 8px;
}

.image-upload-actions {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.info-card {
  margin-bottom: 16px;
}

.usage-card,
.config-card,
.task-card,
.access-card,
.collaboration-card {
  margin-top: 16px;
}

.access-add-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 4px;
}

.color-display {
  display: flex;
  align-items: center;
  gap: 8px;
}

.color-block {
  width: 24px;
  height: 24px;
  border-radius: 4px;
  border: 1px solid #dcdfe6;
}

.current-project-display {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  min-height: 44px;
  padding: 0 14px;
  border-radius: 12px;
  background: #f8fafc;
  border: 1px solid #dbe4ef;
}

.current-project-display__label {
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #64748b;
}

.current-project-display__value {
  font-size: 14px;
  font-weight: 600;
  color: #0f172a;
}

.field-helper {
  margin-top: 8px;
  font-size: 12px;
  line-height: 1.6;
  color: #64748b;
}

.form-section-block {
  margin-top: 4px;
  margin-bottom: 18px;
}

.pricing-grid {
  align-items: end;
}

.field-stack {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.field-stack__label {
  line-height: 1.4;
  font-weight: 600;
  font-size: 14px;
  color: #334155;
}

.field-stack :deep(.el-input-number) {
  width: 100%;
}

.count-based-hint {
  margin-top: 4px;
  padding: 10px 12px;
  border-radius: 12px;
  background: #f0f9eb;
  border: 1px solid #d9f0c7;
  color: #3f6212;
  font-size: 13px;
  line-height: 1.6;
}

.toggle-grid {
  margin-top: 2px;
}

.toggle-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  min-height: 68px;
  padding: 14px 16px;
  border-radius: 16px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
}

.toggle-card__label {
  font-size: 14px;
  font-weight: 600;
  color: #334155;
}

.toggle-card :deep(.el-switch__label) {
  white-space: nowrap;
}

.category-dialog-panel {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.category-dialog-panel__intro {
  font-size: 13px;
  line-height: 1.7;
  color: #64748b;
}

.category-create-box {
  padding: 18px;
  border-radius: 18px;
  background: linear-gradient(180deg, #f8fafc 0%, #eef6ff 100%);
  border: 1px solid rgba(191, 219, 254, 0.8);
}

.category-create-box__meta {
  margin-bottom: 12px;
}

.category-create-box__title {
  font-size: 16px;
  font-weight: 700;
  color: #0f172a;
}

.category-create-box__hint {
  margin-top: 6px;
  font-size: 12px;
  color: #64748b;
}

.category-create-box__form {
  display: flex;
  align-items: center;
  gap: 12px;
}

.category-list-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.category-list-header__title {
  font-size: 15px;
  font-weight: 700;
  color: #0f172a;
}

.category-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.category-list-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  padding: 14px 16px;
  border-radius: 16px;
  background: #ffffff;
  border: 1px solid #e2e8f0;
}

.category-list-item__name {
  font-size: 15px;
  font-weight: 600;
  color: #1e293b;
}

.category-list-item__actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

@media (max-width: 768px) {
  .category-create-box__form,
  .category-list-item {
    align-items: stretch;
    flex-direction: column;
  }

  .category-list-item__actions {
    justify-content: flex-end;
  }

  .toggle-card {
    align-items: stretch;
    flex-direction: column;
  }
}
</style>
