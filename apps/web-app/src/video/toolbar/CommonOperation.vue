<template>
  <el-button-group>
    <el-tooltip placement="bottom-start" raw-content :content="'<span>Undo' +
      '</br>' +
      '</br>快捷键：Ctrl + Z' +
      '</span>'
      ">
      <el-button type="primary" @click="unDoConf.handle()" :disabled="unDoConf.disabled.value">
        <Icon :icon="unDoConf.icon" />
        </el-button>
    </el-tooltip>
    <el-tooltip placement="bottom-start" raw-content :content="'<span>Redo' +
        '</br>' +
        '</br>快捷键：Ctrl + Y' +
        '</span>'
        ">
      <el-button type="primary" @click="reDoConf.handle()" :disabled="reDoConf.disabled.value">
        <Icon :icon="reDoConf.icon" />
      </el-button>
    </el-tooltip>
    <el-tooltip placement="bottom-start" raw-content :content="'<span>' +
      item.name +
      '</br>' +
      item.description +
      '</br>快捷键：' +
      item.shortcut +
      '</span>'
      " v-for="(item, index) in commonButtons" :key="index">
      <el-button type="primary" @click="item.handle()" :loading="item.loading">
        <Icon :icon="item.icon" v-show="!item.loading" />
      </el-button>
    </el-tooltip>
    <el-popover placement="bottom" width="250" trigger="hover">
      <template #reference>
        <el-button type="primary">
          删
        </el-button>
      </template>
      <div>
        <el-button-group>
          <el-tooltip placement="bottom-start" raw-content :content="'<span>' +
      item.name +
      '</br>' +
      item.description +
      '</br>快捷键：' +
      item.shortcut +
      '</span>'
      " v-for="(item, index) in delButtons" :key="index">
      <el-button type="primary" @click="item.handle()" :loading="item.loading">
        <Icon :icon="item.icon" v-show="!item.loading" />
      </el-button>
    </el-tooltip>
        </el-button-group>
      </div>
    </el-popover>
  </el-button-group>
</template>

<script lang="ts" setup>
import { computed, onMounted, reactive, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Icon } from '@iconify/vue'
import { commonChannel } from '../channel'
import { jobConfig } from '@/states/job-config'
import { challengeApi, labelsApi } from '@/api'
import type { Action } from 'element-plus'
import { globalStates } from '@/states'
import { hotkeysManager } from '../hotkeysManager'
import { messages } from '@/states'
import { userSettings } from '@/states/UserState'
import { useUnit } from '../composables/useUnit'
import { extractIntervals, validateIntervals, withObjectIds } from '@/libs/intervals'

const { unit: currentUnit } = useUnit()

const unDoConf = {
  id: 'common-undo',
  icon: 'mynaui:undo',
  name: '取消上次',
  shortcut: 'Shift+Z',
  description: '<el-text>取消上次的编辑</el-text>',
  showButton: true,
  disabled: computed(() => {
    if (globalStates.mainAnnoater.undoRedo?.states.canUndo) {
      return false
    } else {
      return true
    }
  }),
  handle: () => {
    globalStates.mainAnnoater.undoLastOp?.()
    // commonChannel.pub(commonChannel.Events.ButtonClicked, { data: 'common-undo' })
  }
}

const reDoConf = {
  id: 'common-redo',
  icon: 'mynaui:redo',
  name: '重做上次',
  shortcut: 'Shift+D',
  description: '<el-text>重做上次的编辑</el-text>',
  showButton: true,
  disabled: computed(() => {
    if (globalStates.mainAnnoater.undoRedo?.states.canRedo) {
      return false
    } else {
      return true
    }
  }),
  handle: () => {
    globalStates.mainAnnoater.redoLastOp?.()
    // commonChannel.pub(commonChannel.Events.ButtonClicked, { data: 'common-undo' })
  }
}

