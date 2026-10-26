<script setup lang="ts">
import { computed, onMounted, ref, shallowRef } from 'vue'
import { ElMessage } from 'element-plus'
import { tenantAdminApi } from '@/api'
import VideoAnnotationPanel from '@/components/challenge/VideoAnnotationPanel.vue'

interface ReviewTask {
  unit_id: number
  video_name: string
  status: string
  reason: string | null
  assignee_name: string
  reviewer_name: string
  updated_at: string
  history: Array<{ rejected_at: string; reason: string }>
}

const loading = shallowRef(false)
const tasks = ref<ReviewTask[]>([])
const selectedId = ref<number | null>(null)

const selected = computed(() =>
  tasks.value.find((item) => item.unit_id === selectedId.value) ?? null,
)

async function loadTasks() {
  loading.value = true
  try {
    const response = await tenantAdminApi.reviews()
    tasks.value = response.tasks ?? []
    if (selectedId.value && !tasks.value.some((item) => item.unit_id === selectedId.value)) {
      selectedId.value = null
    }
    selectedId.value ??= tasks.value[0]?.unit_id ?? null
  } finally {
    loading.value = false
  }
}

function statusLabel(status: string) {
  return {
    returned: '标注员回退',
    rejected: '审核退回',
    escalated: '升级裁决',
    source_confirmed: '已确认视频问题',
    void: '已作废',
    difficult_sample: '困难样本',
  }[status] ?? status
}

function selectTask(row: ReviewTask | null) {
  selectedId.value = row?.unit_id ?? tasks.value[0]?.unit_id ?? null
}

onMounted(loadTasks)
</script>

<template>
  <section class="admin-review">
    <header class="admin-review__header">
      <div>
        <p>QUALITY DESK</p>
        <h3>问题视频复核</h3>
        <span>管理员可查看真实标注员和视频内容，并决定问题、退回、重分配或作废。</span>
      </div>
      <div class="admin-review__exports">
        <el-button :loading="loading" @click="loadTasks">刷新</el-button>
      </div>
    </header>

    <div class="admin-review__grid">
      <el-card shadow="never" class="admin-review__queue">
        <template #header><span>待复核任务（{{ tasks.length }}）</span></template>
        <el-table
          v-loading="loading"
          :data="tasks"
          row-key="unit_id"
          highlight-current-row
          @current-change="selectTask"
        >
          <el-table-column prop="unit_id" label="任务" width="64" />
          <el-table-column label="视频 / 原因" min-width="180">
            <template #default="{ row }">
              <div class="admin-review__item">
                <strong>{{ row.video_name }}</strong>
                <small>{{ row.reason || statusLabel(row.status) }}</small>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="状态" width="96">
            <template #default="{ row }">
              <el-tag type="warning">{{ statusLabel(row.status) }}</el-tag>
            </template>
          </el-table-column>
          <template #empty><el-empty description="暂无问题视频" /></template>
        </el-table>
      </el-card>

      <VideoAnnotationPanel
        :unit-id="selectedId"
        mode="admin"
        :reject-history="selected?.history ?? []"
        @completed="loadTasks"
      />
    </div>
  </section>
</template>

<style scoped>
.admin-review {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.admin-review__header,
.admin-review__exports {
  display: flex;
  align-items: center;
  gap: 12px;
}

.admin-review__header {
  justify-content: space-between;
}

.admin-review__header p {
  margin: 0 0 4px;
  color: var(--el-color-primary);
  font: 600 var(--y-font-size-xs) var(--y-font-family-mono);
  letter-spacing: 0.1em;
}

.admin-review__header h3 {
  margin: 0;
  font-size: var(--y-font-size-2xl);
}

.admin-review__header span,
.admin-review__item small {
  color: var(--el-text-color-secondary);
}

.admin-review__grid {
  display: grid;
  grid-template-columns: minmax(300px, 340px) minmax(0, 1fr);
  gap: 18px;
  align-items: start;
}

.admin-review__item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

@media (max-width: 980px) {
  .admin-review__grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 820px) {
  .admin-review__header {
    align-items: flex-start;
    flex-direction: column;
  }

  .admin-review__exports {
    flex-wrap: wrap;
  }
}
</style>
