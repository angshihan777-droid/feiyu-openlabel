<script setup lang="ts">
import { Icon } from '@iconify/vue'

defineProps<{
  currentFrame: number
  totalFrames: number
  currentTime: number
  previewUrl: string
  selectionHint: string
  isPlaying: boolean
}>()

const fps = defineModel<number>('fps', { required: true })

defineEmits<{
  previousFrame: []
  togglePlayback: []
  nextFrame: []
}>()
</script>

<template>
  <div class="frame-controls">
    <div class="frame-controls__transport">
      <el-button circle aria-label="上一帧" @click="$emit('previousFrame')">
        <Icon icon="lucide:chevron-left" />
      </el-button>
      <el-button type="primary" circle aria-label="播放或暂停" @click="$emit('togglePlayback')">
        <Icon :icon="isPlaying ? 'lucide:pause' : 'lucide:play'" />
      </el-button>
      <el-button circle aria-label="下一帧" @click="$emit('nextFrame')">
        <Icon icon="lucide:chevron-right" />
      </el-button>
      <span class="frame-controls__count">
        帧 {{ currentFrame }} / {{ totalFrames }}
      </span>
      <el-input-number
        v-model="fps"
        :min="1"
        :max="120"
        :precision="0"
        size="small"
        controls-position="right"
        aria-label="帧率"
      />
      <span class="frame-controls__unit">FPS</span>
      <span class="frame-controls__hint">{{ selectionHint }}</span>
    </div>

    <div class="frame-controls__preview">
      <img
        v-if="previewUrl"
        :src="previewUrl"
        class="frame-controls__image"
        alt="当前帧预览"
      />
      <div v-else class="frame-controls__placeholder">
        <Icon icon="lucide:image" :width="24" />
      </div>
      <div class="frame-controls__copy">
        <span>当前帧预览</span>
        <strong>{{ currentTime.toFixed(2) }}s</strong>
        <small>空格第一次设开始，第二次设结束；← / → 逐帧</small>
      </div>
    </div>
  </div>
</template>

<style scoped>
.frame-controls {
  padding: 10px 0 0;
}

.frame-controls__transport {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px;
  padding: 6px 0 10px;
}

.frame-controls__count {
  font-family: var(--y-font-family-mono);
  font-size: var(--y-font-size-md);
}

.frame-controls__unit,
.frame-controls__hint {
  color: var(--el-text-color-secondary);
  font-size: var(--y-font-size-sm);
}

.frame-controls__hint {
  margin-left: auto;
}

.frame-controls__preview {
  display: grid;
  grid-template-columns: 180px minmax(0, 1fr);
  gap: 14px;
  align-items: center;
  padding: 12px;
  border-radius: 10px;
  background: var(--el-fill-color-lighter);
}

.frame-controls__image,
.frame-controls__placeholder {
  width: 180px;
  height: 130px;
  border-radius: 8px;
  background: #111;
  object-fit: contain;
}

.frame-controls__placeholder {
  display: grid;
  color: #7c91a5;
  place-items: center;
}

.frame-controls__copy {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 6px;
}

.frame-controls__copy span,
.frame-controls__copy small {
  color: var(--el-text-color-secondary);
}

.frame-controls__copy strong {
  font: 600 var(--y-font-size-2xl) var(--y-font-family-mono);
}

@media (max-width: 680px) {
  .frame-controls__preview {
    grid-template-columns: 1fr;
  }
}
</style>
