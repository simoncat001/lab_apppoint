<template>
  <div class="page-container">
    <el-card class="header-card" shadow="never">
      <div class="header-row">
        <div class="header-left">
          <el-button :icon="Back" @click="handleCancel">返回</el-button>
          <span class="page-title">
            <el-icon><Tools /></el-icon>
            {{ pageTitle }}
          </span>
        </div>
        <div class="header-right">
          <el-space>
            <el-button @click="handleCancel">取消</el-button>
            <el-button type="primary" :loading="submitting" @click="handleSubmit">
              {{ isEdit ? '保存' : '创建' }}
            </el-button>
          </el-space>
        </div>
      </div>
    </el-card>

    <el-card v-loading="loading" class="form-card" shadow="never">
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
          <div class="field-helper">仪器所属项目固定为当前页面所在项目，不能切换到其他项目。</div>
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

        <el-form-item v-if="isEdit" id="tool-admins-section" label="仪器管理员">
          <el-select
            v-model="selectedToolAdminIds"
            multiple
            filterable
            clearable
            collapse-tags
            collapse-tags-tooltip
            placeholder="请选择可管理此仪器的管理员"
            style="width: 100%"
          >
            <el-option
              v-for="u in staffUsers"
              :key="u.id"
              :label="getUserDisplayName(u)"
              :value="u.id"
            />
          </el-select>
          <div class="field-helper">全局管理员不需要加入这里；这里配置的是只管理本仪器的管理员。</div>
        </el-form-item>
        <el-form-item v-else label="仪器管理员">
          <div class="field-helper">创建仪器后，可在编辑页为这台仪器单独配置管理员。</div>
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

        <el-form-item v-if="isEdit" label="仪器图片">
          <div class="image-manager">
            <div class="image-manager__header">
              <span class="field-helper image-helper">支持多张图片，第一张作为列表封面图。</span>
            </div>
            <div class="image-grid">
              <div
                v-for="(item, index) in toolImages"
                :key="item.id || item.path"
                class="image-card"
              >
                <el-button
                  v-if="item.id"
                  class="image-card__delete"
                  type="danger"
                  :icon="Delete"
                  circle
                  @click.stop="handleDeleteImage(item.id)"
                />
                <el-image
                  :src="getToolImageUrl(item.path) ?? undefined"
                  fit="cover"
                  class="upload-preview-image"
                  :preview-src-list="toolPreviewUrls"
                  :initial-index="index"
                />
                <div class="image-card__meta">
                  <el-tag size="small" :type="index === 0 ? 'primary' : 'info'">
                    {{ index === 0 ? '封面' : `图片 ${index + 1}` }}
                  </el-tag>
                </div>
              </div>
              <el-upload
                class="image-upload-card"
                :auto-upload="true"
                multiple
                :show-file-list="false"
                :disabled="imageUploading"
                :before-upload="beforeImageUpload"
                :http-request="handleImageUpload"
                accept=".jpg,.jpeg,.png,.gif,.webp"
              >
                <div class="image-upload-card__inner">
                  <el-icon class="image-upload-card__icon"><Plus /></el-icon>
                  <span class="image-upload-card__text">添加图片</span>
                </div>
              </el-upload>
            </div>
          </div>
        </el-form-item>
        <el-form-item v-else label="仪器图片">
          <div class="field-helper">创建仪器后会自动进入编辑页，你可以继续上传多张图片。</div>
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
                <el-input-number v-model="formData.price_per_use" :min="0" :precision="2" :step="1" style="width: 100%" />
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
                  style="width: 100%"
                />
              </div>
            </el-col>
            <el-col v-if="formData.price_type === 1" :xs="24" :md="14">
              <div class="field-stack">
                <div class="field-stack__label">每小时价格</div>
                <el-input-number v-model="formData.price_per_hour" :min="0" :precision="2" :step="1" style="width: 100%" />
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
                <el-switch v-model="formData.operational" active-text="正常" inactive-text="故障" />
              </div>
            </el-col>
            <el-col :xs="24" :md="8">
              <div class="toggle-card">
                <div class="toggle-card__label">可见性</div>
                <el-switch v-model="formData.visible" active-text="可见" inactive-text="隐藏" />
              </div>
            </el-col>
            <el-col :xs="24" :md="8">
              <div class="toggle-card">
                <div class="toggle-card__label">需要预约</div>
                <el-switch v-model="formData.requires_reservation" active-text="需要" inactive-text="不需要" />
              </div>
            </el-col>
            <el-col :xs="24" :md="8">
              <div class="toggle-card">
                <div class="toggle-card__label">外部用户限制</div>
                <el-switch v-model="formData.restrict_external_access" active-text="受限" inactive-text="开放" />
              </div>
            </el-col>
          </el-row>
        </div>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, nextTick, onMounted } from 'vue'
