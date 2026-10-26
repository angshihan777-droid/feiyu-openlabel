<script setup lang="ts">
import { Icon } from '@iconify/vue'
import type { VideoInterval } from '@/libs/intervals'
import type { AnnotationConfig, PanelMode } from './types'

defineProps<{
  mode: PanelMode
  config: AnnotationConfig
  duration: number
  currentTotal: number
  submissionError: string | null
}>()

const intervals = defineModel<VideoInterval[]>('intervals', { required: true })
const draftStart = defineModel<number>('start', { required: true })
const draftEnd = defineModel<number>('end', { required: true })
const draftLabel = defineModel<string>('label', { required: true })
const fps = defineModel<number>('fps', { required: true })

const emit = defineEmits<{
  setStart: []
  setEnd: []
  add: []
  remove: [index: number]
}>()
</script>

<template>
  <section v-if="mode === 'annotate'" class="interval-editor">
    <h3>创建片段</h3>
    <div class="interval-editor__form">
      <el-input-number
        v-model="draftStart"
        :min="0"
        :max="duration || undefined"
        :precision="2"
        :step="1 / fps"
        controls-position="right"
      />
      <span>至</span>
      <el-input-number
        v-model="draftEnd"
        :min="0"
        :max="duration || undefined"
        :precision="2"
        :step="1 / fps"
        controls-position="right"
      />
    </div>
    <el-select
      v-if="config.label_mode === 'preset'"
      v-model="draftLabel"
      placeholder="选择项目标签"
      class="interval-editor__select"
    >
      <el-option v-for="label in config.labels" :key="label" :label="label" :value="label" />
    </el-select>
    <el-input v-else v-model="draftLabel" placeholder="输入标签" />
    <div class="interval-editor__inline-actions">
      <el-button @click="emit('setStart')">当前帧设为开始</el-button>
      <el-button @click="emit('setEnd')">当前帧设为结束</el-button>
      <el-button type="primary" @click="emit('add')">加入片段</el-button>
    </div>
  </section>

  <section class="interval-list">
    <div class="interval-list__head">
      <h3>区间与标签</h3>
      <span>{{ currentTotal.toFixed(2) }} 秒</span>
    </div>
    <div v-if="intervals.length === 0" class="interval-list__empty">
      还没有片段。播放视频并用空格选择区间。
    </div>
    <article
      v-for="(interval, index) in intervals"
      :key="`${index}-${interval.start}`"
      class="interval-list__row"
    >
      <div class="interval-list__index">{{ index + 1 }}</div>
      <div class="interval-list__fields">
        <el-select
          v-if="mode === 'annotate' && config.label_mode === 'preset'"
          v-model="interval.label"
          placeholder="选择标签"
        >
          <el-option v-for="label in config.labels" :key="label" :label="label" :value="label" />
        </el-select>
        <el-input
          v-else-if="mode === 'annotate'"
          v-model="interval.label"
          placeholder="输入标签"
        />
        <strong v-else>{{ interval.label || '未命名' }}</strong>
        <div class="interval-list__times">
          <el-input-number
            v-if="mode === 'annotate'"
            v-model="interval.start"
            :min="0"
            :max="duration || undefined"
            :precision="2"
            :step="1 / fps"
            size="small"
            controls-position="right"
          />
          <span v-else>{{ interval.start.toFixed(2) }}s</span>
          <span>→</span>
          <el-input-number
            v-if="mode === 'annotate'"
            v-model="interval.end"
            :min="0"
            :max="duration || undefined"
            :precision="2"
            :step="1 / fps"
            size="small"
            controls-position="right"
          />
          <span v-else>{{ interval.end.toFixed(2) }}s</span>
        </div>
      </div>
      <el-button
        v-if="mode === 'annotate'"
        type="danger"
        plain
        size="small"
        class="interval-list__delete"
        @click="emit('remove', index)"
      >
        <Icon icon="lucide:trash-2" />
        删除
      </el-button>
    </article>
  </section>

  <el-alert
    v-if="mode === 'annotate' && submissionError && intervals.length"
    type="warning"
    :closable="false"
    :title="submissionError"
  />
</template>

<style scoped>
.interval-editor,
.interval-list {
  padding: 14px;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 10px;
}

.interval-list {
  max-height: 430px;
  overflow-y: auto;
}

.interval-editor h3,
.interval-list h3 {
  margin: 0;
  font-size: var(--y-font-size-lg);
}

.interval-editor__form {
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  gap: 8px;
  align-items: center;
  margin: 12px 0;
}

.interval-editor__select {
  width: 100%;
}

.interval-editor__inline-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 10px;
}

.interval-list__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.interval-list__row {
  display: grid;
  grid-template-columns: 32px minmax(0, 1fr) auto;
  gap: 10px;
  align-items: start;
  padding: 12px 0;
  border-bottom: 1px solid var(--el-border-color-lighter);
}

.interval-list__index {
  display: grid;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  color: var(--el-color-primary);
  background: var(--el-color-primary-light-9);
  place-items: center;
}

.interval-list__fields {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 8px;
}

.interval-list__times {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr);
  gap: 6px;
  align-items: center;
  color: var(--el-text-color-secondary);
}

.interval-list__empty {
  padding: 28px 8px;
  color: var(--el-text-color-secondary);
  text-align: center;
}

@media (max-width: 680px) {
  .interval-editor__form,
  .interval-list__times {
    grid-template-columns: 1fr;
  }

  .interval-editor__form > span,
  .interval-list__times > span {
    text-align: center;
  }

  .interval-list__row {
    grid-template-columns: 28px minmax(0, 1fr);
  }

  .interval-list__delete {
    grid-column: 2;
    justify-self: start;
  }
}
</style>
