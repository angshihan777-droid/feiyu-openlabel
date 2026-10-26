<script setup lang="ts">
import { computed, onMounted, ref, shallowRef } from 'vue'
import { ElMessage } from 'element-plus'
import { Icon } from '@iconify/vue'
import { challengeApi, tenantAdminApi } from '@/api'

interface Overview {
  total_tasks: number
  completed_tasks: number
  completion_rate: number
  reviewed_tasks: number
  approved_tasks: number
  approval_rate: number
  batch_count: number
  active_annotators: number
  active_reviewers: number
  returned_tasks: number
  problem_tasks: number
  status_counts: Record<string, number>
}

interface VideoInterval {
  start: number
  end: number
  label?: string
}

interface VideoResult {
  unit_id: number
  video_id: number | null
  video_name: string
  video_url: string | null
  video_duration: number | null
  status: string
  reason: string | null
  intervals: VideoInterval[]
  total_duration: number
  annotator_name: string
  reviewer_name: string
  updated_at: string
}

type ResultKind = 'success' | 'problem'

const loading = shallowRef(false)
const downloading = shallowRef<ResultKind | null>(null)
const overview = shallowRef<Overview | null>(null)
const successVideos = ref<VideoResult[]>([])
const problemVideos = ref<VideoResult[]>([])
const activeKind = shallowRef<ResultKind>('success')
const previewVideo = shallowRef<VideoResult | null>(null)
const previewOpen = shallowRef(false)

const activeVideos = computed(() =>
  activeKind.value === 'success' ? successVideos.value : problemVideos.value,
)

const previewUrl = computed(() =>
  previewVideo.value?.video_url
    ? challengeApi.mediaStreamUrl(previewVideo.value.video_url)
    : '',
)

const progressSegments = computed(() => {
  const data = overview.value
  if (!data) return []
  const approved = data.status_counts?.approved ?? data.approved_tasks ?? 0
  const problem = data.problem_tasks ?? 0
  const reviewing = (data.status_counts?.under_review ?? 0)
    + (data.status_counts?.submitted ?? 0)
  const pending = Math.max(data.total_tasks - approved - problem - reviewing, 0)
  return [
    { label: '已通过', value: approved, color: 'var(--el-color-success)' },
    { label: '问题视频', value: problem, color: 'var(--el-color-danger)' },
    { label: '审核中', value: reviewing, color: 'var(--el-color-warning)' },
    { label: '待处理', value: pending, color: 'var(--el-color-primary)' },
  ]
})

const donutStyle = computed(() => {
  const total = Math.max(
    progressSegments.value.reduce((sum, item) => sum + item.value, 0),
    1,
  )
  let start = 0
  const pieces = progressSegments.value.map((item) => {
    const end = start + (item.value / total) * 100
    const piece = `${item.color} ${start}% ${end}%`
    start = end
    return piece
  })
  return {
    background: `conic-gradient(${pieces.join(', ') || '#e5e7eb 0 100%'})`,
  }
})

const completionPercent = computed(() =>
  Math.round((overview.value?.completion_rate ?? 0) * 100),
)
const approvalPercent = computed(() =>
  Math.round((overview.value?.approval_rate ?? 0) * 100),
)

async function load() {
  loading.value = true
  try {
    const [summary, success, problem] = await Promise.all([
      tenantAdminApi.overview(),
      tenantAdminApi.videoResults('success'),
      tenantAdminApi.videoResults('problem'),
    ])
    overview.value = summary
    successVideos.value = success.items ?? []
    problemVideos.value = problem.items ?? []
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '租户统计加载失败')
  } finally {
    loading.value = false
  }
}

async function download(kind: ResultKind) {
  downloading.value = kind
  try {
    const blob = await tenantAdminApi.downloadWorkbenchCsv(kind)
    const link = document.createElement('a')
    link.href = URL.createObjectURL(blob)
    link.download = kind === 'success' ? 'success-videos.csv' : 'problem-videos.csv'
    link.click()
    URL.revokeObjectURL(link.href)
    ElMessage.success('CSV 已开始下载')
  } finally {
    downloading.value = null
  }
}

