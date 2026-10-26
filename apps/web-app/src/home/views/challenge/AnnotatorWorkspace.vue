<script setup lang="ts">
import { onMounted, ref, shallowRef } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Icon } from '@iconify/vue'
import { challengeApi } from '@/api'

interface AnnotatorTask {
  unit_id: number
  video_name: string
  video_duration: number | null
  status: string
  reject_count: number
  reject_reason: string | null
}

const router = useRouter()
const loading = shallowRef(false)
const tasks = ref<AnnotatorTask[]>([])

async function loadTasks() {
  loading.value = true
  try {
    const response = await challengeApi.myTasks()
    tasks.value = response.tasks ?? []
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '任务加载失败')
  } finally {
    loading.value = false
  }
}

function statusLabel(status: string) {
  return {
    assigned: '待标注',
    in_progress: '标注中',
    rejected: '待修改',
  }[status] ?? status
}

function statusType(status: string): 'primary' | 'warning' | 'danger' {
  if (status === 'rejected') return 'danger'
  if (status === 'in_progress') return 'warning'
  return 'primary'
}

function openTask(task: AnnotatorTask) {
  router.push({ name: 'annotate-video', params: { unitId: task.unit_id } })
}

onMounted(loadTasks)
</script>

<template>
  <section class="task-page">
    <header class="task-page__header">
      <div>
        <p class="task-page__eyebrow">ANNOTATOR QUEUE</p>
        <h1 class="task-page__title">
          <Icon icon="lucide:clipboard-list" />
          我的标注任务
        </h1>
        <p class="task-page__hint">这里只做任务选择；进入独立标注页后播放视频并划分片段。</p>
      </div>
      <el-button size="large" :loading="loading" @click="loadTasks">刷新任务</el-button>
    </header>

    <el-card shadow="never" class="task-page__card task-page__desktop">
      <el-table
        v-loading="loading"
        :data="tasks"
        row-key="unit_id"
        class="task-page__table"
        @row-click="openTask"
      >
        <el-table-column prop="unit_id" label="任务" width="86" />
        <el-table-column label="视频" min-width="280">
          <template #default="{ row }">
            <div class="task-page__video">
              <strong>{{ row.video_name }}</strong>
              <small>{{ row.video_duration == null ? '时长未知' : `${row.video_duration.toFixed(1)} 秒` }}</small>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="130">
          <template #default="{ row }">
            <el-tag :type="statusType(row.status)">
              {{ statusLabel(row.status) }}
              <template v-if="row.reject_count">（{{ row.reject_count }}）</template>
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="最近处理意见" min-width="260">
          <template #default="{ row }">
            <span v-if="row.reject_reason" class="task-page__reason">{{ row.reject_reason }}</span>
            <span v-else class="task-page__muted">暂无意见</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="140" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" @click.stop="openTask(row)">
              {{ row.status === 'rejected' ? '继续修改' : '开始标注' }}
            </el-button>
          </template>
        </el-table-column>
        <template #empty>
          <el-empty description="当前没有待处理任务，刷新后系统会补充演示任务" />
        </template>
      </el-table>
    </el-card>

    <div v-loading="loading" class="task-page__mobile">
      <article v-for="task in tasks" :key="task.unit_id" class="task-mobile-card">
        <div class="task-mobile-card__head">
          <span>任务 #{{ task.unit_id }}</span>
          <el-tag :type="statusType(task.status)">
            {{ statusLabel(task.status) }}
            <template v-if="task.reject_count">（{{ task.reject_count }}）</template>
          </el-tag>
        </div>
        <strong class="task-mobile-card__video">{{ task.video_name }}</strong>
        <span class="task-mobile-card__duration">
          {{ task.video_duration == null ? '时长未知' : `${task.video_duration.toFixed(1)} 秒` }}
        </span>
        <p class="task-mobile-card__reason">
          {{ task.reject_reason || '暂无处理意见' }}
        </p>
        <el-button type="primary" size="large" @click="openTask(task)">
          {{ task.status === 'rejected' ? '继续修改' : '开始标注' }}
        </el-button>
      </article>
      <el-empty
        v-if="!loading && tasks.length === 0"
        description="当前没有待处理任务，刷新后系统会补充演示任务"
      />
    </div>
  </section>
</template>

<style scoped>
.task-page {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.task-page__header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 24px;
}

.task-page__eyebrow {
  margin: 0 0 6px;
  color: var(--el-color-primary);
  font: 600 var(--y-font-size-sm) var(--y-font-family-mono);
  letter-spacing: 0.12em;
}

.task-page__title {
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 0;
  font-size: var(--y-font-size-3xl);
}

.task-page__hint,
.task-page__muted,
.task-page__video small {
  color: var(--el-text-color-secondary);
}

.task-page__card :deep(.el-card__body) {
  padding: 0;
}

.task-page__table {
  --el-table-row-height: 72px;
}

:deep(.el-table__row) {
  cursor: pointer;
}

.task-page__video {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 4px;
}

.task-page__video strong {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.task-page__reason {
  color: var(--el-color-danger);
}

.task-page__mobile {
  display: none;
}

.task-mobile-card {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 18px;
  border: 1px solid var(--lab-hairline);
  border-radius: 18px;
  background: #fff;
  box-shadow: var(--lab-shadow-soft);
}

.task-mobile-card__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  color: var(--lab-slate);
  font-size: 13px;
}

.task-mobile-card__video {
  color: var(--lab-ink);
  font-size: 16px;
  word-break: break-all;
}

.task-mobile-card__duration,
.task-mobile-card__reason {
  margin: 0;
  color: var(--lab-slate);
  font-size: 13px;
}

.task-mobile-card__reason {
  color: var(--lab-coral);
}

@media (max-width: 760px) {
  .task-page__header {
    align-items: flex-start;
    flex-direction: column;
  }

  .task-page__desktop {
    display: none;
  }

  .task-page__mobile {
    display: flex;
    min-height: 150px;
    flex-direction: column;
    gap: 12px;
  }
}
</style>