import { useRoute, useRouter, onBeforeRouteLeave } from 'vue-router'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import type { UploadRequestOptions } from 'element-plus'
import { Back, Delete, Plus, Tools } from '@element-plus/icons-vue'
import {
  getTool,
  createTool,
  updateTool,
  getToolCategories,
  getToolTags,
  uploadToolImage,
  deleteToolImage,
  deleteToolImageById,
  getToolAdmins,
  getToolImages,
  getToolImageUrl,
  getToolImagePreviewUrls,
  updateToolAdmins,
} from '@/api/tools'
import { getUsers } from '@/api/users'
import type { Tool, ToolCategory, ToolTag, User } from '@/types'
import { useProjectContextStore } from '@/stores/project-context'
import { getUserDisplayName } from '@/utils/user'

const route = useRoute()
const router = useRouter()
const projectContextStore = useProjectContextStore()

const isEdit = computed(() => !!route.params.id)
const toolId = computed(() =>
  route.params.id ? Number(route.params.id) : undefined
)
const pageTitle = computed(() => (isEdit.value ? '编辑仪器' : '创建仪器'))
const redirectTarget = computed(() => {
  const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : ''
  if (redirect.startsWith('/')) return redirect
  if (isEdit.value && toolId.value) return `/tools/${toolId.value}`
  return '/tools'
})

const loading = ref(false)
const submitting = ref(false)
const imageUploading = ref(false)
const formRef = ref<FormInstance>()

// 脏标记：提交成功后不再二次确认
const savedClean = ref(false)
const initialSnapshot = ref<string>('')

const categories = ref<ToolCategory[]>([])
const tags = ref<ToolTag[]>([])
const staffUsers = ref<User[]>([])
const selectedToolAdminIds = ref<number[]>([])
const toolImages = computed(() => getToolImages(formData))
const toolPreviewUrls = computed(() => getToolImagePreviewUrls(formData))

const formData = reactive<Partial<Tool>>({
  id: undefined,
  name: '',
  category_id: undefined,
  project_id: projectContextStore.currentProjectId ?? undefined,
  tag_ids: [],
  location: '',
  description: '',
  image: '',
  images: [],
  operational: true,
  visible: true,
  requires_reservation: true,
  price_type: 1,
  price_per_use: 0,
  price_per_hour: 0,
  maximum_reservations_per_day: undefined,
  restrict_external_access: false,
})