const saveButtonConf = reactive({
  id: 'save-annotation',
  icon: 'lucide:upload',
  name: '保存标注',
  shortcut: 'Shift+S',
  description: '<el-text>保存当前帧所有件</el-text>',
  showButton: true,
  loading: false,
  handle: () => {
    commonChannel.pub(commonChannel.Events.ButtonClicked, { data: 'save-annotation' })
  }
})
const loadButtonConf = {
  id: 'load-annotation',
  icon: 'uis:refresh',
  name: '加载标注',
  shortcut: 'Shift+R',
  description: '<el-text>重新从后台加载已经保存的标签</el-text>',
  showButton: true,
  loading: false,
  handle: () => {
    commonChannel.pub(commonChannel.Events.ButtonClicked, { data: 'load-annotation' })
  }
}

const submitButtonConf = reactive({
  id: 'submit-review',
  icon: 'lucide:send',
  name: '提交审核',
  shortcut: 'Shift+Enter',
  description: '<el-text>校验区间并提交审核，提交后不可直接修改</el-text>',
  showButton: true,
  loading: false,
  handle: () => submitForReview(),
})

const commonButtons = [
  saveButtonConf,
  loadButtonConf,
  submitButtonConf,
]


const delButtons = [
  {
    id: 'delete',
    icon: 'ep:delete',
    name: '删除选中',
    shortcut: 'X',
    description: '<el-text>删除选中件</el-text>',
    showButton: true,
    loading: false,
    handle: () => {
      commonChannel.pub(commonChannel.Events.ButtonClicked, { data: 'delete' })
    }
  },
  {
    id: 'delete-all',
    icon: 'ep:delete-filled',
    name: '删除本帧',
    shortcut: 'Shift+X',
    description: '<el-text>清除本帧所有标注</el-text>',
    showButton: true,
    loading: false,
    handle: () => {
      commonChannel.pub(commonChannel.Events.ButtonClicked, { data: 'delete-all' })
    }
  }
  ,
  {
    id: 'delete-seq-all',
    icon: 'mdi:database-remove',
    name: '删除任务标签',
    shortcut: '',
    description: '<el-text>删除本任务所有标签</el-text>',
    showButton: true,
    loading: false,
    handle: () => {
      commonChannel.pub(commonChannel.Events.ButtonClicked, { data: 'delete-seq-all' })
    }
  }
]

const saveLabel = () => {
  saveButtonConf.loading = true
  const frame_labels = globalStates.mainAnnoater.export('createOrUpdated')

  // 要删除的数据
  globalStates.mainAnnoater.deletedObjs?.forEach((v: any, k: any) => {
    frame_labels.push({ ...v.userData.anno, 'attributes': {'opType': 'remove'}})
  })

  if (frame_labels.length === 0) {
    messages.lastInfo = ""
    saveButtonConf.loading = false
    return
  }

  // Stage 9.5: 若当前 jobConfig 对应一个 Stage 7 spawn 出来的 unit,
  // 走新 label v2 端点(乐观锁 + 版本 + 关联 workflow instance)
  if (currentUnit.value) {
    const unitId = currentUnit.value.id
    const expectedVersion = (currentUnit.value as any).data_version ?? 0
    labelsApi
      .save(unitId, {
        expected_version: expectedVersion,
        objects: withObjectIds(frame_labels),
        attrs: {
          current_tool: globalStates.mainTool,
          current_mission: jobConfig.mission,
        },
      })
      .then((rec: any) => {
        ElMessage.success(`帧${jobConfig.frame}:已保存 v${rec.version}`)
        // 同步本地 data_version,下次保存基于该版本
        if (currentUnit.value) {
          ;(currentUnit.value as any).data_version = rec.version
        }
        globalStates.mainAnnoater.deletedObjs?.clear()
        loadAnnos()
      })
      .catch(() => {
        // req.ts 已提示
      })
      .finally(() => {
        saveButtonConf.loading = false
      })
    return
  }

  ElMessage.warning('当前页面未绑定标注任务，无法保存')
  saveButtonConf.loading = false
}


const saveFramesLabel = (frameIds: number[]) => {
}

const loadAnnos = () => {
  loadButtonConf.loading = true
  const unit = currentUnit.value
  if (unit) {
    labelsApi
      .getLatest(unit.id)
      .then((rec: any) => {
        unit.data_version = rec.version ?? 0
        globalStates.mainAnnoater.import('default', rec.objects ?? [])
      })
      .catch(() => {
        globalStates.mainAnnoater.import('default', [])
      })
      .finally(() => {
        loadButtonConf.loading = false
        globalStates.anno.annoDataLoaded += 1
      })
    return
  }
  loadButtonConf.loading = false
  ElMessage.warning('当前页面未绑定标注任务，无法加载标注')
}

