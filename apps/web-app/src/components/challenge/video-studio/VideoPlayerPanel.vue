<script setup lang="ts">
import { computed, useTemplateRef } from 'vue'
import { Icon } from '@iconify/vue'
import type { VideoInterval } from '@/libs/intervals'

const props = defineProps<{
  videoUrl: string
  intervals: VideoInterval[]
  currentTime: number
  duration: number
}>()

const emit = defineEmits<{
  timeUpdate: [time: number]
  durationChange: [duration: number]
  previewChange: [preview: string]
  playingChange: [playing: boolean]
  timelineInput: [time: number]
  intervalClick: [time: number]
}>()

const videoElement = useTemplateRef<HTMLVideoElement>('videoElement')

const timelineMax = computed(() => Math.max(props.duration, 1))
const timelineIntervals = computed(() =>
  props.intervals.map((interval, index) => ({
    index,
    left: `${(interval.start / timelineMax.value) * 100}%`,
    width: `${Math.max(
      ((interval.end - interval.start) / timelineMax.value) * 100,
      0.35,
    )}%`,
  })),
)
const currentMarkerStyle = computed(() => ({
  left: `${(props.currentTime / timelineMax.value) * 100}%`,
}))

function roundTime(value: number) {
  return Math.round(Math.max(0, value) * 100) / 100
}

function seek(value: number) {
  const next = Math.min(Math.max(0, value), props.duration || value)
  if (videoElement.value) videoElement.value.currentTime = next
  emit('timeUpdate', roundTime(next))
  capturePreview()
}

function pause() {
  videoElement.value?.pause()
}

function togglePlayback() {
  const video = videoElement.value
  if (!video) return
  if (video.paused) {
    void video.play()
  } else {
    video.pause()
  }
}

function syncDuration() {
  const mediaDuration = videoElement.value?.duration ?? 0
  emit('durationChange', Number.isFinite(mediaDuration) ? mediaDuration : props.duration)
  capturePreview()
}

function emitCurrentTime() {
  const time = roundTime(videoElement.value?.currentTime ?? 0)
  emit('timeUpdate', time)
  capturePreview()
}

function emitPlayingState() {
  emit('playingChange', Boolean(videoElement.value && !videoElement.value.paused))
}

function capturePreview() {
  const video = videoElement.value
  if (!video || video.readyState < 2) return
  const canvas = document.createElement('canvas')
  canvas.width = video.videoWidth || 320
  canvas.height = video.videoHeight || 180
  const context = canvas.getContext('2d')
  if (!context) return
  try {
    context.drawImage(video, 0, 0, canvas.width, canvas.height)
    emit('previewChange', canvas.toDataURL('image/jpeg', 0.72))
  } catch {
    // The preview is optional; protected media can still play normally.
  }
}

function onTimelineInput(event: Event) {
  emit('timelineInput', roundTime(Number((event.target as HTMLInputElement).value)))
}

defineExpose({ pause, seek, togglePlayback })
</script>

<template>
  <section class="video-player">
    <video
      v-if="videoUrl"
      ref="videoElement"
      class="video-player__media"
      :src="videoUrl"
      controls
      preload="metadata"
      @loadedmetadata="syncDuration"
      @loadeddata="capturePreview"
      @timeupdate="emitCurrentTime"
      @seeked="emitCurrentTime"
      @play="emitPlayingState"
      @pause="emitPlayingState"
    />
    <el-empty v-else description="任务视频不可用" />

    <div class="video-player__timeline">
      <button
        v-for="item in timelineIntervals"
        :key="item.index"
        class="video-player__range"
        :style="{ left: item.left, width: item.width }"
        type="button"
        :title="`区间 ${item.index + 1}`"
        @click="emit('intervalClick', intervals[item.index]!.start)"
      />
      <span class="video-player__cursor" :style="currentMarkerStyle" />
      <input
        class="video-player__scrubber"
        type="range"
        min="0"
        :max="timelineMax"
        step="0.01"
        :value="currentTime"
        aria-label="视频时间轴"
        @input="onTimelineInput"
      >
    </div>
  </section>
</template>

<style scoped>
.video-player {
  min-width: 0;
}

.video-player__media {
  width: 100%;
  max-height: 560px;
  border-radius: 12px;
  background: #080b10;
}

.video-player__timeline {
  position: relative;
  height: 42px;
  margin: 14px 8px 0;
}

.video-player__timeline::before {
  position: absolute;
  top: 19px;
  right: 0;
  left: 0;
  height: 6px;
  border-radius: 999px;
  content: '';
  background: var(--el-fill-color-dark);
}

.video-player__range {
  position: absolute;
  top: 12px;
  z-index: 2;
  min-width: 3px;
  height: 20px;
  padding: 0;
  border: 0;
  border-radius: 5px;
  background: var(--el-color-primary-light-3);
  cursor: pointer;
}

.video-player__cursor {
  position: absolute;
  top: 5px;
  z-index: 3;
  width: 2px;
  height: 34px;
  pointer-events: none;
  background: var(--el-color-danger);
}

.video-player__scrubber {
  position: absolute;
  top: 0;
  z-index: 4;
  width: 100%;
  height: 42px;
  margin: 0;
  cursor: ew-resize;
  opacity: 0.01;
}
</style>
