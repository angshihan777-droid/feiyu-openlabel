<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Icon } from '@iconify/vue'
import VideoAnnotationPanel from '@/components/challenge/VideoAnnotationPanel.vue'

const route = useRoute()
const router = useRouter()
const unitId = computed(() => Number(route.params.unitId))

function backToReviews() {
  router.push({ name: 'my-reviews' })
}
</script>

<template>
  <section class="review-page">
    <header class="review-page__header">
      <el-button link size="large" @click="backToReviews">
        <Icon icon="lucide:arrow-left" /> 返回审核列表
      </el-button>
      <div>
        <p>REVIEW STUDIO</p>
        <h1>视频审核</h1>
      </div>
      <span>任务 {{ unitId }} · 标注员匿名</span>
    </header>
    <VideoAnnotationPanel
      :unit-id="unitId"
      mode="review"
      @completed="backToReviews"
    />
  </section>
</template>

<style scoped>
.review-page {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.review-page__header {
  display: grid;
  grid-template-columns: minmax(180px, 0.5fr) 1fr auto;
  align-items: center;
  gap: 18px;
}

.review-page__header p {
  margin: 0 0 4px;
  color: var(--el-color-primary);
  font: 600 var(--y-font-size-sm) var(--y-font-family-mono);
  letter-spacing: 0.1em;
}

.review-page__header h1 {
  margin: 0;
  font-size: var(--y-font-size-3xl);
}

.review-page__header > span {
  color: var(--el-text-color-secondary);
}

@media (max-width: 760px) {
  .review-page__header {
    grid-template-columns: 1fr;
  }
}
</style>