function selectKind(kind: ResultKind) {
  activeKind.value = kind
}

function openVideo(row: VideoResult) {
  previewVideo.value = row
  previewOpen.value = true
}

function formatTime(value: string) {
  return value ? new Date(value).toLocaleString('zh-CN') : '—'
}

function statusLabel(status: string) {
  return {
    approved: '已通过',
    returned: '标注员回退',
    rejected: '审核退回',
    escalated: '升级裁决',
    source_confirmed: '视频问题已确认',
    void: '已作废',
    difficult_sample: '困难样本',
  }[status] ?? status
}

onMounted(load)
</script>

<template>
  <section v-loading="loading" class="overview">
    <header class="overview__header">
      <div>
        <p>OVERVIEW</p>
        <h3>标注进度与视频结果</h3>
        <span>状态、质量趋势和视频结果集中在概览中查看与导出。</span>
      </div>
      <div class="overview__exports">
        <el-button :loading="downloading === 'success'" @click="download('success')">
          <Icon icon="lucide:download" /> 成功视频 CSV
        </el-button>
        <el-button type="warning" plain :loading="downloading === 'problem'" @click="download('problem')">
          <Icon icon="lucide:download" /> 失败视频 CSV
        </el-button>
        <el-button :loading="loading" @click="load">刷新</el-button>
      </div>
    </header>

    <template v-if="overview">
      <div class="overview__metrics">
        <el-card shadow="never">
          <span>任务总数</span>
          <strong>{{ overview.total_tasks }}</strong>
          <small>{{ overview.batch_count }} 个批次</small>
        </el-card>
        <el-card shadow="never">
          <span>已完成</span>
          <strong>{{ overview.completed_tasks }}</strong>
          <small>完成度 {{ completionPercent }}%</small>
        </el-card>
        <el-card shadow="never">
          <span>问题视频</span>
          <strong class="danger">{{ overview.problem_tasks }}</strong>
          <small>{{ overview.returned_tasks }} 条已回退或确认有问题</small>
        </el-card>
        <el-card shadow="never">
          <span>作业人员</span>
          <strong>{{ overview.active_annotators }} / {{ overview.active_reviewers }}</strong>
          <small>标注员 / 审核员</small>
        </el-card>
      </div>

      <div class="overview__charts">
        <el-card shadow="never" class="overview__chart-card">
          <template #header><span>任务状态分布</span></template>
          <div class="overview__donut-wrap">
            <div class="overview__donut" :style="donutStyle">
              <div class="overview__donut-hole">
                <strong>{{ overview.total_tasks }}</strong>
                <span>全部任务</span>
              </div>
            </div>
            <div class="overview__legend">
              <div v-for="item in progressSegments" :key="item.label">
                <i :style="{ background: item.color }" />
                <span>{{ item.label }}</span>
                <strong>{{ item.value }}</strong>
              </div>
            </div>
          </div>
        </el-card>

        <el-card shadow="never" class="overview__chart-card">
          <template #header><span>质量指标</span></template>
          <div class="overview__bars">
            <div class="overview__bar-row">
              <div><span>任务完成度</span><strong>{{ completionPercent }}%</strong></div>
              <div class="overview__bar"><i :style="{ width: `${completionPercent}%` }" /></div>
            </div>
            <div class="overview__bar-row">
              <div><span>审核通过率</span><strong>{{ approvalPercent }}%</strong></div>
              <div class="overview__bar success"><i :style="{ width: `${approvalPercent}%` }" /></div>
            </div>
            <div class="overview__quality-note">
              <Icon icon="lucide:badge-check" />
              <span>终审通过 {{ overview.approved_tasks }} / 已审核 {{ overview.reviewed_tasks }}</span>
            </div>
          </div>
        </el-card>
      </div>

      <div class="overview__result-boxes">
        <button
          type="button"
          class="overview__result-box success"
          :class="{ active: activeKind === 'success' }"
          @click="selectKind('success')"
        >
          <span class="overview__result-icon"><Icon icon="lucide:circle-check-big" /></span>
          <div>
            <small>PASSED VIDEOS</small>
            <strong>已通过视频</strong>
            <span>{{ successVideos.length }} 个视频文件</span>
          </div>
          <Icon icon="lucide:arrow-right" />
        </button>
        <button
          type="button"
          class="overview__result-box problem"
          :class="{ active: activeKind === 'problem' }"
          @click="selectKind('problem')"
        >
          <span class="overview__result-icon"><Icon icon="lucide:circle-x" /></span>
          <div>
            <small>FAILED / RETURNED</small>
            <strong>失败与问题视频</strong>
            <span>{{ problemVideos.length }} 个视频文件</span>
          </div>
          <Icon icon="lucide:arrow-right" />
        </button>
      </div>

      <el-card shadow="never" class="overview__results">
        <template #header>
          <div class="overview__results-head">
            <span>{{ activeKind === 'success' ? '已通过视频文件' : '失败与问题视频文件' }}</span>
            <el-tag :type="activeKind === 'success' ? 'success' : 'danger'">
              {{ activeVideos.length }} 条
            </el-tag>
          </div>
        </template>
        <el-table :data="activeVideos" row-key="unit_id" @row-click="openVideo">
          <el-table-column prop="unit_id" label="任务" width="76" />
          <el-table-column label="视频文件" min-width="280" show-overflow-tooltip>
            <template #default="{ row }">
              <div class="overview__video-cell">
                <strong>{{ row.video_name }}</strong>
                <small>{{ row.video_duration ? `${row.video_duration.toFixed(1)} 秒` : '时长未知' }}</small>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="结果" width="140">
            <template #default="{ row }">
              <el-tag :type="row.status === 'approved' ? 'success' : 'danger'">
                {{ statusLabel(row.status) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="失败原因" min-width="220">
            <template #default="{ row }">
              <span v-if="row.reason" class="overview__reason">{{ row.reason }}</span>
              <span v-else class="overview__muted">—</span>
            </template>
          </el-table-column>
          <el-table-column prop="annotator_name" label="标注员" min-width="190" show-overflow-tooltip />
          <el-table-column label="更新时间" width="170">
            <template #default="{ row }">{{ formatTime(row.updated_at) }}</template>
          </el-table-column>
          <template #empty>
            <el-empty :description="activeKind === 'success' ? '暂无已通过视频' : '暂无失败或问题视频'" />
          </template>
        </el-table>
      </el-card>
    </template>

    <el-dialog v-model="previewOpen" :title="previewVideo?.video_name || '视频详情'" width="760px">
      <video
        v-if="previewUrl"
        class="overview__preview-video"
        :src="previewUrl"
        controls
        preload="metadata"
      />
      <el-descriptions v-if="previewVideo" :column="2" border>
        <el-descriptions-item label="任务">{{ previewVideo.unit_id }}</el-descriptions-item>
        <el-descriptions-item label="结果">{{ statusLabel(previewVideo.status) }}</el-descriptions-item>
        <el-descriptions-item label="标注员">{{ previewVideo.annotator_name }}</el-descriptions-item>
        <el-descriptions-item label="审核员">{{ previewVideo.reviewer_name || '—' }}</el-descriptions-item>
        <el-descriptions-item label="有效时长">{{ previewVideo.total_duration.toFixed(2) }} 秒</el-descriptions-item>
        <el-descriptions-item label="更新时间">{{ formatTime(previewVideo.updated_at) }}</el-descriptions-item>
        <el-descriptions-item label="原因" :span="2">{{ previewVideo.reason || '—' }}</el-descriptions-item>
      </el-descriptions>
    </el-dialog>
  </section>
</template>

<style scoped>
.overview {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.overview__header,
.overview__exports,
.overview__results-head {
  display: flex;
  align-items: center;
  gap: 12px;
}

.overview__header {
  justify-content: space-between;
}

.overview__header p {
  margin: 0 0 4px;
  color: var(--el-color-primary);
  font: 600 var(--y-font-size-xs) var(--y-font-family-mono);
  letter-spacing: 0.1em;
}

.overview__header h3 {
  margin: 0;
  font-size: var(--y-font-size-2xl);
}

.overview__header span {
  color: var(--el-text-color-secondary);
}

.overview__exports {
  flex-wrap: wrap;
}

.overview__metrics {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 16px;
}

.overview__metrics :deep(.el-card__body) {
  display: flex;
  min-height: 142px;
  flex-direction: column;
  gap: 10px;
}

.overview__metrics span,
.overview__metrics small {
  color: var(--el-text-color-secondary);
}

.overview__metrics strong {
  font-size: var(--y-font-size-3xl);
}

.overview__metrics .danger {
  color: var(--el-color-danger);
}

.overview__charts {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.overview__donut-wrap {
  display: grid;
  grid-template-columns: 180px minmax(0, 1fr);
  gap: 28px;
  align-items: center;
  min-height: 220px;
}

.overview__donut {
  display: grid;
  width: 180px;
  height: 180px;
  border-radius: 50%;
  place-items: center;
}

.overview__donut-hole {
  display: flex;
  width: 112px;
  height: 112px;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: var(--el-bg-color);
  border-radius: 50%;
}

.overview__donut-hole strong {
  font-size: var(--y-font-size-3xl);
}

.overview__donut-hole span,
.overview__legend span {
  color: var(--el-text-color-secondary);
}

.overview__legend {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.overview__legend > div {
  display: grid;
  grid-template-columns: 10px 1fr auto;
  gap: 10px;
  align-items: center;
}

.overview__legend i {
  width: 10px;
  height: 10px;
  border-radius: 50%;
}

.overview__bars {
  display: flex;
  flex-direction: column;
  gap: 26px;
  padding: 20px 4px;
}

.overview__bar-row > div:first-child {
  display: flex;
  justify-content: space-between;
  margin-bottom: 10px;
}

.overview__bar {
  height: 14px;
  overflow: hidden;
  background: var(--el-fill-color-dark);
  border-radius: 999px;
}

.overview__bar i {
  display: block;
  height: 100%;
  background: var(--el-color-primary);
  border-radius: inherit;
}

.overview__bar.success i {
  background: var(--el-color-success);
}

.overview__quality-note {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--el-text-color-secondary);
}

.overview__result-boxes {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.overview__result-box {
  display: grid;
  grid-template-columns: auto 1fr auto;
  gap: 18px;
  align-items: center;
  padding: 22px;
  text-align: left;
  cursor: pointer;
  background: var(--el-bg-color);
  border: 2px solid transparent;
  border-radius: 16px;
  box-shadow: var(--el-box-shadow-lighter);
}

.overview__result-box.success {
  color: var(--el-color-success-dark-2);
  background: var(--el-color-success-light-9);
}

.overview__result-box.problem {
  color: var(--el-color-danger-dark-2);
  background: var(--el-color-danger-light-9);
}

.overview__result-box.active {
  border-color: currentColor;
}

.overview__result-icon {
  display: grid;
  width: 54px;
  height: 54px;
  font-size: 28px;
  background: var(--el-bg-color);
  border-radius: 14px;
  place-items: center;
}

.overview__result-box div {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.overview__result-box small {
  font: 600 var(--y-font-size-xs) var(--y-font-family-mono);
  letter-spacing: 0.08em;
}

.overview__result-box strong {
  color: var(--el-text-color-primary);
  font-size: var(--y-font-size-xl);
}

.overview__result-box span {
  color: var(--el-text-color-secondary);
}

.overview__results-head {
  justify-content: space-between;
}

.overview__video-cell {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.overview__video-cell small,
.overview__muted {
  color: var(--el-text-color-secondary);
}

.overview__reason {
  color: var(--el-color-danger);
}

:deep(.overview__results .el-table__row) {
  cursor: pointer;
}

.overview__preview-video {
  width: 100%;
  max-height: 460px;
  margin-bottom: 18px;
  background: #080b10;
  border-radius: 10px;
}

@media (max-width: 980px) {
  .overview__header {
    align-items: flex-start;
    flex-direction: column;
  }

  .overview__metrics,
  .overview__charts,
  .overview__result-boxes {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 560px) {
  .overview__donut-wrap {
    grid-template-columns: 1fr;
    justify-items: center;
  }

  .overview__exports {
    width: 100%;
  }
}
</style>
