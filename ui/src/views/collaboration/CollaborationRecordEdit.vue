<template>
  <div class="page-container">
    <el-card class="header-card" shadow="never">
      <div class="header-row">
        <div class="header-left">
          <el-button :icon="Back" @click="handleCancel">返回</el-button>
          <div>
            <div class="page-kicker">Research Collaboration</div>
            <div class="page-title">
              <el-icon><EditPen /></el-icon>
              {{ pageTitle }}
            </div>
          </div>
        </div>
        <el-space>
          <el-button @click="handleCancel">取消</el-button>
          <el-button type="primary" :loading="submitting" @click="handleSubmit">
            保存记录
          </el-button>
        </el-space>
      </div>
    </el-card>

    <el-card v-loading="loading" class="form-card" shadow="never">
      <el-form ref="formRef" :model="formData" :rules="rules" label-position="top">
        <el-row :gutter="16">
          <el-col :xs="24" :md="8">
            <el-form-item label="记录类型" prop="record_type">
              <el-select v-model="formData.record_type" placeholder="请选择记录类型" style="width: 100%">
                <el-option v-for="item in recordTypeOptions" :key="item.value" :label="item.label" :value="item.value" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :xs="24" :md="8">
            <el-form-item label="可见性" prop="visibility">
              <el-select v-model="formData.visibility" style="width: 100%">
                <el-option label="项目可见" value="project" />
                <el-option label="管理员可见" value="staff" />
                <el-option label="仪器管理员" value="tool_managers" />
                <el-option label="仅作者" value="author_private" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :xs="24" :md="8">
            <el-form-item label="状态" prop="status">
              <el-select v-model="formData.status" style="width: 100%">
                <el-option label="草稿" value="draft" />
                <el-option label="发布" value="published" />
                <el-option v-if="formData.status === 'archived'" label="已归档" value="archived" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item label="标题" prop="title">
          <el-input
            v-model="formData.title"
            placeholder="请输入协作记录标题"
            maxlength="200"
            show-word-limit
            size="large"
          />
        </el-form-item>

        <el-form-item v-if="isEdit" label="置顶">
          <el-switch v-model="formData.pinned" />
        </el-form-item>

        <el-form-item label="内容" prop="content">
          <div class="editor-container">
            <template v-if="editorReady">
              <Toolbar
                :editor="editorRef"
                :defaultConfig="toolbarConfig"
                :mode="'default'"
                class="editor-toolbar"
              />
              <Editor
                v-model="formData.content"
                :defaultConfig="editorConfig"
                :mode="'default'"
                class="editor-content"
                @onCreated="handleEditorCreated"
              />
            </template>
            <div v-else class="editor-placeholder">编辑器加载中...</div>
          </div>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref, shallowRef } from 'vue'
import { useRoute, useRouter, onBeforeRouteLeave } from 'vue-router'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { Back, EditPen } from '@element-plus/icons-vue'
import '@wangeditor/editor/dist/css/style.css'
import { Editor, Toolbar } from '@wangeditor/editor-for-vue'
import type { IDomEditor, IEditorConfig, IToolbarConfig } from '@wangeditor/editor'
import {
  createCollaborationRecord,
  getCollaborationRecord,
  updateCollaborationRecord,
} from '@/api/collaboration'
import { useAuthStore } from '@/stores/auth'
import type {
  CollaborationRecord,
  CollaborationRecordPayload,
  CollaborationRecordType,
  CollaborationStatus,
  CollaborationVisibility,
} from '@/types'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

type CollaborationRecordForm = CollaborationRecordPayload & {
  pinned?: boolean
  status: CollaborationStatus
  visibility: CollaborationVisibility
}

const isEdit = computed(() => !!route.params.id)
const recordId = computed(() => (route.params.id ? Number(route.params.id) : undefined))
const pageTitle = computed(() => (isEdit.value ? '编辑协作记录' : '新增协作记录'))

const formRef = ref<FormInstance>()
const loading = ref(false)
const submitting = ref(false)
const savedClean = ref(false)
const initialSnapshot = ref('')
const editorRef = shallowRef<IDomEditor>()
const editorReady = ref(false)

const queryNumber = (key: string) => {
  const raw = route.query[key]
  const value = Array.isArray(raw) ? raw[0] : raw
  const num = value ? Number(value) : undefined
  return Number.isFinite(num) ? num : undefined
}

const queryString = (key: string) => {
  const raw = route.query[key]
  return Array.isArray(raw) ? raw[0] : raw
}

const defaultRecordType = computed<CollaborationRecordType>(() => {
  const type = queryString('record_type') as CollaborationRecordType | undefined
  if (type) return type
  if (queryNumber('reservation_id')) return 'reservation_note'
  return 'tool_note'
})

