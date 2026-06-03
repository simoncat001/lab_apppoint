<template>
  <div class="page-container">
    <el-card class="header-card" shadow="never">
      <div class="header-row">
        <div class="header-left">
          <el-button :icon="Back" @click="handleCancel">返回列表</el-button>
          <span class="page-title">
            <el-icon><Document /></el-icon>
            {{ pageTitle }}
          </span>
        </div>
        <div class="header-right">
          <el-space>
            <el-switch
              v-model="formData.published"
              active-text="发布"
              inactive-text="草稿"
              inline-prompt
            />
            <el-button @click="handleCancel">取消</el-button>
            <el-button type="primary" :loading="submitting" @click="handleSubmit">
              {{ isEdit ? '保存' : '发布' }}
            </el-button>
          </el-space>
        </div>
      </div>
    </el-card>

    <el-card v-loading="loading" class="form-card" shadow="never">
      <el-form
        ref="formRef"
        :model="formData"
        :rules="rules"
        label-position="top"
      >
        <el-form-item label="标题" prop="title">
          <el-input
            v-model="formData.title"
            placeholder="请输入公告标题"
            size="large"
            maxlength="200"
            show-word-limit
          />
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
import { ref, reactive, shallowRef, onMounted, onBeforeUnmount, computed } from 'vue'
import { useRoute, useRouter, onBeforeRouteLeave } from 'vue-router'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { Back, Document } from '@element-plus/icons-vue'
import {
  getAnnouncement,
  createAnnouncement,
  updateAnnouncement,
  deleteAnnouncement,
} from '@/api/announcements'
import type { Announcement } from '@/types'

// WangEditor
import '@wangeditor/editor/dist/css/style.css'
import { Editor, Toolbar } from '@wangeditor/editor-for-vue'
import type { IDomEditor, IEditorConfig, IToolbarConfig } from '@wangeditor/editor'

const route = useRoute()
const router = useRouter()

const isEdit = computed(() => !!route.params.id)
const announcementId = computed(() =>
  route.params.id ? Number(route.params.id) : undefined
)
const pageTitle = computed(() => (isEdit.value ? '编辑公告' : '发布公告'))

const loading = ref(false)
const submitting = ref(false)
const formRef = ref<FormInstance>()

// 脏标记：提交成功后不再二次确认
const savedClean = ref(false)
const initialSnapshot = ref<string>('')

const formData = reactive<Partial<Announcement>>({
  id: undefined,
  title: '',
  content: '',
  published: true,
})

const rules: FormRules = {
  title: [{ required: true, message: '请输入标题', trigger: 'blur' }],
  content: [
    {
      validator: (_rule, value, cb) => {
        const text = String(value || '').replace(/<[^>]+>/g, '').trim()
        if (!text) cb(new Error('请输入公告内容'))
        else cb()
      },
      trigger: 'blur',
    },
  ],
}

// WangEditor 实例
const editorRef = shallowRef<IDomEditor>()
const editorReady = ref(false)
const toolbarConfig: Partial<IToolbarConfig> = {}
const editorConfig: Partial<IEditorConfig> = {
  placeholder: '请输入公告内容...',
  MENU_CONF: {
    uploadImage: {
      server: '',        // 在 onMounted 时用 announcementId 动态拼出
      fieldName: 'file',
      maxFileSize: 20 * 1024 * 1024,
      allowedFileTypes: ['image/jpeg', 'image/png', 'image/gif', 'image/webp'],
      headers: {} as Record<string, string>,
      onFailed(_file: File, res: any) {
        console.error('图片上传失败', res)
        ElMessage.error(`图片上传失败：${res?.message || res?.detail || '请检查登录状态'}`)
      },
      onError(_file: File, err: any, res: any) {
        console.error('图片上传出错', err, res)
        ElMessage.error('图片上传出错，请稍后重试或检查登录状态')
      },
    },
  },
}