const submitForReview = async () => {
  if (!currentUnit.value) {
    ElMessage.warning('当前任务未绑定 Unit，无法提交审核')
    return
  }
  const objects = globalStates.mainAnnoater.export('all')
  const intervals = extractIntervals(objects)
  const validation = validateIntervals(intervals)
  if (!validation.valid) {
    ElMessage.error(validation.error || '标注区间无效')
    return
  }

  try {
    await ElMessageBox.confirm(
      `将提交 ${intervals.length} 个区间，总时长 ${intervals
        .reduce((sum, item) => sum + item.end - item.start, 0)
        .toFixed(2)} 秒。提交后进入匿名审核。`,
      '提交审核',
      { type: 'warning', confirmButtonText: '确认提交', cancelButtonText: '取消' },
    )
  } catch {
    return
  }
  submitButtonConf.loading = true
  try {
    const response = await challengeApi.submit(currentUnit.value.id, { intervals })
    ElMessage.success(`提交成功，有效时长 ${response.total_duration.toFixed(2)} 秒`)
    currentUnit.value.status = response.status
  } finally {
    submitButtonConf.loading = false
  }
}
/**
 * 保存标签
 */
commonChannel.sub(commonChannel.Events.ButtonClicked, (msg: any) => {
  switch (msg.data) {
    case 'common-undo':
      globalStates.mainAnnoater.undoLastOp()
      break
    case 'load-annotation':
      loadAnnos()
      break
    case 'save-annotation':
      saveLabel()
      break
    case 'delete':
      globalStates.mainAnnoater.removeSelected()
      break
    case 'delete-all':
      ElMessageBox.confirm('是否删除？本操作将清空本帧所有已标注的数据。', 'Confirm', {
        distinguishCancelAndClose: true,
        confirmButtonText: '是',
        cancelButtonText: '否'
      })
        .then(() => {
          globalStates.mainAnnoater.cleanData()
          messages.lastInfo = '清空'
        })
        .catch((action: Action) => {
          if (action === 'cancel') {
            // do nothing
          }
        })
      break
    case 'delete-seq-all':
      ElMessageBox.confirm('本操作将清除本任务所有标签数据，无法恢复。是否删除？', 'Confirm', {
        distinguishCancelAndClose: true,
        confirmButtonText: '是',
        cancelButtonText: '否'
      })
        .then(async () => {
          const unit = currentUnit.value
          if (!unit) {
            ElMessage.warning('当前页面未绑定标注任务')
            return
          }
          globalStates.mainAnnoater.cleanData()
          const rec: any = await labelsApi.save(unit.id, {
            expected_version: (unit as any).data_version ?? 0,
            objects: [],
            attrs: {
              current_tool: globalStates.mainTool,
              current_mission: jobConfig.mission,
            },
          })
          ;(unit as any).data_version = rec.version
          commonChannel.pub(commonChannel.Events.UpdateObjectCounts, {})
          ElMessage.success('删除成功')
        })
        .catch((action: Action) => {
          if (action === 'cancel') {
            // do nothing
          }
        })
      break
    default:
      break
  }
})

const init = () => {
  const btns = [...commonButtons, ...delButtons]
  const filterdButtns = btns.filter((btn) => btn.shortcut && btn.shortcut !== '')
  const keys = filterdButtns.map((btn) => btn.shortcut)
  const handles = filterdButtns.map((btn) => () => btn.handle())
  keys.forEach((key, index) => {
    hotkeysManager.registerHotkeys({ toolId: 'commonOp', keys: key, cb: handles[index] })
  })
}

let timerId = null as any
watch(() => userSettings.value.savePerSeconds.enabled, (newVal, oldVal) => {
  if (!newVal) {
    if (timerId) {
      clearInterval(timerId)
      timerId = null
    }
  } else {
    if (!timerId) {
      // 没有定时器，则创建
      timerId = setInterval(saveLabel, userSettings.value.savePerSeconds.prop * 1000)
    }
  }
}, {immediate: true})

onMounted(() => {
  init()
})
</script>
