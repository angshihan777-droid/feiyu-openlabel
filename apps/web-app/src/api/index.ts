import { jobConfig } from '@/states/job-config'
import { userAuth } from '@/states/UserState'
import { reqJson } from './req'

const bizBaseURL = '/api/v1/b'

export const capchaApi = {
  imgUri: '/api/v1/c/captcha/generate/',
  checkUri: '/api/v1/c/captcha/validate/',
  sendcode: '/api/v1/c/mobilecode/sendcode/',
  checkCode: '/api/v1/c/mobilecode/validate/',
}

export const emailCodeApi = {
  sendcode: '/api/v1/c/emailcode/sendcode/',
  checkUri: '/api/v1/c/emailcode/validate/',
}

const userApiBaseUri = '/api/v1/b/u/a'
export const userApi = {
  captcha_id: '',
  login: (data: any, header?: any) =>
    reqJson({ uri: `${userApiBaseUri}/noau/token`, method: 'POST', data, header }),
  refresh: (data: any) =>
    reqJson({ uri: `${userApiBaseUri}/noau/refresh`, method: 'POST', data }),
  register: (data: any, header?: any) =>
    reqJson({ uri: `${userApiBaseUri}/noau/register`, method: 'POST', data, header }),
  reset: (data: any, header?: any) =>
    reqJson({ uri: `${userApiBaseUri}/noau/reset-password`, method: 'POST', data, header }),
}

export const demoAuthApi = {
  status: () =>
    reqJson({ uri: `${userApiBaseUri}/noau/demo-login/status`, method: 'GET' }),
  login: (identity: 'platform-admin' | 'tenant-admin' | 'annotator' | 'reviewer') =>
    reqJson({
      uri: `${userApiBaseUri}/noau/demo-login/${identity}`,
      method: 'POST',
    }),
}

export const systemApi = {
  config: (data: any) =>
    reqJson({ uri: `${bizBaseURL}/system/config`, data, method: 'POST' }),
  user_info: (data: any) =>
    reqJson({ uri: `${bizBaseURL}/system/user_info`, data, method: 'POST' }),
  update_password: (data: any) =>
    reqJson({ uri: `${bizBaseURL}/system/update_password`, data, method: 'POST' }),
  update_account: (data: any) =>
    reqJson({ uri: `${bizBaseURL}/system/update_account`, data, method: 'POST' }),
}

export const openlabelApi = {
  classes: () =>
    reqJson({ uri: `${bizBaseURL}/openlabel/classes`, data: jobConfig, method: 'POST' }),
  domains: () =>
    reqJson({ uri: `${bizBaseURL}/openlabel/domains`, data: {}, method: 'GET' }),
  query: (params: any) =>
    reqJson({ uri: `${bizBaseURL}/openlabel/query`, data: params, method: 'POST' }),
}

export const metaApi = {
  getCurrentSeqMeta: () =>
    reqJson({ uri: `${bizBaseURL}/seq/meta`, data: jobConfig, method: 'POST' }),
  getCurrentStreamMeta: () =>
    reqJson({ uri: `${bizBaseURL}/seq/stream/meta`, data: jobConfig, method: 'POST' }),
}

export const projectsApi = {
  list: (params?: any) =>
    reqJson({ uri: `${bizBaseURL}/projects`, data: params, method: 'GET' }),
  create: (data: any) =>
    reqJson({ uri: `${bizBaseURL}/projects`, data, method: 'POST' }),
  get: (projectId: number) =>
    reqJson({ uri: `${bizBaseURL}/projects/${projectId}`, method: 'GET' }),
  update: (projectId: number, data: any) =>
    reqJson({ uri: `${bizBaseURL}/projects/${projectId}`, data, method: 'PATCH' }),
  remove: (projectId: number) =>
    reqJson({ uri: `${bizBaseURL}/projects/${projectId}`, method: 'DELETE' }),
}