const formData = reactive<CollaborationRecordForm>({
  tool_id: queryNumber('tool_id'),
  reservation_id: queryNumber('reservation_id'),
  record_type: defaultRecordType.value,
  title: '',
  content: '',
  content_format: 'html',
  visibility: 'project',
  status: 'draft',
  pinned: false,
})

const canCreateKnowledgeRecords = computed(() => authStore.isStaff() || authStore.isSuperuser())

const regularRecordTypeOptions = computed(() => {
  if (formData.reservation_id) {
    return [
      { label: '预约笔记', value: 'reservation_note' },
      { label: '实验过程', value: 'experiment_note' },
      { label: '问题记录', value: 'issue' },
    ] as Array<{ label: string; value: CollaborationRecordType }>
  }
  return [
    { label: '仪器笔记', value: 'tool_note' },
    { label: '预约笔记', value: 'reservation_note' },
    { label: '实验过程', value: 'experiment_note' },
    { label: '问题记录', value: 'issue' },
  ] as Array<{ label: string; value: CollaborationRecordType }>
})

const knowledgeRecordTypeOptions = [
    { label: '维护经验', value: 'maintenance_experience' },
    { label: 'SOP', value: 'sop' },
    { label: 'FAQ', value: 'faq' },
    { label: '案例', value: 'case_study' },
  ] as Array<{ label: string; value: CollaborationRecordType }>

const recordTypeOptions = computed(() => {
  const options = [...regularRecordTypeOptions.value]
  if (canCreateKnowledgeRecords.value && !formData.reservation_id) {
    options.splice(3, 0, ...knowledgeRecordTypeOptions)
  }
  if (!options.some(item => item.value === formData.record_type)) {
    const known = knowledgeRecordTypeOptions.find(item => item.value === formData.record_type)
    if (known && isEdit.value) options.push(known)
  }
  return options
})

const ensureCreateRecordTypeAllowed = () => {
  if (isEdit.value) return
  if (recordTypeOptions.value.some(item => item.value === formData.record_type)) return
  formData.record_type = recordTypeOptions.value[0]?.value || 'tool_note'
}

