import { reactive } from 'vue'
import type { Action, Context, Event } from '@/openlabel'
import { AnnoTool } from '@/core/anno-tool'
import { globalStates } from '@/states'
import VideoEventToolUi from './video-event-tool-ui.vue'

export { VideoEventToolUi }

const Name = 'videoEventTool'

function newLabelId() {
  return globalThis.crypto?.randomUUID?.() ??
    `label-${Date.now()}-${Math.random().toString(16).slice(2)}`
}

export const toolStates = reactive({
  mode: undefined as string | undefined,
  activated: false,
  subTool: 'action' as string | undefined,
  toolConf: {
    id: Name,
    icon: 'fluent-mdl2:edit-create',
    name: '时间段',
    shortcut: 'E',
    description: '为视频添加动作、事件或场景时间段',
  },
})

class VideoEventTool extends AnnoTool {
  static Name = Name
  private static toolInstance: VideoEventTool

  static getInstance() {
    if (!VideoEventTool.toolInstance) VideoEventTool.toolInstance = new VideoEventTool()
    return VideoEventTool.toolInstance
  }

  static get instance() {
    return VideoEventTool.getInstance()
  }

  reset() {}

  activate() {
    toolStates.activated = true
  }

  deactivate() {
    toolStates.activated = false
  }

  doBuildObject(frameInterval: { time_start: number; time_end: number }) {
    const typeMap: Record<string, 'Action' | 'Event' | 'Context'> = {
      action: 'Action',
      event: 'Event',
      context: 'Context',
    }
    const olType = typeMap[toolStates.subTool || 'action'] || 'Action'
    const message = {
      ol_type_: olType,
      label_uuid: newLabelId(),
      frame_intervals: [{ ...frameInterval, frame_start: 0, frame_end: 0 }],
      attributes: { opType: 'create' },
    } as Action | Context | Event
    globalStates.mainAnnoater.onMessage(message)
  }
}

export { VideoEventTool }
