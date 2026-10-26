<template>
  <Teleport to="#_Draggable_teleport">
  <Draggable v-slot="{ x, y }" class="fixed" :initial-value="{ x: canvaPanel.left_px, y: topBar.height_px + 5 }"
    :storage-key="'yh-vd-tool-pos-' + toolStates.toolConf.id" storage-type="session" v-show="toolStates.activated" :handle="dragHandle"
    :resizeable="false" :style="[topDivStyle]">
    <div ref="dragHandle" class="cursor-move" style="text-align: center;">新增</div>
    <el-card>
      <el-row  class="justify-center">
        <el-button-group>
          <el-button size="default" @click="toolStates.subTool = 'event'"
            :type="toolStates.subTool === 'event' ? 'success' : ''">事件(1)</el-button>
          <el-button size="default" @click="toolStates.subTool = 'action'"
            :type="toolStates.subTool === 'action' ? 'success' : ''">活动(2)</el-button>
          <el-button size="default" @click="toolStates.subTool = 'context'"
            :type="toolStates.subTool === 'context' ? 'success' : ''">场景(3)</el-button>
        </el-button-group>
      </el-row>
      <el-row class="justify-center">
        <el-tex>
          第{{ annotatorStates.player.currentTime }} / {{ annotatorStates.player.duration }} 秒
        </el-tex>
      </el-row>
      <el-row>
        <el-col span="8">开始时间
        </el-col>
        <el-col span="12">
          <el-input v-model="frameInterval.time_start"></el-input>
        </el-col>
        <el-col span="4"><el-button type="success" size="small" @click="frameInterval.time_start = annotatorStates.player.currentTime">获取</el-button>
        </el-col>
      </el-row>
      <el-row>
        <el-col span="8">结束时间
        </el-col>
        <el-col span="12">
          <el-input v-model="frameInterval.time_end"></el-input>
        </el-col>
        <el-col span="4"><el-button type="success" size="small" @click="frameInterval.time_end = annotatorStates.player.currentTime">获取</el-button>
        </el-col>
      </el-row>
      <el-row class="justify-center">
        <el-button-group>
          <el-button type="primary" @click="handleBuild">确定</el-button>
        </el-button-group>
      </el-row>
    </el-card>
  </Draggable>
</Teleport>
</template>

<script lang="ts" setup>
import { ref, onMounted, reactive } from 'vue'
import { globalStates } from '@/states'
import { toolSettingLayer, canvaPanel, topBar } from '@/states/UiState'
import { UseDraggable as Draggable } from '@/components/DraggableResizeableComponents'
import { toolStates, VideoEventTool } from './video-event-tool'
import { toolStates as annotatorStates } from './video-annotator'
import { ElMessage } from 'element-plus'
import { extractIntervals, validateIntervals } from '@/libs/intervals'

const frameInterval = reactive({
  time_start: 0,
  time_end: 0
})

const handleBuild = () => {
  const start = Number(frameInterval.time_start)
  const end = Number(frameInterval.time_end)
  if (!Number.isFinite(start) || !Number.isFinite(end)) {
    ElMessage.warning('请输入时间')
    return
  }
  if (start < 0 || end <= start) {
    ElMessage.warning('结束时间必须大于开始时间，且起点不能小于 0')
    return
  }
  if (annotatorStates.player.duration > 0 && end > annotatorStates.player.duration) {
    ElMessage.warning('结束时间不能超过视频时长')
    return
  }
  const existing = extractIntervals(globalStates.mainAnnoater.export('all'))
  const validation = validateIntervals(
    [...existing, { start, end }],
    annotatorStates.player.duration || undefined,
  )
  if (!validation.valid) {
    ElMessage.error(validation.error || '时间段无效')
    return
  }
  VideoEventTool.instance.doBuildObject({ time_start: start, time_end: end })

  frameInterval.time_end = 0
  frameInterval.time_start = 0
}

const dragHandle = ref<HTMLElement | null>(null)
const topDivStyle = ref({
  width: toolSettingLayer.width_px + 'px',
  zIndex: 1000,
  boxShadow: `var(--el-box-shadow-lighter)`
})

onMounted(() => {
})
</script>
