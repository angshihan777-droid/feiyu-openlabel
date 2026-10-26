<template>
  <div id="dataPanelContainer" ref="el">
    <el-row id="panelBar">
      <el-col :span="20">
        <el-button-group class="panel-tabs">
          <el-button
            size="default"
            :type="dataPanel.tabs.active === 'task' ? 'primary' : ''"
            @click="dataPanel.tabs.active = 'task'"
          >
            任务
          </el-button>
          <el-button
            size="default"
            :type="dataPanel.tabs.active === 'objets' ? 'primary' : ''"
            @click="dataPanel.tabs.active = 'objets'"
          >
            时间段
          </el-button>
        </el-button-group>
      </el-col>
      <el-col :span="4" class="data-panel__settings">
        <el-popover placement="bottom-start" :width="520" trigger="click">
          <template #reference>
            <Icon icon="material-symbols-light:tv-options-input-settings-outline" />
          </template>
          <div>
            <el-button size="small" @click="dataPanel.panelWidth = 0">隐藏面板</el-button>
            <el-slider
              v-model="panelWidth"
              :min="240"
              :max="700"
              :step="50"
              show-input
              @change="dataPanel.panelWidth = panelWidth"
            />
          </div>
        </el-popover>
      </el-col>
    </el-row>
    <el-row id="panelContent" class="data-panel__content">
      <div v-show="dataPanel.tabs.active === 'task'" class="data-panel__pane">
        <TaskInfo />
      </div>
      <div v-show="dataPanel.tabs.active === 'objets'" class="data-panel__pane">
        <ObjectsInfo />
      </div>
    </el-row>
  </div>
</template>

<script lang="ts" setup>
import { ref } from 'vue'
import { Icon } from '@iconify/vue'
import { dataPanel } from '@/states/UiState'
import TaskInfo from './annos/TaskInfo.vue'
import ObjectsInfo from './annos/ObjectsInfo.vue'

const panelWidth = ref(dataPanel.value.panelWidth)
</script>

<style scoped>
.data-panel__settings {
  text-align: right;
  font-size: 18pt;
}

.data-panel__content {
  margin-top: 1px;
}

.data-panel__pane {
  width: 100%;
}
</style>
