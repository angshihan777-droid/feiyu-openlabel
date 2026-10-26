<template>
  <div id="mainPanelContainer" class="video-main-panel">
    <div id="imageAnnoContainer" class="video-main-panel__stage">
      <VideoPlayer />
    </div>
  </div>
</template>

<script lang="ts" setup>
import { onMounted, watch } from 'vue'
import { userAuth } from '@/states/UserState'
import { dataSeqState } from '@/states/DataSeqState'
import { globalStates } from '@/states'
import { VideoAnnotator, toolStates } from './tools/video-annotator'
import VideoPlayer from './video-player.vue'

function loadVideo(source: string) {
  if (!source) return
  const separator = source.includes('?') ? '&' : '?'
  toolStates.player.src = `${source}${separator}token=${encodeURIComponent(userAuth.value.access_token)}`
  toolStates.player.title = source
}

watch(
  [() => dataSeqState.loaded, () => globalStates.current_data.image_uri],
  ([loaded, source]) => {
    if (loaded && source) loadVideo(source)
  },
  { immediate: true },
)

onMounted(() => {
  globalStates.mainTool = VideoAnnotator.name
  globalStates.mainAnnoater = VideoAnnotator.getInstance()
})
</script>

<style scoped>
.video-main-panel {
  height: 100%;
}

.video-main-panel__stage {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--y-color-canvas-surface);
}
</style>
