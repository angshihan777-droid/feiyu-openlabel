<script setup lang="ts">
import {
  computed,
  onMounted,
  onUnmounted,
  ref,
  shallowRef,
  useTemplateRef,
  watch,
} from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { challengeApi } from '@/api'
import {
  totalDuration,
  validateIntervals,
  type VideoInterval,
} from '@/libs/intervals'
import FrameControls from './video-studio/FrameControls.vue'
import IntervalEditor from './video-studio/IntervalEditor.vue'
import ReviewActions from './video-studio/ReviewActions.vue'
import VideoPlayerPanel from './video-studio/VideoPlayerPanel.vue'
import type {
  AnnotationConfig,
  PanelMode,
  RejectHistoryItem,
  UnitDetail,
  WorkerOption,
} from './video-studio/types'

const props = withDefaults(defineProps<{
  unitId: number | null
  mode: PanelMode
  rejectHistory?: RejectHistoryItem[]
}>(), {
  rejectHistory: () => [],
})

const emit = defineEmits<{
  completed: []
}>()

const loading = shallowRef(false)
const saving = shallowRef(false)
const submitting = shallowRef(false)
const reviewing = shallowRef(false)
const detail = ref<UnitDetail | null>(null)
const intervals = ref<VideoInterval[]>([])
const currentTime = shallowRef(0)
const duration = shallowRef(0)
const fps = shallowRef(30)
const draftStart = shallowRef(0)
const draftEnd = shallowRef(0)
const draftLabel = shallowRef('')
const selectionPhase = shallowRef<'idle' | 'end'>('idle')
const previewUrl = shallowRef('')
const isPlaying = shallowRef(false)
const annotators = shallowRef<WorkerOption[]>([])
const playerRef = useTemplateRef<{
  pause: () => void
  seek: (time: number) => void
  togglePlayback: () => void
}>('playerRef')

const config = computed<AnnotationConfig>(() => (
  detail.value?.annotation_config
  ?? detail.value?.annotation_settings
  ?? {
    instructions: '',
    require_label: true,
    min_interval_seconds: 0.1,
    label_mode: 'free',
    labels: [],
    label_template: '',
    fps: 30,
    return_reasons: [],
  }
))

const videoUrl = computed(() => {
  const path = detail.value?.video.path
  return path ? challengeApi.mediaStreamUrl(path) : ''
})

const currentFrame = computed(() => Math.floor(currentTime.value * fps.value))
const totalFrames = computed(() => Math.floor(duration.value * fps.value))
const currentTotal = computed(() => totalDuration(intervals.value))
const profileName = computed(() => {
  if (props.mode === 'review') return '标注员：匿名'
  if (props.mode === 'admin' && detail.value?.annotator_name) {
    return `标注员：${detail.value.annotator_name}`
  }
  return ''
})

const submissionError = computed(() => {
  const validation = validateIntervals(
    intervals.value,
    duration.value > 0 ? duration.value : undefined,
  )
  if (!validation.valid) return validation.error ?? '标注区间无效'
  if (config.value.require_label && intervals.value.some((item) => !item.label?.trim())) {
    return '每个标注区间都必须选择或填写标签'
  }
  if (
    config.value.label_mode === 'preset'
    && intervals.value.some((item) => !config.value.labels.includes(item.label || ''))
  ) {
    return '请选择项目预设标签'
  }
  if (intervals.value.some(
    (item) => item.end - item.start < config.value.min_interval_seconds,
  )) {
    return `区间不能短于 ${config.value.min_interval_seconds} 秒`
  }
  return null
})

const selectionHint = computed(() => {
  if (props.mode !== 'annotate') return ''
  return selectionPhase.value === 'end'
    ? `开始帧 ${Math.floor(draftStart.value * fps.value)}，再按空格设置结束`
    : '点击视频区域后按空格设开始，再按一次设结束；←/→ 逐帧'
})

function roundTime(value: number) {
  return Math.round(Math.max(0, value) * 100) / 100
}

function seekTo(value: number) {
  playerRef.value?.seek(value)
}

