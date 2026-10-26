import { reactive } from 'vue'
import { challengeApi } from '@/api'
import { ElMessageBox } from 'element-plus'
import { Mission } from '@/constants'

const initFromQuery = () => {
  const url = new URL(window.location.href)
  const unitId = parseInt(url.searchParams.get('unit_id') || '0')

  if (unitId > 0) {
    challengeApi
      .getUnit(unitId)
      .then((response: any) => {
        const unit = response?.data?.unit_id ? response.data : response
        if (!unit?.unit_id || !unit?.video) {
          throw new Error('任务详情响应缺少视频信息')
        }
        jobConfig.unit_id = unitId
        jobConfig.uuid = ''
        jobConfig.seq = `unit:${unitId}`
        jobConfig.stream = unit.video?.filename || `video-${unit.video?.id ?? 0}`
        jobConfig.frame = 0
        jobConfig.ts = 0
        jobConfig.mission = Mission.VideoEvents
        jobConfig.data_source = 'remote'
        jobConfig.media_url = unit.video?.path || ''
        jobConfig.taxonomy = {
          key: 'ol_video-event_0.1.0_zh-CN.json',
          type: 'system',
          name: '视频标注',
          domain: 'intelligent-driving',
        }
        jobConfig.status = unit.status || ''
        jobConfig.inited = true
      })
      .catch(() => {
        ElMessageBox.alert('任务不存在或你无权访问', 'error')
      })
    return true
  }

  ElMessageBox.alert('URL 缺少 unit_id，无法打开挑战任务', '任务不存在')
  return false
}

const jobConfig = reactive({
  data_format: 'simple-directory',
  data_source: '',
  seq: '',
  stream: '',
  /**
   * frame序号
   */
  frame: 0,
  coordinate_system: '',

  domain: '',
  mission: '',
  taxonomy: {} as {
    key?: string
    type?: string
    name?: string
    domain?: string
  },
  uuid: '',
  unit_id: 0,
  media_url: '',
  status: '',
  /** frame 时间戳 */
  ts: 0,
  inited: false
})


export { initFromQuery, jobConfig}