const formRules: FormRules = {
  name: [{ required: true, message: '请输入仪器名称', trigger: 'blur' }],
  category_id: [{ required: true, message: '请选择分类', trigger: 'change' }],
  project_id: [{ required: true, message: '请先选择当前项目', trigger: 'change' }],
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

const snapshot = () =>
  JSON.stringify({
    name: formData.name,
    category_id: formData.category_id,
    project_id: formData.project_id,
    tag_ids: [...(formData.tag_ids ?? [])].sort(),
    location: formData.location,
    description: formData.description,
    operational: formData.operational,
    visible: formData.visible,
    requires_reservation: formData.requires_reservation,
    price_type: formData.price_type,
    price_per_use: formData.price_per_use,
    price_per_hour: formData.price_per_hour,
    maximum_reservations_per_day: formData.maximum_reservations_per_day,
    restrict_external_access: formData.restrict_external_access,
    selected_tool_admin_ids: [...selectedToolAdminIds.value].sort(),
  })

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

const loadStaffUsers = async () => {
  try {
    const users = await getUsers({ skip: 0, limit: 1000 })
    staffUsers.value = users.filter((user) => user.is_staff || user.is_superuser)
  } catch (error) {
    console.error(error)
  }
}

const loadToolAdmins = async (id: number) => {
  try {
    selectedToolAdminIds.value = (await getToolAdmins(id)).map((user) => user.id)
  } catch (error) {
    console.error(error)
    selectedToolAdminIds.value = []
  }
}

const scrollToFocusedSection = async () => {
  if (route.query.focus !== 'admins') return
  await nextTick()
  document.getElementById('tool-admins-section')?.scrollIntoView({
    behavior: 'smooth',
    block: 'center',
  })
}

const loadTool = async (id: number) => {
  loading.value = true
  try {
    const response = await getTool(id)
    const data: Tool = (response as any)?.data
      ? (response as any).data
      : (response as unknown as Tool)
    Object.assign(formData, {
      id: data.id,
      name: data.name,
      category_id: data.category_id ?? data.category?.id,
      project_id: projectContextStore.currentProjectId ?? data.project_id ?? data.project?.id,
      tag_ids: data.tags ? data.tags.map((tag) => tag.id) : [],
      location: data.location ?? '',
      description: data.description ?? '',
      image: data.image ?? '',
      images: data.images ?? [],
      operational: data.operational ?? true,
      visible: data.visible ?? true,
      requires_reservation: data.requires_reservation ?? true,
      price_type: data.price_type ?? 1,
      price_per_use: Number(data.price_per_use || 0),
      price_per_hour: Number(data.price_per_hour || 0),
      maximum_reservations_per_day: data.maximum_reservations_per_day ?? undefined,
      restrict_external_access: data.restrict_external_access ?? false,
    })
    await loadToolAdmins(id)
    initialSnapshot.value = snapshot()
    await scrollToFocusedSection()
  } catch (error) {
    console.error(error)
    ElMessage.error('加载仪器失败')
    router.replace('/tools')
  } finally {
    loading.value = false
  }
}

// ==================== 图片（仅编辑态） ====================
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
  if (!toolId.value) {
    const error = new Error('Missing tool id')
    options.onError?.(error as any)
    ElMessage.error('请先保存仪器后再上传图片')
    return
  }
  imageUploading.value = true
  try {
    const result = await uploadToolImage(toolId.value, options.file as File)
    formData.image = result.image ?? ''
    formData.images = result.images ?? []
    options.onSuccess?.(result as any)
    ElMessage.success('图片上传成功')
  } catch (error: any) {
    options.onError?.(error as any)
    console.error(error)
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

const handleDeleteImage = async (imageId: number) => {
  if (!toolId.value) return
  try {
    await ElMessageBox.confirm('确定要删除仪器图片吗？', '提示', { type: 'warning' })
    const result = imageId > 0
      ? await deleteToolImageById(toolId.value, imageId)
      : await deleteToolImage(toolId.value)
    formData.image = result.image ?? ''
    formData.images = result.images ?? []
    ElMessage.success('图片已删除')
  } catch (error) {
    if (error !== 'cancel') ElMessage.error('删除失败')
  }
}

// ==================== 保存 ====================
const handleSubmit = async () => {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    if (!ensureCurrentProjectSelected()) return

    if (
      formData.price_type === 0 &&
      (!formData.maximum_reservations_per_day || Number(formData.maximum_reservations_per_day) < 1)
    ) {
      ElMessage.warning('按次收费仪器必须配置每日最多预约次数')
      return
    }

    submitting.value = true
    try {
      if (isEdit.value && toolId.value) {
        await updateTool(toolId.value, formData)
        await updateToolAdmins(toolId.value, selectedToolAdminIds.value)
        ElMessage.success('保存成功')
        savedClean.value = true
        router.push(redirectTarget.value)
      } else {
        const createdTool = await createTool(formData)
        ElMessage.success('创建成功，请继续上传图片')
        savedClean.value = true
        router.replace({
          name: 'ToolEdit',
          params: { id: createdTool.id },
          query: { redirect: redirectTarget.value },
        })
      }
    } catch (error) {
      console.error(error)
      ElMessage.error(isEdit.value ? '保存失败' : '创建失败')
    } finally {
      submitting.value = false
    }
  })
}

