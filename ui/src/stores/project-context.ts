import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import type { Project } from '@/types'
import { getProjects } from '@/api/projects'
import { getProjectDisplayName } from '@/utils/project'

const STORAGE_PROJECT_ID_KEY = 'current_project_id'
const STORAGE_PROJECT_NAME_KEY = 'current_project_name'

export const useProjectContextStore = defineStore('projectContext', () => {
    const currentProjectId = ref<number | null>(null)
    const currentProjectName = ref<string>('')
    const projects = ref<Project[]>([])
    const loading = ref(false)
    const loaded = ref(false)

    const hasCurrentProject = computed(() => !!currentProjectId.value)

    const hydrate = () => {
        const rawId = localStorage.getItem(STORAGE_PROJECT_ID_KEY)
        const rawName = localStorage.getItem(STORAGE_PROJECT_NAME_KEY) || ''
        const parsed = rawId ? Number(rawId) : NaN
        currentProjectId.value = Number.isFinite(parsed) && parsed > 0 ? parsed : null
        currentProjectName.value = rawName
    }

    const persistCurrentProject = () => {
        if (currentProjectId.value) {
            localStorage.setItem(STORAGE_PROJECT_ID_KEY, String(currentProjectId.value))
            localStorage.setItem(STORAGE_PROJECT_NAME_KEY, currentProjectName.value || '')
            return
        }
        localStorage.removeItem(STORAGE_PROJECT_ID_KEY)
        localStorage.removeItem(STORAGE_PROJECT_NAME_KEY)
    }

    const clearCurrentProject = () => {
        currentProjectId.value = null
        currentProjectName.value = ''
        persistCurrentProject()
    }

    const setCurrentProject = (project: Pick<Project, 'id' | 'name' | 'external_display_name'> | null) => {
        if (!project) {
            clearCurrentProject()
            return
        }
        currentProjectId.value = project.id
        currentProjectName.value = getProjectDisplayName(project)
        persistCurrentProject()
    }

    const loadProjects = async (force = false) => {
        if (loading.value) return projects.value
        if (loaded.value && !force) return projects.value

        loading.value = true
        try {
            const response = await getProjects({ active: true, skip: 0, limit: 2000 })
            const list = Array.isArray(response) ? response : (response as any).data || []
            projects.value = Array.isArray(list) ? list : []
            loaded.value = true

            if (currentProjectId.value) {
                const matched = projects.value.find((p) => p.id === currentProjectId.value)
                if (matched) {
                    currentProjectName.value = getProjectDisplayName(matched)
                    persistCurrentProject()
                } else {
                    clearCurrentProject()
                }
            }

            return projects.value
        } finally {
            loading.value = false
        }
    }

    const ensureProjectSelected = async () => {
        if (!currentProjectId.value) {
            await loadProjects()
            return !!currentProjectId.value
        }
        if (!loaded.value) {
            await loadProjects()
        }
        return !!currentProjectId.value
    }

    return {
        currentProjectId,
        currentProjectName,
        projects,
        loading,
        loaded,
        hasCurrentProject,
        hydrate,
        loadProjects,
        setCurrentProject,
        clearCurrentProject,
        ensureProjectSelected,
    }
})