function stepFrame(direction: -1 | 1) {
  playerRef.value?.pause()
  seekTo(currentTime.value + direction / fps.value)
}

function setStartFromPlayer() {
  draftStart.value = currentTime.value
  selectionPhase.value = 'end'
}

function setEndFromPlayer() {
  draftEnd.value = currentTime.value
}

function addInterval() {
  const start = Math.min(draftStart.value, draftEnd.value)
  const end = Math.max(draftStart.value, draftEnd.value)
  if (end <= start) {
    ElMessage.warning('结束帧必须晚于开始帧')
    return
  }
  intervals.value.push({
    start: roundTime(start),
    end: roundTime(end),
    label: draftLabel.value,
  })
  intervals.value.sort((a, b) => a.start - b.start)
  selectionPhase.value = 'idle'
}

function removeInterval(index: number) {
  intervals.value.splice(index, 1)
}

function handleShortcut(event: KeyboardEvent) {
  if (props.mode !== 'annotate') return
  const target = event.target as HTMLElement | null
  if (target?.closest('input, textarea, [contenteditable="true"], .el-select')) return
  if (event.code === 'ArrowLeft') {
    event.preventDefault()
    stepFrame(-1)
    return
  }
  if (event.code === 'ArrowRight') {
    event.preventDefault()
    stepFrame(1)
    return
  }
  if (event.code !== 'Space') return
  event.preventDefault()
  playerRef.value?.pause()
  if (selectionPhase.value === 'idle') {
    draftStart.value = currentTime.value
    selectionPhase.value = 'end'
    return
  }
  draftEnd.value = currentTime.value
  addInterval()
}

function normalizeIntervals() {
  return intervals.value.map((interval) => ({
    start: interval.start,
    end: interval.end,
    ...(interval.label?.trim() ? { label: interval.label.trim() } : {}),
  }))
}

async function loadDetail() {
  detail.value = null
  intervals.value = []
  currentTime.value = 0
  duration.value = 0
  previewUrl.value = ''
  selectionPhase.value = 'idle'
  if (props.unitId == null) return

  loading.value = true
  try {
    const response = (await challengeApi.getUnit(props.unitId)) as UnitDetail
    detail.value = response
    intervals.value = (response.current_label?.intervals ?? []).map((item) => ({ ...item }))
    duration.value = response.video.duration ?? 0
    fps.value = response.annotation_config?.fps
      ?? response.annotation_settings?.fps
      ?? 30
    draftStart.value = 0
    draftEnd.value = roundTime(Math.min(10 / fps.value, duration.value))
    if (props.mode === 'admin') {
      const pools = await challengeApi.userPools()
      annotators.value = pools.annotators ?? []
    }
  } finally {
    loading.value = false
  }
}

async function saveDraft() {
  if (props.unitId == null) return
  saving.value = true
  try {
    const response = await challengeApi.saveDraft(props.unitId, normalizeIntervals())
    if (detail.value) {
      detail.value.current_label.intervals = normalizeIntervals()
      detail.value.current_label.version = response.version
      detail.value.status = response.status
    }
    ElMessage.success('草稿已保存')
  } finally {
    saving.value = false
  }
}

async function submit() {
  if (props.unitId == null) return
  if (submissionError.value) {
    ElMessage.warning(submissionError.value)
    return
  }
  const confirmation = await ElMessageBox.confirm(
    `提交 ${intervals.value.length} 个区间，共 ${currentTotal.value.toFixed(2)} 秒？`,
    '提交标注',
    {
      confirmButtonText: '确认提交',
      cancelButtonText: '继续编辑',
      type: 'warning',
    },
  ).catch(() => null)
  if (!confirmation) return

  submitting.value = true
  try {
    await challengeApi.submit(props.unitId, { intervals: normalizeIntervals() })
    ElMessage.success('标注已提交，等待审核')
    emit('completed')
  } finally {
    submitting.value = false
  }
}

