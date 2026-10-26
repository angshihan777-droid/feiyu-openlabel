<template>
  <div id="attrPanelContainer" class="attr-panel">
    <div class="attr-panel__header">时间段属性</div>
    <el-scrollbar class="attr-panel__scroll">
      <VideoEventAttributes />
    </el-scrollbar>
  </div>
</template>

<script lang="ts" setup>
import { ElScrollbar } from 'element-plus'
import VideoEventAttributes from './annos/video-event-attributes.vue'
</script>

<style scoped>
.attr-panel {
  height: 100%;
}

.attr-panel__header {
  padding: 10px 12px;
  font-weight: 600;
  border-bottom: 1px solid var(--el-border-color-lighter);
}

.attr-panel__scroll {
  height: calc(100% - 44px);
}
</style>
