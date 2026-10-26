<template>
  <el-table
    :data="rows"
    :row-class-name="rowClassName"
    height="calc(100% - 8px)"
    @row-click="selectRow"
  >
    <el-table-column prop="index" label="#" width="42" />
    <el-table-column prop="type" label="类型" width="76" />
    <el-table-column prop="label" label="标签" min-width="90" show-overflow-tooltip />
    <el-table-column prop="range" label="时间段（秒）" min-width="120" />
    <el-table-column label="" width="52" align="center">
      <template #default="{ row }">
        <el-button
          link
          type="danger"
          aria-label="删除时间段"
          @click.stop="removeRow(row)"
        >
          <Icon icon="material-symbols-light:delete-outline" />
        </el-button>
      </template>
    </el-table-column>
  </el-table>
</template>

<script lang="ts" setup>
import { ref, watch } from 'vue'
import { Icon } from '@iconify/vue'
import { globalStates } from '@/states'
import { toolStates } from '../../tools/video-annotator'

interface IntervalRow {
  id: string
  index: number
  type: string
  label: string
  range: string
}

const rows = ref<IntervalRow[]>([])

function refreshRows() {
  const annotator = globalStates.mainAnnoater
  if (typeof annotator?.export !== 'function') {
    rows.value = []
    return
  }
  rows.value = (annotator.export('all') as Array<Record<string, any>>).map(
    (object, index) => {
      const range = object.frame_intervals?.[0] ?? {}
      const start = Number(range.time_start ?? range.start ?? 0)
      const end = Number(range.time_end ?? range.end ?? 0)
      const attributes = object.attributes ?? {}
      return {
        id: String(object.label_uuid ?? object.id ?? index),
        index: index + 1,
        type: object.ol_type_ ?? 'Action',
        label:
          attributes.label ??
          attributes.name ??
          attributes.annotation ??
          '未命名',
        range: `${start.toFixed(2)} - ${end.toFixed(2)}`,
      }
    },
  )
}

function selectRow(row: IntervalRow) {
  globalStates.mainAnnoater.selectObject?.(row.id)
}

function removeRow(row: IntervalRow) {
  globalStates.mainAnnoater.removeObject?.(row.id)
}

function rowClassName({ row }: { row: IntervalRow }) {
  const selectedId = toolStates.selected?.userData?.anno?.label_uuid
  return row.id === selectedId ? 'video-interval-row--selected' : ''
}

watch(
  () => toolStates.observer.objectsUpdated,
  refreshRows,
  { immediate: true },
)
</script>

<style scoped>
:deep(.video-interval-row--selected) {
  background: var(--el-color-primary-light-9);
}
</style>