const handleCancel = () => {
  router.push(redirectTarget.value)
}

// 未保存改动拦截
onBeforeRouteLeave(async () => {
  if (savedClean.value) return true
  // 新建模式：未填任何字段则放行
  if (!isEdit.value && snapshot() === initialSnapshot.value) return true
  if (isEdit.value && snapshot() === initialSnapshot.value) return true
  try {
    await ElMessageBox.confirm('有未保存的修改，确定离开吗？', '提示', {
      type: 'warning',
      confirmButtonText: '离开',
      cancelButtonText: '继续编辑',
    })
    return true
  } catch {
    return false
  }
})

onMounted(async () => {
  projectContextStore.hydrate()
  await Promise.all([loadCategories(), loadTags(), loadStaffUsers()])

  if (isEdit.value && toolId.value) {
    await loadTool(toolId.value)
  } else {
    if (!ensureCurrentProjectSelected()) {
      router.replace('/tools')
      return
    }
    initialSnapshot.value = snapshot()
  }
})
</script>

<style scoped>
.page-container {
  padding: 20px;
}

.header-card {
  margin-bottom: 16px;
  position: sticky;
  top: 0;
  z-index: 10;
}

.header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.page-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 600;
  color: #0f172a;
}

.form-card {
  margin-bottom: 16px;
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

.image-manager {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.image-manager__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.upload-preview-image {
  width: 160px;
  height: 160px;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
  background: #f8fafc;
  object-fit: contain;
}

.image-helper {
  margin-top: 0;
}

.image-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 14px;
}

.image-upload-card {
  width: 100%;
}

.image-upload-card :deep(.el-upload) {
  display: block;
  width: 100%;
}

.image-upload-card__inner {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  min-height: 214px;
  border-radius: 14px;
  border: 1px dashed #94a3b8;
  background:
    linear-gradient(180deg, rgba(248, 250, 252, 0.98) 0%, rgba(241, 245, 249, 0.98) 100%);
  color: #64748b;
  cursor: pointer;
  transition: border-color 0.2s ease, background 0.2s ease, transform 0.2s ease;
}

.image-upload-card :deep(.el-upload:hover) .image-upload-card__inner {
  border-color: #2563eb;
  background:
    linear-gradient(180deg, rgba(239, 246, 255, 0.98) 0%, rgba(219, 234, 254, 0.98) 100%);
  color: #1d4ed8;
  transform: translateY(-1px);
}

.image-upload-card__icon {
  font-size: 28px;
}

.image-upload-card__text {
  font-size: 13px;
  font-weight: 600;
}

.image-card {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 12px;
  border-radius: 14px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
}

.image-card__meta {
  display: flex;
  align-items: center;
  justify-content: flex-start;
  gap: 10px;
}

.image-card__delete {
  position: absolute;
  top: 10px;
  right: 10px;
  z-index: 2;
  width: 28px;
  height: 28px;
  border: none;
  box-shadow: 0 8px 20px rgba(239, 68, 68, 0.24);
}

.image-card__delete :deep(.el-icon) {
  font-size: 13px;
}

@media (max-width: 768px) {
  .toggle-card {
    align-items: stretch;
    flex-direction: column;
  }
}
</style>
