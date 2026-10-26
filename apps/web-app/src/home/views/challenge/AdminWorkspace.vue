<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Icon } from '@iconify/vue'
import { challengeApi } from '@/api'
import AdminStatsPanel from './AdminStatsPanel.vue'

interface EscalatedTask {
  unit_id: number
  video_name: string
  batch_name: string | null
  annotator_id: number
  annotator_name: string
  reviewer_id: number
  reviewer_name: string
  reject_count: number
  current_intervals: Array<{ start: number; end: number; label?: string }>
  reject_history: Array<Record<string, any>>
}

const loading = ref(false)
const tasks = ref<EscalatedTask[]>([])

async function loadTasks() {
  loading.value = true
  try {
    const response = await challengeApi.escalated()
    tasks.value = response.tasks ?? []
  } finally {
    loading.value = false
  }
}

async function forceApprove(task: EscalatedTask) {
  const result = await ElMessageBox.prompt('填写裁决说明（可选）', '强制通过', {
    inputPlaceholder: '例如：审核标准过严，标注可接受',
    confirmButtonText: '强制通过',
    cancelButtonText: '取消',
  }).catch(() => null)
  if (!result) return
  await challengeApi.forceApprove(task.unit_id, result.value)
  ElMessage.success('已强制通过')
  await loadTasks()
}

async function reassign(task: EscalatedTask) {
  const result = await ElMessageBox.prompt('输入批次内其他标注员 ID', '重新分配', {
    inputPattern: /^\d+$/,
    inputErrorMessage: '请输入数字 ID',
    confirmButtonText: '重新分配',
    cancelButtonText: '取消',
  }).catch(() => null)
  if (!result) return
  await challengeApi.reassign(task.unit_id, Number(result.value), '管理员重新分配')
  ElMessage.success('已重新分配')
  await loadTasks()
}

async function markDifficult(task: EscalatedTask) {
  const result = await ElMessageBox.prompt('填写困难样本原因', '标记困难样本', {
    inputValidator: (value) => Boolean(value?.trim()) || '请填写原因',
    confirmButtonText: '确认',
    cancelButtonText: '取消',
  }).catch(() => null)
  if (!result) return
  await challengeApi.markDifficult(task.unit_id, result.value)
  ElMessage.success('已标记困难样本')
  await loadTasks()
}

onMounted(loadTasks)
</script>

<template>
  <section class="admin">
    <header class="admin__header">
      <div>
        <h2 class="admin__title">
          <Icon icon="lucide:shield-check" />
          管理员裁决与统计
        </h2>
        <p class="admin__hint">管理员可看到标注员、审核员真实身份和完整驳回历史。</p>
      </div>
      <div class="admin__actions">
        <el-button @click="$router.push('/batches')">批次管理</el-button>
        <el-button type="primary" @click="$router.push('/batches/create')">创建批次</el-button>
        <el-button :loading="loading" @click="loadTasks">刷新</el-button>
      </div>
    </header>

    <AdminStatsPanel />

    <el-card shadow="never">
      <template #header>
        <span>待裁决任务（{{ tasks.length }}）</span>
      </template>
      <el-table v-loading="loading" :data="tasks" row-key="unit_id">
        <el-table-column prop="unit_id" label="任务" width="80" />
        <el-table-column prop="video_name" label="视频" min-width="190" />
        <el-table-column prop="annotator_name" label="标注员" min-width="170" />
        <el-table-column prop="reviewer_name" label="审核员" min-width="170" />
        <el-table-column prop="reject_count" label="驳回次数" width="100" />
        <el-table-column label="标注区间" min-width="230">
          <template #default="{ row }">
            <span v-for="item in row.current_intervals" :key="`${item.start}-${item.end}`">
              [{{ item.start }}, {{ item.end }}] {{ item.label || '未命名' }}；
            </span>
          </template>
        </el-table-column>
        <el-table-column label="驳回历史" min-width="280">
          <template #default="{ row }">
            <el-popover placement="left" :width="380" trigger="click">
              <template #reference>
                <el-button link type="primary">查看 {{ row.reject_history.length }} 条</el-button>
              </template>
              <div v-for="history in row.reject_history" :key="history.rejected_at" class="admin__history">
                <strong>{{ history.reviewer_name }}</strong>
                <span>{{ history.reason }}</span>
              </div>
            </el-popover>
          </template>
        </el-table-column>
        <el-table-column label="裁决" width="280" fixed="right">
          <template #default="{ row }">
            <el-button type="success" link @click="forceApprove(row)">强制通过</el-button>
            <el-button type="warning" link @click="reassign(row)">重新分配</el-button>
            <el-button type="info" link @click="markDifficult(row)">困难样本</el-button>
          </template>
        </el-table-column>
        <template #empty>
          <el-empty description="暂无待裁决任务" />
        </template>
      </el-table>
    </el-card>
  </section>
</template>

<style scoped>
.admin {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.admin__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.admin__actions { display: flex; align-items: center; gap: 8px; }

.admin__title {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0;
}

.admin__hint {
  color: var(--el-text-color-secondary);
}

.admin__history {
  display: flex;
  flex-direction: column;
  gap: 3px;
  padding: 8px 0;
  border-bottom: 1px solid var(--el-border-color-lighter);
}
</style>