async function approve() {
  if (props.unitId == null) return
  const confirmation = await ElMessageBox.confirm(
    '确认该视频的区间与标签均符合要求？',
    '审核通过',
    {
      confirmButtonText: '通过',
      cancelButtonText: '再看一下',
      type: 'success',
    },
  ).catch(() => null)
  if (!confirmation) return
  reviewing.value = true
  try {
    await challengeApi.approve(props.unitId)
    ElMessage.success('审核已通过')
    emit('completed')
  } finally {
    reviewing.value = false
  }
}

async function reject() {
  if (props.unitId == null) return
  const result = await ElMessageBox.prompt('请输入具体、可执行的驳回原因', '驳回标注', {
    inputType: 'textarea',
    inputValidator: (value) => Boolean(value?.trim()) || '驳回原因不能为空',
    confirmButtonText: '确认驳回',
    cancelButtonText: '取消',
  }).catch(() => null)
  if (!result) return
  reviewing.value = true
  try {
    const response = await challengeApi.reject(props.unitId, result.value)
    ElMessage.warning(response.escalated ? '已升级管理员裁决' : '已退回标注员')
    emit('completed')
  } finally {
    reviewing.value = false
  }
}

async function returnVideo(payload: { code: string; detail: string }) {
  if (props.unitId == null) return
  await challengeApi.returnVideo(props.unitId, payload.code, payload.detail)
  ElMessage.success('视频已回退给租户管理员复核')
  emit('completed')
}

async function adminAction(payload: {
  action: 'confirm_issue' | 'return_to_annotator' | 'void'
  reason: string
}) {
  if (props.unitId == null) return
  const labels = {
    confirm_issue: '确认视频有问题',
    return_to_annotator: '退回标注员重标',
    void: '作废此任务',
  }
  const confirmation = await ElMessageBox.confirm(
    `确认执行“${labels[payload.action]}”？`,
    '管理员复核',
    {
      type: payload.action === 'void' ? 'warning' : 'info',
      confirmButtonText: '确认',
      cancelButtonText: '取消',
    },
  ).catch(() => null)
  if (!confirmation) return
  reviewing.value = true
  try {
    await challengeApi.adminReviewAction(props.unitId, {
      action: payload.action,
      reason: payload.reason.trim(),
    })
    ElMessage.success('管理员复核已保存')
    emit('completed')
  } finally {
    reviewing.value = false
  }
}

async function reassign(payload: { newAssigneeId: number; reason: string }) {
  if (props.unitId == null) return
  reviewing.value = true
  try {
    await challengeApi.adminReviewAction(props.unitId, {
      action: 'reassign',
      reason: payload.reason.trim(),
      new_assignee_id: payload.newAssigneeId,
    })
    ElMessage.success('任务已重新分配')
    emit('completed')
  } finally {
    reviewing.value = false
  }
}

function formatTime(value: string) {
  return new Date(value).toLocaleString('zh-CN')
}

function statusLabel(status: string) {
  return {
    assigned: '待标注',
    in_progress: '标注中',
    rejected: '待修改',
    under_review: '待审核',
    returned: '待管理员复核',
    escalated: '待管理员裁决',
    source_confirmed: '视频问题已确认',
    void: '已作废',
    approved: '已通过',
  }[status] ?? status
}

watch(() => props.unitId, loadDetail, { immediate: true })

onMounted(() => {
  window.addEventListener('keydown', handleShortcut)
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleShortcut)
})
</script>

