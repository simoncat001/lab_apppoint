import type { User } from '@/types'

type UserLike = Pick<User, 'username' | 'first_name' | 'last_name'>

export const getUserDisplayName = (user?: Partial<UserLike> | null, fallback = '-') => {
  if (!user) return fallback

  const lastName = (user.last_name || '').trim()
  const firstName = (user.first_name || '').trim()
  const fullName = `${lastName}${firstName}`.trim()

  return fullName || user.username || fallback
}

export const getUserInitial = (user?: Partial<UserLike> | null, fallback = 'U') => {
  const displayName = getUserDisplayName(user, '')
  return displayName.charAt(0).toUpperCase() || fallback
}
