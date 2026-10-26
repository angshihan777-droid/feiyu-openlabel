/**
 * Stage 9.5 — anno 工作台关联 Stage 7 unit。
 *
 * 给定 jobConfig(seq/stream/frame/mission),反查:
 *  - unit: 找不到 = 老 AnnoJob,前端走 frame_save 兼容路径
 *  - instance: 最近一个 workflow instance(含 stage_history)
 *  - latestReject: 最近一次驳回原因(若有),用于横幅显示
 *
 * 当 frame / seq / stream 变化时自动重新拉取。
 */
import { computed, ref, watch } from 'vue'
import { challengeApi, unitsApi } from '@/api'
import { jobConfig } from '@/states/job-config'
import type { RejectReason, Unit, WorkflowInstance } from '@/types/api'

const unit = ref<Unit | null>(null)
const instance = ref<WorkflowInstance | null>(null)
const loading = ref(false)
const notFound = ref(false) // 404 = 老 AnnoJob,无 unit 绑定

interface LatestReject extends RejectReason {
  stage_code?: string
  actor_id?: number
  finished_at?: string
}

const latestReject = computed<LatestReject | null>(() => {
  if (unit.value?.current_reject_reason) {
    return {
      category: 'other',
      severity: 'major',
      note: unit.value.current_reject_reason,
      finished_at: unit.value.reviewed_at,
    } as LatestReject
  }
  const inst = instance.value
  if (!inst || !inst.stage_history) return null
  // 倒序找最近一次 rejected
  for (let i = inst.stage_history.length - 1; i >= 0; i--) {
    const r: any = inst.stage_history[i]
    if (r?.decision === 'rejected' && r.reject_reason) {
      return {
        ...(r.reject_reason as RejectReason),
        stage_code: r.stage_code,
        actor_id: r.actor_id,
        finished_at: r.finished_at || r.started_at,
      }
    }
  }
  return null
})

const isRejectedUnit = computed(() => {
  const inst = instance.value
  if (!inst) return false
  // 实例仍在 in_progress/arbitrate/rejected 且有驳回历史 → 返工中
  if (inst.current_status === 'approved') return false
  return latestReject.value != null
})

const hasUnit = computed(() => unit.value != null)

const reload = async () => {
  if (!jobConfig.inited) return

  loading.value = true
  try {
    if (jobConfig.unit_id > 0) {
      const response: any = await challengeApi.getUnit(jobConfig.unit_id)
      const detail = response?.data?.unit_id ? response.data : response
      if (!detail?.unit_id || !detail?.video) {
        throw new Error('任务详情响应缺少视频信息')
      }
      unit.value = {
        id: detail.unit_id,
        tenant_id: '',
        project_id: 0,
        batch_id: detail.batch_id,
        seq: `unit:${detail.unit_id}`,
        stream: detail.video?.filename || '',
        frame: 0,
        frame_start: 0,
        frame_end: 0,
        mission: jobConfig.mission,
        assignee_id: detail.assignee_id,
        reviewer_id: detail.reviewer_id,
        current_stage: null,
        stage_status: detail.status,
        status: detail.status,
        reject_count: detail.reject_count,
        max_rejects: 2,
        current_reject_reason: detail.reject_reason,
        submitted_at: null,
        reviewed_at: null,
        approved_at: null,
        data_version: detail.current_label?.version ?? 0,
        created_at: '',
        updated_at: '',
      } as unknown as Unit
      instance.value = null
      notFound.value = false
      return
    }
    if (!jobConfig.seq || !jobConfig.stream || !jobConfig.mission) return
    const res = await unitsApi.findByCoord({
      seq: jobConfig.seq,
      stream: jobConfig.stream,
      frame: jobConfig.frame,
      mission: jobConfig.mission,
    })
    unit.value = res?.unit ?? null
    instance.value = res?.instance ?? null
    notFound.value = unit.value == null
  } catch {
    // 静默:不阻塞 anno 主流程
    unit.value = null
    instance.value = null
    notFound.value = true
  } finally {
    loading.value = false
  }
}

// jobConfig 是 reactive,watch 它的关键字段
watch(
  () => [jobConfig.unit_id, jobConfig.seq, jobConfig.stream, jobConfig.frame, jobConfig.mission, jobConfig.inited],
  () => {
    reload()
  },
  { immediate: true, deep: true },
)

export const useUnit = () => {
  return {
    unit,
    instance,
    latestReject,
    isRejectedUnit,
    hasUnit,
    notFound,
    loading,
    reload,
  }
}
