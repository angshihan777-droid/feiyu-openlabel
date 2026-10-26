<script setup lang="ts">
import { shallowRef } from 'vue'
import { Icon } from '@iconify/vue'
import TenantWorkersPanel from './TenantWorkersPanel.vue'
import TenantOverviewPanel from './TenantOverviewPanel.vue'
import TenantProjectsPanel from './TenantProjectsPanel.vue'
import TenantReviewPanel from './TenantReviewPanel.vue'

const activeTab = shallowRef('workers')
</script>

<template>
  <section class="tenant-admin">
    <header class="tenant-admin__header">
      <div>
        <p class="tenant-admin__eyebrow">TENANT OPERATIONS</p>
        <h1 class="tenant-admin__title">
          <Icon icon="lucide:building-2" />
          租户管理工作台
        </h1>
        <p class="tenant-admin__hint">人员、质量和项目视频规则各自独立，避免把管理动作挤在同一个表单里。</p>
      </div>
      <el-tag size="large" effect="plain">当前租户</el-tag>
    </header>

    <el-tabs v-model="activeTab" class="tenant-admin__tabs" stretch>
      <el-tab-pane name="workers">
        <template #label>
          <span class="tenant-admin__tab-label"><Icon icon="lucide:users" /> 租户人员</span>
        </template>
        <TenantWorkersPanel />
      </el-tab-pane>
      <el-tab-pane name="overview">
        <template #label>
          <span class="tenant-admin__tab-label"><Icon icon="lucide:chart-no-axes-combined" /> 概览</span>
        </template>
        <TenantOverviewPanel />
      </el-tab-pane>
      <el-tab-pane name="review">
        <template #label>
          <span class="tenant-admin__tab-label"><Icon icon="lucide:scan-eye" /> 视频审核</span>
        </template>
        <TenantReviewPanel />
      </el-tab-pane>
      <el-tab-pane name="settings">
        <template #label>
          <span class="tenant-admin__tab-label"><Icon icon="lucide:sliders-horizontal" /> 设置</span>
        </template>
        <TenantProjectsPanel />
      </el-tab-pane>
    </el-tabs>
  </section>
</template>

<style scoped>
.tenant-admin {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.tenant-admin__header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 24px;
}

.tenant-admin__eyebrow {
  margin: 0 0 6px;
  color: var(--el-color-primary);
  font: 600 var(--y-font-size-sm) var(--y-font-family-mono);
  letter-spacing: 0.12em;
}

.tenant-admin__title {
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 0;
  font-size: var(--y-font-size-3xl);
}

.tenant-admin__hint {
  margin-bottom: 0;
  color: var(--el-text-color-secondary);
}

.tenant-admin__tabs :deep(.el-tabs__header) {
  margin-bottom: 20px;
}

.tenant-admin__tab-label {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: var(--y-font-size-md);
}

@media (max-width: 760px) {
  .tenant-admin__header {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
