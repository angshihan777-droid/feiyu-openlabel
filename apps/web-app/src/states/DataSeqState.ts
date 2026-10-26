import { reactive, watch } from 'vue'
import { metaApi } from '@/api'
import { jobConfig } from './job-config'
import { globalStates } from '@/states'
import _ from 'lodash'

export const dataSeqState = reactive({
    seqMeta: null,
    streamMeta: null,
    tsToFrame: new Map<number, number>(),
    loaded: false
})

watch(() => jobConfig.seq, (newVal, oldVal) => {
    if (newVal === oldVal) {
        return
    }
    if (jobConfig.media_url || newVal.startsWith('unit:')) {
        return
    }
    metaApi.getCurrentSeqMeta().then((res) => {
        dataSeqState.seqMeta = res.data
    })
})

watch(() => jobConfig.inited, async (newVal, oldVal) => {
    if (newVal === oldVal) {
        return
    }
    if (jobConfig.media_url) {
        dataSeqState.seqMeta = null
        dataSeqState.streamMeta = null
        dataSeqState.tsToFrame.clear()
        globalStates.current_data.image_uri = jobConfig.media_url
        dataSeqState.loaded = true
        return
    }

    // metaApi.getCurrentStreamMeta().then((res) => {
    //     dataSeqState.streamMeta = res.data
    //     // TO 0
    //     // jobConfig.frame = 0
    //     dataSeqState.tsToFrame.clear()
    //     _.forEach(res.data.openlabel.frames, (value, key) => {
    //         dataSeqState.tsToFrame.set(value.frame_properties.timestamp, parseInt(key))
    //     })
    // })

    const res = await metaApi.getCurrentStreamMeta()
    dataSeqState.streamMeta = res.data
    dataSeqState.tsToFrame.clear()
    if (res.data.openlabel) {
        _.forEach(res.data.openlabel.frames, (value, key) => {
            dataSeqState.tsToFrame.set(parseInt(key), value.frame_properties.timestamp)
        })
    }

    dataSeqState.loaded = true
})

watch(
    () => dataSeqState.streamMeta,
    (newVal) => {
        const uri = _.get(
            newVal,
            `openlabel.frames.${jobConfig.frame}.frame_properties.uri`,
            ''
        )
        if ('' !== uri) {
            globalStates.current_data.image_uri = uri
        }
    }
)
