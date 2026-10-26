export function roleLandingPath(roles: string[] = []): string {
  if (roles.includes('*')) return '/platform-admin'
  if (roles.includes('platform-admin')) return '/platform-admin'
  if (roles.includes('admin') || roles.includes('tenant-admin')) return '/tenant-admin'
  if (roles.includes('annotator')) return '/my-tasks'
  if (roles.includes('reviewer')) return '/my-reviews'
  return '/403'
}
