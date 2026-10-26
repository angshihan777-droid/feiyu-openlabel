<template>
    <div class="app">
        <div class="test-player-wrap" v-if="toolStates.player.src">
            <Vue3VideoPlayer autoplay :src="toolStates.player.src" :title="toolStates.player.title" @ended="playEnded"
                :view-core="viewCore.bind(null, 'video1')">
                <!-- <template #cusControls>
                    <span class="btn-play" @click="play('video1')">play</span>
                </template> -->
            </Vue3VideoPlayer>
        </div>
    </div>
</template>

<script lang="ts" setup>
import '@cloudgeek/vue3-video-player/dist/vue3-video-player.css'
import { toolStates } from './tools/video-annotator'
import { onUnmounted } from 'vue';

interface VideoPlayerInstance {
    getVideoElement(): HTMLVideoElement
    destroy(): void
}

const viewCore = (_id: string, player: VideoPlayerInstance) => {
    player.getVideoElement().addEventListener('timeupdate', (event: Event) => {
        toolStates.player.timestamp = event.timeStamp
        toolStates.player.currentTime = player.getVideoElement().currentTime
    })
    player.getVideoElement().addEventListener('canplay', () => {
        toolStates.player.duration = player.getVideoElement().duration
    })
    toolStates.player.instance = player
}

const playEnded = () => {
    ;
}

onUnmounted(() => {
    if (toolStates.player.instance) {
        toolStates.player.instance.destroy()
    }
})

</script>

<style scoped>
.app {
    font-family: Avenir, Helvetica, Arial, sans-serif;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
    text-align: center;
    color: var(--y-color-text-primary);
    margin-top: 20px;
}

.test-player-wrap {
    /* width: 720px;
    height: 405px; */
    position: relative;
    margin: 10px auto;
}

.btn-play {
    color: var(--y-color-text-inverse);
    margin-right: 10px;
    cursor: pointer;
}

.btn-play svg {
    width: 16px;
}
</style>
