<script setup lang="ts">
import { onMounted, ref, shallowRef } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Icon } from '@iconify/vue'
import { challengeApi } from '@/api'

interface ReviewTask {
  unit_id: number
  video_name: string
  total_duration: number
  submitted_at: string | null
}

const router = useRouter()
const loading = shallowRef(false)
const tasks = ref<ReviewTask[]>([])

async function loadTasks() {
  loading.value = true
  try {
    const response = await challengeApi.myReviews()
    tasks.value = response.tasks ?? []
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '审核任务加载失败')
  } finally {
    loading.value = false
  }
}

function formatTime(value: string | null) {
  return value ? new Date(value).toLocaleString('zh-CN') : '—'
}

function openReview(task: ReviewTask) {
  router.push({ name: 'review-video', params: { unitId: task.unit_id } })
}

onMounted(loadTasks)
</script>

<template>
  <section class="review-queue">
    <header class="review-queue__header">
      <div>
        <p class="review-queue__eyebrow">REVIEW QUEUE</p>
        <h1 class="review-queue__title">
          <Icon icon="lucide:scan-eye" />
          我的审核任务
        </h1>
        <p class="review-queue__hint">任务列表与视频审核分开；标注员身份保持匿名。</p>
      </div>
      <el-button size="large" :loading="loading" @click="loadTasks">刷新任务</el-button>
    </header>

    <el-card shadow="never" class="review-queue__card review-queue__desktop">
      <el-table v-loading="loading" :data="tasks" row-key="unit_id" @row-click="openReview">
        <el-table-column prop="unit_id" label="任务" width="86" />
        <el-table-column label="视频 / 提交时间" min-width="320">
          <template #default="{ row }">
            <div class="review-queue__video">
              <strong>{{ row.video_name }}</strong>
              <small>{{ formatTime(row.submitted_at) }}</small>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="有效时长" width="130">
          <template #default="{ row }">{{ row.total_duration.toFixed(2) }} 秒</template>
        </el-table-column>
        <el-table-column label="标注员" width="120">
          <template #default><el-tag>匿名</el-tag></template>
        </el-table-column>
        <el-table-column label="操作" width="140" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" @click.stop="openReview(row)">开始审核</el-button>
          </template>
        </el-table-column>
        <template #empty>
          <el-empty description="当前没有待审核任务，刷新后系统会补充演示任务" />
        </template>
      </el-table>
    </el-card>

    <div v-loading="loading" class="review-queue__mobile">
      <article v-for="task in tasks" :key="task.unit_id" class="review-mobile-card">
        <div class="review-mobile-card__head">
          <span>任务 #{{ task.unit_id }}</span>
          <el-tag>匿名标注员</el-tag>
        </div>
        <strong class="review-mobile-card__video">{{ task.video_name }}</strong>
        <p>提交时间：{{ formatTime(task.submitted_at) }}</p>
        <p>有效时长：{{ task.total_duration.toFixed(2) }} 秒</p>
        <el-button type="primary" size="large" @click="openReview(task)">开始审核</el-button>
      </article>
      <el-empty
        v-if="!loading && tasks.length === 0"
        description="当前没有待审核任务，刷新后系统会补充演示任务"
      />
    </div>
  </section>
</template>

<style scoped>
.review-queue {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.review-queue__header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 24px;
}

.review-queue__eyebrow {
  margin: 0 0 6px;
  color: var(--el-color-primary);
  font: 600 var(--y-font-size-sm) var(--y-font-family-mono);
  letter-spacing: 0.12em;
}

.review-queue__title {
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 0;
  font-size: var(--y-font-size-3xl);
}

.review-queue__hint,
.review-queue__video small {
  color: var(--el-text-color-secondary);
}

.review-queue__card :deep(.el-card__body) {
  padding: 0;
}

:deep(.el-table__row) {
  cursor: pointer;
}

.review-queue__video {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.review-queue__video strong {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.review-queue__mobile {
  display: none;
}

.review-mobile-card {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 18px;
  border: 1px solid var(--lab-hairline);
  border-radius: 18px;
  background: #fff;
  box-shadow: var(--lab-shadow-soft);
}

.review-mobile-card__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  color: var(--lab-slate);
  font-size: 13px;
}

.review-mobile-card__video {
  color: var(--lab-ink);
  font-size: 16px;
  word-break: break-all;
}

.review-mobile-card p {
  margin: 0;
  color: var(--lab-slate);
  font-size: 13px;
}

@media (max-width: 760px) {
  .review-queue__header {
    align-items: flex-start;
    flex-direction: column;
  }

  .review-queue__desktop {
    display: none;
  }

  .review-queue__mobile {
    display: flex;
    min-height: 150px;
    flex-direction: column;
    gap: 12px;
  }
}
</style>