export const labelsApi = {
  getLatest: (unitId: number) =>
    reqJson({ uri: `${bizBaseURL}/labels/units/${unitId}`, method: 'GET' }),
  listVersions: (unitId: number) =>
    reqJson({ uri: `${bizBaseURL}/labels/units/${unitId}/versions`, method: 'GET' }),
  getVersion: (unitId: number, version: number) =>
    reqJson({
      uri: `${bizBaseURL}/labels/units/${unitId}/versions/${version}`,
      method: 'GET',
    }),
  diff: (unitId: number, params: any) =>
    reqJson({ uri: `${bizBaseURL}/labels/units/${unitId}/diff`, data: params, method: 'GET' }),
  save: (unitId: number, data: any) =>
    reqJson({ uri: `${bizBaseURL}/labels/units/${unitId}`, data, method: 'POST' }),
  submit: (unitId: number, data: any) =>
    reqJson({ uri: `${bizBaseURL}/labels/units/${unitId}/submit`, data, method: 'POST' }),
}

export const batchesApi = {
  listBatches: (projectId: number, params?: any) =>
    reqJson({
      uri: `${bizBaseURL}/projects/${projectId}/batches`,
      data: params,
      method: 'GET',
    }),
  createBatch: (projectId: number, data: any) =>
    reqJson({
      uri: `${bizBaseURL}/projects/${projectId}/batches`,
      data,
      method: 'POST',
    }),
  getBatch: (batchId: number) =>
    reqJson({ uri: `${bizBaseURL}/batches/${batchId}`, method: 'GET' }),
  updateBatch: (batchId: number, data: any) =>
    reqJson({ uri: `${bizBaseURL}/batches/${batchId}`, data, method: 'PATCH' }),
  removeBatch: (batchId: number) =>
    reqJson({ uri: `${bizBaseURL}/batches/${batchId}`, method: 'DELETE' }),
  spawnBatch: (batchId: number, data?: any) =>
    reqJson({ uri: `${bizBaseURL}/batches/${batchId}/spawn`, data, method: 'POST' }),
  listUnits: (projectId: number, params?: any) =>
    reqJson({
      uri: `${bizBaseURL}/projects/${projectId}/units`,
      data: params,
      method: 'GET',
    }),
  claimUnit: (unitId: number) =>
    reqJson({ uri: `${bizBaseURL}/units/${unitId}/claim`, method: 'POST' }),
  assignUnit: (unitId: number, data: any) =>
    reqJson({ uri: `${bizBaseURL}/units/${unitId}/assign`, data, method: 'POST' }),
  releaseUnit: (unitId: number) =>
    reqJson({ uri: `${bizBaseURL}/units/${unitId}/release`, method: 'POST' }),
}

export const unitsApi = {
  list: (projectId: number, params?: any) =>
    reqJson({
      uri: `${bizBaseURL}/projects/${projectId}/units`,
      data: params,
      method: 'GET',
    }),
  claim: (unitId: number) =>
    reqJson({ uri: `${bizBaseURL}/units/${unitId}/claim`, method: 'POST' }),
  assign: (unitId: number, data: any) =>
    reqJson({ uri: `${bizBaseURL}/units/${unitId}/assign`, data, method: 'POST' }),
  release: (unitId: number) =>
    reqJson({ uri: `${bizBaseURL}/units/${unitId}/release`, method: 'POST' }),
  findByCoord: (params: {
    seq: string
    stream: string
    frame: number
    mission: string
  }) => reqJson({ uri: `${bizBaseURL}/units/by-coord`, data: params, method: 'GET' }),
  get: (unitId: number) =>
    reqJson({ uri: `${bizBaseURL}/units/${unitId}`, method: 'GET' }),
}

