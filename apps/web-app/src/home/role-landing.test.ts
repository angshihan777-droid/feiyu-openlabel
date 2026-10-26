import { describe, expect, it } from 'vitest'

import { roleLandingPath } from './role-landing'

describe('role landing path', () => {
  it('separates platform, tenant, and project administrators', () => {
    expect(roleLandingPath(['platform-admin'])).toBe('/platform-admin')
    expect(roleLandingPath(['admin'])).toBe('/tenant-admin')
    expect(roleLandingPath(['tenant-admin'])).toBe('/tenant-admin')
  })

  it('prioritizes project administration when business roles overlap', () => {
    expect(roleLandingPath(['annotator', 'tenant-admin'])).toBe('/tenant-admin')
  })

  it('routes separated annotation and review roles to different pages', () => {
    expect(roleLandingPath(['annotator'])).toBe('/my-tasks')
    expect(roleLandingPath(['reviewer'])).toBe('/my-reviews')
  })

  it('does not leak an unknown role into the admin page', () => {
    expect(roleLandingPath([])).toBe('/403')
  })
})
