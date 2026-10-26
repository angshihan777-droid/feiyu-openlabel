<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { challengeApi } from '@/api'

const batchId = ref<number>()
const dateRange = ref<[string, string]>()
const loading = ref(false)
const items = ref<Array<Record<string, any>>>([])
const total = ref(0)

const dates = computed(() =>
  dateRange.value ?? [
    new Date().toISOString().slice(0, 10),
    new Date().toISOString().slice(0, 10),
  ],
)

async function loadStats() {
  if (!batchId.value) {
    ElMessage.warning('请输入批次 ID')
    return
  }
  loading.value = true
  try {
    const response = await challengeApi.dailyDuration({
      batch_id: batchId.value,
      start_date: dates.value[0]!,
      end_date: dates.value[1]!,
    })
    items.value = response.items ?? []
    total.value = response.total_duration ?? 0
  } finally {
    loading.value = false
  }
}

async function download() {
  if (!batchId.value) return
  const blob = await challengeApi.exportStats({
    batch_id: batchId.value,
    start_date: dates.value[0]!,
    end_date: dates.value[1]!,
  })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `batch_${batchId.value}_stats.csv`
  link.click()
  URL.revokeObjectURL(url)
}

onMounted(() => {
  const today = new Date().toISOString().slice(0, 10)
  dateRange.value = [
    today,
    today,
  ]
})
</script>

<template>
  <el-card shadow="never">
    <template #header>
      <div class="stats__header">
        <span>按日有效时长</span>
        <el-tag>合计 {{ total.toFixed(2) }} 秒</el-tag>
      </div>
    </template>
    <div class="stats__filters">
      <el-input-number v-model="batchId" :min="1" placeholder="批次 ID" />
      <el-date-picker
        v-model="dateRange"
        type="daterange"
        value-format="YYYY-MM-DD"
        start-placeholder="开始日期"
        end-placeholder="结束日期"
      />
      <el-button type="primary" :loading="loading" @click="loadStats">查询</el-button>
      <el-button :disabled="!batchId" @click="download">导出 CSV</el-button>
    </div>
    <p class="stats__note">统计日期按 UTC 归集；如租户需要本地自然日，请先确认时区策略。</p>
    <el-table v-loading="loading" :data="items">
      <el-table-column prop="date" label="提交日期" width="140" />
      <el-table-column prop="username" label="标注员" min-width="200" />
      <el-table-column label="有效时长（秒）" width="150">
        <template #default="{ row }">{{ Number(row.duration).toFixed(2) }}</template>
      </el-table-column>
    </el-table>
  </el-card>
</template>

<style scoped>
.stats__header,
.stats__filters {
  display: flex;
  align-items: center;
  gap: 12px;
}

.stats__header {
  justify-content: space-between;
}

.stats__filters {
  margin-bottom: 14px;
  flex-wrap: wrap;
}

.stats__note {
  margin: -4px 0 12px;
  color: var(--el-text-color-secondary);
  font-size: 12px;
}
</style>