const textFromHtml = (value: string) =>
  String(value || '')
    .replace(/<style[\s\S]*?<\/style>/gi, ' ')
    .replace(/<script[\s\S]*?<\/script>/gi, ' ')
    .replace(/<[^>]+>/g, ' ')
    .replace(/&nbsp;/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()

const rules: FormRules = {
  record_type: [{ required: true, message: '请选择记录类型', trigger: 'change' }],
  title: [{ required: true, message: '请输入标题', trigger: 'blur' }],
  visibility: [{ required: true, message: '请选择可见性', trigger: 'change' }],
  status: [{ required: true, message: '请选择状态', trigger: 'change' }],
  content: [
    {
      validator: (_rule, value, callback) => {
        if (textFromHtml(String(value || ''))) callback()
        else callback(new Error('请输入内容'))
      },
      trigger: 'blur',
    },
  ],
}

const toolbarConfig: Partial<IToolbarConfig> = {}

const editorConfig: Partial<IEditorConfig> = {
  placeholder: '请输入运行笔记、实验过程、SOP、FAQ、案例或问题记录...',
  MENU_CONF: {
    uploadImage: {
      server: '',
      fieldName: 'file',
      maxFileSize: 20 * 1024 * 1024,
      allowedFileTypes: ['image/jpeg', 'image/png', 'image/gif', 'image/webp'],
      headers: {} as Record<string, string>,
      onFailed(_file: File, res: any) {
        console.error('协作记录图片上传失败', res)
        ElMessage.error(`图片上传失败：${res?.message || res?.detail || '请检查登录状态'}`)
      },
      onError(_file: File, err: any, res: any) {
        console.error('协作记录图片上传出错', err, res)
        ElMessage.error('图片上传出错，请稍后重试或检查登录状态')
      },
    },
    uploadVideo: {
      server: '',
      fieldName: 'file',
      maxFileSize: 300 * 1024 * 1024,
      allowedFileTypes: ['video/mp4', 'video/webm', 'video/ogg', 'video/quicktime'],
      headers: {} as Record<string, string>,
      onFailed(_file: File, res: any) {
        console.error('协作记录视频上传失败', res)
        ElMessage.error(`视频上传失败：${res?.message || res?.detail || '请检查登录状态或文件大小'}`)
      },
      onError(_file: File, err: any, res: any) {
        console.error('协作记录视频上传出错', err, res)
        ElMessage.error('视频上传出错，请稍后重试或检查登录状态')
      },
    },
  },
}

const handleEditorCreated = (editor: IDomEditor) => {
  editorRef.value = editor
}

const getUploadHeaders = () => {
  const headers: Record<string, string> = {}
  const token = localStorage.getItem('access_token')
  if (token) headers.Authorization = `Bearer ${token}`
  const projectId = localStorage.getItem('current_project_id')
  if (projectId) headers['X-Current-Project-Id'] = projectId
  return headers
}

const buildUploadServer = (kind: 'image' | 'video') => {
  const params = new URLSearchParams()
  if (formData.tool_id) params.set('tool_id', String(formData.tool_id))
  if (formData.reservation_id) params.set('reservation_id', String(formData.reservation_id))
  const query = params.toString()
  return `/api/collaboration-records/media/${kind}${query ? `?${query}` : ''}`
}

const configureUploadEndpoints = () => {
  const imageConf = editorConfig.MENU_CONF?.uploadImage as any
  const videoConf = editorConfig.MENU_CONF?.uploadVideo as any
  const headers = getUploadHeaders()
  if (imageConf) {
    imageConf.server = buildUploadServer('image')
    imageConf.headers = headers
  }
  if (videoConf) {
    videoConf.server = buildUploadServer('video')
    videoConf.headers = headers
  }
}

const snapshot = () =>
  JSON.stringify({
    tool_id: formData.tool_id,
    reservation_id: formData.reservation_id,
    record_type: formData.record_type,
    title: formData.title,
    content: formData.content,
    visibility: formData.visibility,
    status: formData.status,
    pinned: formData.pinned,
  })

const normalizeRecord = (response: unknown) => {
  return (response as any)?.data ? (response as any).data as CollaborationRecord : response as CollaborationRecord
}

const loadRecord = async (id: number) => {
  loading.value = true
  try {
    const record = normalizeRecord(await getCollaborationRecord(id))
    Object.assign(formData, {
      tool_id: record.tool_id ?? undefined,
      reservation_id: record.reservation_id ?? undefined,
      record_type: record.record_type,
      title: record.title,
      content: record.content || '',
      content_format: 'html',
      visibility: record.visibility,
      status: record.status,
      pinned: record.pinned,
    })
    initialSnapshot.value = snapshot()
  } catch (error) {
    console.error(error)
    ElMessage.error('加载协作记录失败')
    router.replace('/collaboration-records')
  } finally {
    loading.value = false
  }
}

const getRedirectPath = () => {
  const redirect = queryString('redirect')
  if (redirect) return redirect
  if (formData.tool_id) return `/tools/${formData.tool_id}`
  return '/collaboration-records'
}

const handleCancel = () => {
  router.push(getRedirectPath())
}

const buildPayload = () => ({
  tool_id: formData.tool_id,
  reservation_id: formData.reservation_id,
  record_type: formData.record_type,
  title: formData.title,
  content: formData.content,
  content_format: 'html',
  visibility: formData.visibility,
  status: formData.status,
})

const handleSubmit = async () => {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    submitting.value = true
    try {
      if (isEdit.value && recordId.value) {
        await updateCollaborationRecord(recordId.value, {
          ...buildPayload(),
          pinned: formData.pinned,
        })
        ElMessage.success('协作记录已更新')
      } else {
        await createCollaborationRecord(buildPayload())
        ElMessage.success('协作记录已创建')
      }
      savedClean.value = true
      router.push(getRedirectPath())
    } catch (error) {
      console.error(error)
      ElMessage.error('保存协作记录失败，请确认当前账号有权限')
    } finally {
      submitting.value = false
    }
  })
}

onBeforeRouteLeave(async () => {
  if (savedClean.value || snapshot() === initialSnapshot.value) return true
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
  if (isEdit.value && recordId.value) {
    await loadRecord(recordId.value)
  } else {
    ensureCreateRecordTypeAllowed()
    initialSnapshot.value = snapshot()
  }
  configureUploadEndpoints()
  editorReady.value = true
})

onBeforeUnmount(() => {
  if (editorRef.value) {
    editorRef.value.destroy()
    editorRef.value = undefined
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

.page-kicker {
  margin-bottom: 4px;
  color: #64748b;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.page-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 18px;
  font-weight: 700;
  color: #0f172a;
}

.form-card {
  margin-bottom: 16px;
}

.editor-container {
  border: 1px solid #dcdfe6;
  border-radius: 8px;
  overflow: hidden;
  width: 100%;
}

.editor-toolbar {
  border-bottom: 1px solid #dcdfe6;
}

.editor-content {
  height: calc(100vh - 410px);
  min-height: 420px;
  overflow-y: auto;
}

.editor-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 420px;
  color: var(--el-text-color-secondary);
  font-size: 14px;
}
</style>
