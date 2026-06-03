import type { Project } from '@/types'

export const getProjectDisplayName = (
  project?: Pick<Project, 'name' | 'external_display_name'> | null
): string => {
  if (!project) return ''
  const externalName = (project.external_display_name || '').trim()
  if (externalName) return externalName
  return (project.name || '').trim()
}
