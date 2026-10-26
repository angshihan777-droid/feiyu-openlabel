<script setup lang="ts">
import { onMounted, reactive, shallowRef } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Icon } from '@iconify/vue'
import { platformAdminApi } from '@/api'

interface PlatformTenant {
  id: number
  name: string
  slug: string
  status: string
  created_at: string | null
}

const loading = shallowRef(false)
const saving = shallowRef(false)
const tenants = shallowRef<PlatformTenant[]>([])
const form = reactive({
  name: '',
  slug: '',
  admin_email: '',
  admin_password: '',
})

async function loadTenants() {
  loading.value = true
  try {
    const response = await platformAdminApi.tenants()
    tenants.value = response.items ?? []
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '租户列表加载失败')
  } finally {
    loading.value = false
  }
}

async function createTenant() {
  if (!form.name.trim() || !/^[a-z0-9][a-z0-9-]{1,63}$/.test(form.slug)) {
    ElMessage.warning('请填写租户名称和有效标识')
    return
  }
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.admin_email) || form.admin_password.length < 10) {
    ElMessage.warning('请填写管理员邮箱及至少 10 位初始密码')
    return
  }
  saving.value = true
  try {
    const created = await platformAdminApi.createTenant({ ...form, name: form.name.trim() })
    ElMessage.success(`租户 ${created.name} 和初始管理员已创建`)
    Object.assign(form, { name: '', slug: '', admin_email: '', admin_password: '' })
    await loadTenants()
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '租户创建失败')
  } finally {
    saving.value = false
  }
}

async function deleteTenant(tenant: PlatformTenant) {
  const confirmed = await ElMessageBox.confirm(
    `删除租户“${tenant.name}”？该租户下人员将停止登录，历史数据保留用于审计。`,
    '删除租户',
    {
      type: 'warning',
      confirmButtonText: '确认删除',
      cancelButtonText: '取消',
    },
  ).catch(() => false)
  if (!confirmed) return
  await platformAdminApi.deleteTenant(tenant.slug)
  ElMessage.success('租户已删除')
  await loadTenants()
}

function formatDate(value: string | null) {
  return value ? new Date(value).toLocaleDateString('zh-CN') : '—'
}

onMounted(loadTenants)
</script>

<template>
  <section class="platform-admin">
    <header class="platform-admin__header">
      <div>
        <p class="platform-admin__eyebrow">PLATFORM CONTROL</p>
        <h2><Icon icon="lucide:landmark" /> 平台租户工作台</h2>
        <p>平台管理员添加或删除租户，并初始化首位租户管理员。</p>
      </div>
      <el-button :loading="loading" @click="loadTenants">刷新</el-button>
    </header>

    <div class="platform-admin__layout">
      <el-card shadow="never">
        <template #header><span>创建租户</span></template>
        <el-form label-position="top">
          <el-form-item label="租户名称">
            <el-input v-model="form.name" maxlength="128" placeholder="例如：机器人数据团队" />
          </el-form-item>
          <el-form-item label="租户标识">
            <el-input v-model="form.slug" maxlength="64" placeholder="lowercase-team-id" />
          </el-form-item>
          <el-divider content-position="left">初始租户管理员</el-divider>
          <el-form-item label="管理员邮箱">
            <el-input v-model="form.admin_email" type="email" autocomplete="off" />
          </el-form-item>
          <el-form-item label="初始密码">
            <el-input v-model="form.admin_password" type="password" show-password autocomplete="new-password" />
          </el-form-item>
          <el-button type="primary" :loading="saving" @click="createTenant">创建租户</el-button>
        </el-form>
      </el-card>

      <el-card shadow="never">
        <template #header><span>租户列表（{{ tenants.length }}）</span></template>
        <el-table v-loading="loading" :data="tenants" row-key="id" table-layout="fixed">
          <el-table-column prop="name" label="租户" min-width="150" show-overflow-tooltip />
          <el-table-column prop="slug" label="标识" min-width="130" show-overflow-tooltip />
          <el-table-column label="状态" width="96">
            <template #default="{ row }"><el-tag :type="row.status === 'active' ? 'success' : 'info'">{{ row.status }}</el-tag></template>
          </el-table-column>
          <el-table-column label="创建日期" width="112">
            <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
          </el-table-column>
          <el-table-column label="操作" width="96" fixed="right">
            <template #default="{ row }">
              <el-button type="danger" plain size="small" @click="deleteTenant(row)">删除</el-button>
            </template>
          </el-table-column>
          <template #empty><el-empty description="暂无租户" /></template>
        </el-table>
      </el-card>
    </div>
  </section>
</template>

<style scoped>
.platform-admin { display: flex; flex-direction: column; gap: 24px; }
.platform-admin__header { display: flex; align-items: center; justify-content: space-between; gap: 16px; }
.platform-admin__header h2 { display: flex; align-items: center; gap: 10px; margin: 0; font-size: var(--y-font-size-3xl); }
.platform-admin__header p { color: var(--el-text-color-secondary); }
.platform-admin__eyebrow { margin: 0 0 4px; color: var(--el-color-primary); font: 600 var(--y-font-size-sm) var(--y-font-family-mono); letter-spacing: .12em; }
.platform-admin__layout { display: grid; grid-template-columns: minmax(360px, 0.72fr) minmax(0, 1.28fr); gap: 20px; align-items: start; }
@media (max-width: 900px) { .platform-admin__layout { grid-template-columns: 1fr; } }
</style>