const configureUploadEndpoint = (id: number) => {
  const conf = editorConfig.MENU_CONF?.uploadImage as any
  if (!conf) return
  conf.server = `/api/announcements/${id}/image`
  const token = localStorage.getItem('access_token')
  if (token) conf.headers = { Authorization: `Bearer ${token}` }
  const projectId = localStorage.getItem('current_project_id')
  if (projectId) conf.headers = { ...conf.headers, 'X-Current-Project-Id': projectId }
}

const handleEditorCreated = (editor: IDomEditor) => {
  editorRef.value = editor
}

const snapshot = () =>
  JSON.stringify({
    title: formData.title,
    content: formData.content,
    published: formData.published,
  })

const loadAnnouncement = async (id: number) => {
  loading.value = true
  try {
    const response = await getAnnouncement(id)
    const data: Announcement = (response as any)?.data
      ? (response as any).data
      : (response as unknown as Announcement)
    Object.assign(formData, {
      id: data.id,
      title: data.title,
      content: data.content,
      published: data.published,
    })
    initialSnapshot.value = snapshot()
  } catch (error) {
    console.error(error)
    ElMessage.error('加载公告失败')
    router.replace('/announcements')
  } finally {
    loading.value = false
  }
}

// 是否为新建进入时自动创建的空草稿（用户取消则回滚删除）
const isAutoDraft = ref(route.query.draft === '1')

const handleSubmit = async () => {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    submitting.value = true
    try {
      if (isEdit.value && announcementId.value) {
        await updateAnnouncement(announcementId.value, formData)
        ElMessage.success(isAutoDraft.value ? '发布成功' : '保存成功')
      } else {
        await createAnnouncement(formData)
        ElMessage.success('发布成功')
      }
      savedClean.value = true
      isAutoDraft.value = false
      router.push('/announcements')
    } catch (error) {
      console.error(error)
      ElMessage.error('保存失败')
    } finally {
      submitting.value = false
    }
  })
}

const handleCancel = () => {
  router.push('/announcements')
}

// 未保存改动时，拦截路由跳转；若为自动草稿则提示删除草稿
onBeforeRouteLeave(async () => {
  if (savedClean.value) return true

  // 自动草稿：未动过（或用户明确取消）一律回滚删除
  if (isAutoDraft.value && announcementId.value) {
    if (snapshot() === initialSnapshot.value) {
      try {
        await deleteAnnouncement(announcementId.value)
      } catch (error) {
        console.error('清理草稿失败', error)
      }
      return true
    }
    try {
      await ElMessageBox.confirm('尚未保存，草稿将被丢弃，确定离开吗？', '提示', {
        type: 'warning',
        confirmButtonText: '丢弃草稿',
        cancelButtonText: '继续编辑',
      })
      try {
        await deleteAnnouncement(announcementId.value)
      } catch (error) {
        console.error('清理草稿失败', error)
      }
      return true
    } catch {
      return false
    }
  }

  if (snapshot() === initialSnapshot.value) return true
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
  if (isEdit.value && announcementId.value) {
    configureUploadEndpoint(announcementId.value)
    await loadAnnouncement(announcementId.value)
    editorReady.value = true
  } else {
    // 新建路径已弃用：正常情况下列表页会先创建草稿再跳转到 /:id/edit
    // 这里作为兜底，避免用户误用 /new 时空白
    ElMessage.warning('请从公告列表进入发布流程')
    router.replace('/announcements')
  }
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

.editor-container {
  border: 1px solid #dcdfe6;
  border-radius: 6px;
  overflow: hidden;
  width: 100%;
}

.editor-toolbar {
  border-bottom: 1px solid #dcdfe6;
}

.editor-content {
  height: calc(100vh - 360px);
  min-height: 400px;
  overflow-y: auto;
}

.editor-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 400px;
  color: var(--el-text-color-secondary);
  font-size: 14px;
}
</style>