<template>
  <el-card v-loading="loading" shadow="never" class="studio">
    <template #header>
      <div class="studio__head">
        <div>
          <p class="studio__eyebrow">
            {{ mode === 'annotate' ? 'ANNOTATION' : mode === 'review' ? 'REVIEW' : 'ADMIN CHECK' }}
          </p>
          <h2>{{ detail?.video.filename || '视频工作区' }}</h2>
        </div>
        <div class="studio__meta">
          <el-tag v-if="detail" effect="plain">{{ statusLabel(detail.status) }}</el-tag>
          <el-tag v-if="profileName" type="info">{{ profileName }}</el-tag>
        </div>
      </div>
    </template>

    <el-empty v-if="unitId == null" description="当前没有可展示的视频任务" />

    <template v-else-if="detail">
      <div class="studio__body">
        <section class="studio__viewer">
          <VideoPlayerPanel
            ref="playerRef"
            :video-url="videoUrl"
            :intervals="intervals"
            :current-time="currentTime"
            :duration="duration"
            @time-update="currentTime = $event"
            @duration-change="duration = $event"
            @preview-change="previewUrl = $event"
            @playing-change="isPlaying = $event"
            @timeline-input="seekTo"
            @interval-click="seekTo"
          />
          <FrameControls
            v-model:fps="fps"
            :current-frame="currentFrame"
            :total-frames="totalFrames"
            :current-time="currentTime"
            :preview-url="previewUrl"
            :selection-hint="selectionHint"
            :is-playing="isPlaying"
            @previous-frame="stepFrame(-1)"
            @toggle-playback="playerRef?.togglePlayback()"
            @next-frame="stepFrame(1)"
          />
        </section>

        <aside class="studio__side">
          <div class="studio__notice">
            <span>{{ config.instructions || '请按时间轴选择并核对动作片段。' }}</span>
          </div>

          <IntervalEditor
            v-model:intervals="intervals"
            v-model:start="draftStart"
            v-model:end="draftEnd"
            v-model:label="draftLabel"
            v-model:fps="fps"
            :mode="mode"
            :config="config"
            :duration="duration"
            :current-total="currentTotal"
            :submission-error="submissionError"
            @set-start="setStartFromPlayer"
            @set-end="setEndFromPlayer"
            @add="addInterval"
            @remove="removeInterval"
          />

          <el-alert
            v-if="detail.reject_reason"
            type="error"
            :closable="false"
            :title="`处理意见：${detail.reject_reason}`"
          />

          <section v-if="rejectHistory.length" class="studio__history">
            <h3>历史意见</h3>
            <p v-for="item in rejectHistory" :key="item.rejected_at">
              {{ formatTime(item.rejected_at) }}：{{ item.reason }}
            </p>
          </section>

          <ReviewActions
            :mode="mode"
            :saving="saving"
            :submitting="submitting"
            :reviewing="reviewing"
            :can-submit="!submissionError"
            :total="currentTotal"
            :count="intervals.length"
            :return-reasons="config.return_reasons"
            :annotators="annotators"
            @save="saveDraft"
            @submit="submit"
            @approve="approve"
            @reject="reject"
            @return-video="returnVideo"
            @admin-action="adminAction"
            @reassign="reassign"
          />
        </aside>
      </div>
    </template>
  </el-card>
</template>

<style scoped>
.studio {
  outline: none;
}

.studio :deep(.el-card__body) {
  padding: 20px;
}

.studio__head,
.studio__meta {
  display: flex;
  align-items: center;
  gap: 12px;
}

.studio__head {
  justify-content: space-between;
}

.studio__eyebrow {
  margin: 0 0 4px;
  color: var(--el-color-primary);
  font: 600 var(--y-font-size-xs) var(--y-font-family-mono);
  letter-spacing: 0.12em;
}

.studio h2,
.studio h3 {
  margin: 0;
}

.studio h2 {
  font-size: var(--y-font-size-2xl);
}

.studio h3 {
  font-size: var(--y-font-size-lg);
}

.studio__body {
  display: grid;
  grid-template-columns: minmax(0, 1.45fr) minmax(360px, 0.85fr);
  gap: 20px;
}

.studio__viewer,
.studio__side {
  min-width: 0;
}

.studio__side {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.studio__notice {
  padding: 12px 14px;
  border-left: 3px solid var(--el-color-primary);
  border-radius: 8px;
  color: var(--el-text-color-regular);
  background: var(--el-color-primary-light-9);
}

.studio__history {
  padding: 14px;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 10px;
}

.studio__history p {
  margin: 8px 0 0;
  color: var(--el-color-warning-dark-2);
}

@media (max-width: 1100px) {
  .studio__body {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 680px) {
  .studio__head {
    align-items: flex-start;
    flex-direction: column;
  }

  .studio__meta {
    flex-wrap: wrap;
  }
}
</style>