async function challengeUpload(file: File, projectId: number) {
  const body = new FormData()
  body.append('project_id', String(projectId))
  body.append('file', file, file.name)
  const response = await fetch(`${bizBaseURL}/media/upload`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${userAuth.value.access_token}` },
    body,
  })
  if (!response.ok) {
    const payload = await response.json().catch(() => null)
    throw new Error(
      payload?.statusText || payload?.detail || `上传失败 (${response.status})`,
    )
  }
  return response.json()
}

export const challengeApi = {
  myTasks: () => reqJson({ uri: `${bizBaseURL}/units/my-tasks`, method: 'GET' }),
  myReviews: () => reqJson({ uri: `${bizBaseURL}/units/my-reviews`, method: 'GET' }),
  escalated: () => reqJson({ uri: `${bizBaseURL}/units/escalated`, method: 'GET' }),
  getUnit: (unitId: number) =>
    reqJson({ uri: `${bizBaseURL}/units/${unitId}`, method: 'GET' }),
  saveDraft: (unitId: number, intervals: Array<{ start: number; end: number; label?: string }>) =>
    reqJson({
      uri: `${bizBaseURL}/units/${unitId}/draft`,
      data: { intervals },
      method: 'POST',
    }),
  returnVideo: (unitId: number, reasonCode: string, reason = '') =>
    reqJson({
      uri: `${bizBaseURL}/units/${unitId}/return-video`,
      data: { reason_code: reasonCode, reason },
      method: 'POST',
    }),
  adminReviewAction: (
    unitId: number,
    data: {
      action: 'confirm_issue' | 'return_to_annotator' | 'reassign' | 'void'
      reason?: string
      new_assignee_id?: number
    },
  ) =>
    reqJson({
      uri: `${bizBaseURL}/units/${unitId}/admin-review`,
      data,
      method: 'POST',
    }),
  submit: (unitId: number, data: any) =>
    reqJson({ uri: `${bizBaseURL}/units/${unitId}/submit`, data, method: 'POST' }),
  approve: (unitId: number) =>
    reqJson({ uri: `${bizBaseURL}/units/${unitId}/approve`, method: 'POST' }),
  reject: (unitId: number, reason: string) =>
    reqJson({
      uri: `${bizBaseURL}/units/${unitId}/reject`,
      data: { reason },
      method: 'POST',
    }),
  forceApprove: (unitId: number, note = '') =>
    reqJson({
      uri: `${bizBaseURL}/units/${unitId}/force-approve`,
      data: { note },
      method: 'POST',
    }),
  reassign: (unitId: number, newAssigneeId: number, reason = '') =>
    reqJson({
      uri: `${bizBaseURL}/units/${unitId}/reassign`,
      data: { new_assignee_id: newAssigneeId, reason },
      method: 'POST',
    }),
  markDifficult: (unitId: number, reason = '') =>
    reqJson({
      uri: `${bizBaseURL}/units/${unitId}/mark-difficult`,
      data: { reason },
      method: 'POST',
    }),
  dailyDuration: (params: {
    start_date: string
    end_date: string
    batch_id?: number
  }) => reqJson({ uri: `${bizBaseURL}/stats/daily-duration`, data: params, method: 'GET' }),
  exportStats: async (params: {
    batch_id: number
    start_date: string
    end_date: string
  }) => {
    const query = new URLSearchParams(
      Object.entries(params).map(([key, value]) => [key, String(value)]),
    )
    const response = await fetch(`${bizBaseURL}/stats/export?${query}`, {
      headers: { Authorization: `Bearer ${userAuth.value.access_token}` },
    })
    if (!response.ok) {
      const payload = await response.json().catch(() => null)
      throw new Error(
        payload?.statusText || payload?.detail || `导出失败 (${response.status})`,
      )
    }
    return response.blob()
  },
  uploadVideo: challengeUpload,
  listMedia: (projectId: number) =>
    reqJson({ uri: `${bizBaseURL}/media`, data: { project_id: projectId }, method: 'GET' }),
  userPools: () =>
    reqJson({ uri: `${bizBaseURL}/challenge/users/pools`, method: 'GET' }),
  mediaStreamUrl: (path: string) => {
    const streamPath = path.startsWith(`${bizBaseURL}/`)
      ? path
      : `${bizBaseURL}${path.startsWith('/') ? path : `/${path}`}`
    const token = encodeURIComponent(userAuth.value.access_token)
    return `${streamPath}${streamPath.includes('?') ? '&' : '?'}token=${token}`
  },
}

export const tenantAdminApi = {
  overview: () =>
    reqJson({ uri: `${bizBaseURL}/tenant-admin/overview`, method: 'GET' }),
  members: () =>
    reqJson({ uri: `${bizBaseURL}/tenant-admin/members`, method: 'GET' }),
  createMember: (role: 'annotator' | 'reviewer') =>
    reqJson({
      uri: `${bizBaseURL}/tenant-admin/members`,
      data: { role },
      method: 'POST',
    }),
  removeMember: (userId: number) =>
    reqJson({ uri: `${bizBaseURL}/tenant-admin/members/${userId}`, method: 'DELETE' }),
  reviews: () =>
    reqJson({ uri: `${bizBaseURL}/tenant-admin/reviews`, method: 'GET' }),
  videoResults: (kind: 'success' | 'problem') =>
    reqJson({ uri: `${bizBaseURL}/tenant-admin/video-results/${kind}`, method: 'GET' }),
  projectVideoConfig: (projectId: number) =>
    reqJson({ uri: `${bizBaseURL}/projects/${projectId}/video-config`, method: 'GET' }),
  saveProjectVideoConfig: (projectId: number, data: any) =>
    reqJson({
      uri: `${bizBaseURL}/projects/${projectId}/video-config`,
      data,
      method: 'PUT',
    }),
  downloadWorkbenchCsv: async (kind: 'success' | 'problem') => {
    const response = await fetch(`${bizBaseURL}/tenant-admin/export/${kind}.csv`, {
      headers: { Authorization: `Bearer ${userAuth.value.access_token}` },
    })
    if (!response.ok) {
      const payload = await response.json().catch(() => null)
      throw new Error(payload?.statusText || payload?.detail || `导出失败 (${response.status})`)
    }
    return response.blob()
  },
  annotationSettings: () =>
    reqJson({ uri: `${bizBaseURL}/tenant-admin/annotation-settings`, method: 'GET' }),
  saveAnnotationSettings: (data: {
    instructions: string
    require_label: boolean
    min_interval_seconds: number
  }) =>
    reqJson({
      uri: `${bizBaseURL}/tenant-admin/annotation-settings`,
      data,
      method: 'PUT',
    }),
}

export const platformAdminApi = {
  tenants: () =>
    reqJson({ uri: '/api/v1/p/platform/tenants', method: 'GET' }),
  createTenant: (data: {
    name: string
    slug: string
    admin_email: string
    admin_password: string
  }) =>
    reqJson({ uri: '/api/v1/p/platform/tenants', data, method: 'POST' }),
  deleteTenant: (slug: string) =>
    reqJson({ uri: `/api/v1/p/platform/tenants/${slug}`, method: 'DELETE' }),
}

export const meApi = {
  getProfile: () => reqJson({ uri: `${bizBaseURL}/me`, method: 'GET' }),
  updateProfile: (data: any) =>
    reqJson({ uri: `${bizBaseURL}/me`, data, method: 'PATCH' }),
  changePassword: (data: any) =>
    reqJson({ uri: `${bizBaseURL}/me/password`, data, method: 'POST' }),
  getPreferences: () =>
    reqJson({ uri: `${bizBaseURL}/me/preferences`, method: 'GET' }),
  updatePreferences: (data: any) =>
    reqJson({ uri: `${bizBaseURL}/me/preferences`, data, method: 'PATCH' }),
}

export const notificationApi = {
  list: (params?: any) =>
    reqJson({ uri: `${bizBaseURL}/notifications`, data: params, method: 'GET' }),
  unread: () =>
    reqJson({ uri: `${bizBaseURL}/notifications/unread`, method: 'GET' }),
  markRead: (id: string) =>
    reqJson({ uri: `${bizBaseURL}/notifications/${id}/read`, method: 'POST' }),
  markAllRead: () =>
    reqJson({ uri: `${bizBaseURL}/notifications/read-all`, method: 'POST' }),
}

export const NOTIFICATION_STREAM_URL = `${bizBaseURL}/notifications/stream`
