<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Icon } from '@iconify/vue'
import VideoAnnotationPanel from '@/components/challenge/VideoAnnotationPanel.vue'

const route = useRoute()
const router = useRouter()
const unitId = computed(() => Number(route.params.unitId))

function backToTasks() {
  router.push({ name: 'my-tasks' })
}
</script>

<template>
  <section class="annotate-page">
    <header class="annotate-page__header">
      <el-button link size="large" @click="backToTasks">
        <Icon icon="lucide:arrow-left" /> 返回任务列表
      </el-button>
      <div>
        <p>ANNOTATION STUDIO</p>
        <h1>视频标注</h1>
      </div>
      <span class="annotate-page__status">任务 {{ unitId }}</span>
    </header>
    <VideoAnnotationPanel
      :unit-id="unitId"
      mode="annotate"
      @completed="backToTasks"
    />
  </section>
</template>

<style scoped>
.annotate-page {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.annotate-page__header {
  display: grid;
  grid-template-columns: minmax(180px, 0.5fr) 1fr auto;
  align-items: center;
  gap: 18px;
}

.annotate-page__header p {
  margin: 0 0 4px;
  color: var(--el-color-primary);
  font: 600 var(--y-font-size-sm) var(--y-font-family-mono);
  letter-spacing: 0.1em;
}

.annotate-page__header h1 {
  margin: 0;
  font-size: var(--y-font-size-3xl);
}

.annotate-page__status {
  padding: 8px 12px;
  color: var(--el-text-color-secondary);
  background: var(--el-fill-color-light);
  border-radius: 999px;
}

@media (max-width: 760px) {
  .annotate-page__header {
    grid-template-columns: 1fr;
  }
}
</style>
