<template>
  <el-button-group>
    <VideoEventToolUi />
    <el-button
      type="primary"
      :class="{ 'is-tool-active': globalStates.mainTool === VideoEventTool.Name }"
      @click="toggleEventTool"
    >
      新增时间段
    </el-button>
  </el-button-group>
</template>

<script lang="ts" setup>
import { globalStates } from '@/states'
import { VideoEventTool, VideoEventToolUi } from '../tools/video-event-tool'

function toggleEventTool() {
  globalStates.mainTool =
    globalStates.mainTool === VideoEventTool.Name ? undefined : VideoEventTool.Name
}
</script>
