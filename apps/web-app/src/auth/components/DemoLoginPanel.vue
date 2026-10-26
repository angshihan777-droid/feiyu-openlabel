<script setup lang="ts">
import { Icon } from '@iconify/vue'
import { DEMO_IDENTITIES, type DemoIdentity } from '../demo-identities'

const identities = DEMO_IDENTITIES.map((identity) => {
  const [emailLocal, emailDomain] = identity.email.split('@')
  return { ...identity, emailLocal, emailDomain }
})

defineProps<{
  loadingIdentity?: DemoIdentity | null
}>()

defineEmits<{
  select: [identity: DemoIdentity]
}>()
</script>

<template>
  <section class="demo-login" aria-label="快速体验身份">
    <div class="demo-login__header">
      <span class="demo-login__eyebrow">QUICK DEMO</span>
      <span>一键进入四个工作台</span>
    </div>
    <div class="demo-login__grid">
      <el-button
        v-for="identity in identities"
        :key="identity.id"
        class="demo-login__button"
        :data-testid="`demo-login-${identity.id}`"
        :loading="loadingIdentity === identity.id"
        :disabled="loadingIdentity != null"
        @click="$emit('select', identity.id)"
      >
        <span class="demo-login__icon">
          <Icon :icon="identity.icon" :width="20" />
        </span>
        <span class="demo-login__copy">
          <strong>{{ identity.label }}</strong>
          <small>{{ identity.description }}</small>
          <small class="demo-login__email" :title="identity.email">
            <span>{{ identity.emailLocal }}</span>
            <span>@{{ identity.emailDomain }}</span>
          </small>
        </span>
      </el-button>
    </div>
    <p class="demo-login__notice">
      Avery 演示账号已由本地启动脚本创建，可重复用于完整流程。
    </p>
  </section>
</template>

<style scoped>
.demo-login {
  margin: 0;
}

.demo-login__header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
  color: var(--lab-ink);
  font-size: 12px;
  font-weight: 600;
}

.demo-login__eyebrow {
  color: #1677ff;
  font-family: var(--y-font-family-mono);
  font-size: 10px;
  letter-spacing: 0.1em;
}

.demo-login__grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}

.demo-login__button {
  height: auto;
  min-height: 78px;
  margin: 0;
  padding: 11px;
  white-space: normal;
  border-color: #dceaf6;
  border-radius: 12px;
  background: #f8fcff;
}

.demo-login__button :deep(> span) {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  width: 100%;
}

.demo-login__icon {
  display: grid;
  flex: 0 0 32px;
  width: 32px;
  height: 32px;
  place-items: center;
  border-radius: 10px;
  color: #1677ff;
  background: #e3f2ff;
}

.demo-login__copy {
  display: flex;
  min-width: 0;
  flex: 1;
  flex-direction: column;
  align-items: flex-start;
  gap: 3px;
  line-height: 1.35;
}

.demo-login__copy strong {
  color: var(--lab-ink);
  font-size: 12px;
}

.demo-login__copy small {
  color: var(--lab-ash);
  font-size: 9.5px;
  overflow-wrap: anywhere;
  text-align: left;
}

.demo-login__copy .demo-login__email {
  display: flex;
  width: 100%;
  font-size: 8.5px;
  line-height: 1.25;
  flex-direction: column;
}

.demo-login__notice {
  margin: 9px 0 0;
  color: var(--lab-ash);
  font-size: 10px;
  line-height: 1.5;
}

@media (max-width: 480px) {
  .demo-login__grid {
    grid-template-columns: 1fr;
  }

  .demo-login__button {
    min-height: 68px;
  }
}
</style>
