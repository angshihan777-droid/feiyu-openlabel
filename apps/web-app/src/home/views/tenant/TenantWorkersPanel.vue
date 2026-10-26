<script setup lang="ts">
import { computed, onMounted, ref, shallowRef } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Icon } from '@iconify/vue'
import { tenantAdminApi } from '@/api'

interface Member {
  id: number
  name: string
  email: string | null
  is_active: boolean
  roles: string[]
}

interface Credentials {
  email: string
  password: string
  role: 'annotator' | 'reviewer'
}

const loading = shallowRef(false)
const creatingRole = shallowRef<'annotator' | 'reviewer' | null>(null)
const members = ref<Member[]>([])
const credentials = shallowRef<Credentials | null>(null)
const credentialDialog = shallowRef(false)

const annotators = computed(() => members.value.filter((item) => item.roles.includes('annotator')))
const reviewers = computed(() => members.value.filter((item) => item.roles.includes('reviewer')))

async function loadMembers() {
  loading.value = true
  try {
    const response = await tenantAdminApi.members()
    members.value = response.items ?? []
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '人员加载失败')
  } finally {
    loading.value = false
  }
}

async function createMember(role: 'annotator' | 'reviewer') {
  creatingRole.value = role
  try {
    const response = await tenantAdminApi.createMember(role)
    credentials.value = {
      email: response.email,
      password: response.password,
      role,
    }
    credentialDialog.value = true
    await loadMembers()
  } finally {
    creatingRole.value = null
  }
}

async function copyCredentials() {
  if (!credentials.value) return
  const text = `邮箱：${credentials.value.email}\n密码：${credentials.value.password}`
  await navigator.clipboard.writeText(text)
  ElMessage.success('账号和密码已复制')
}

async function removeMember(member: Member) {
  const confirmed = await ElMessageBox.confirm(
    `删除 ${member.email || member.name}？删除后该账号不能继续登录。`,
    '删除作业人员',
    {
      type: 'warning',
      confirmButtonText: '确认删除',
      cancelButtonText: '取消',
    },
  ).catch(() => false)
  if (!confirmed) return
  await tenantAdminApi.removeMember(member.id)
  ElMessage.success('账号已删除')
  await loadMembers()
}

function roleLabel(role: string) {
  return role === 'annotator' ? '标注员' : '审核员'
}

onMounted(loadMembers)
</script>

<template>
  <section v-loading="loading" class="workers">
    <div class="workers__create-grid">
      <el-card shadow="never" class="workers__create-card">
        <div class="workers__create-icon annotator">
          <Icon icon="lucide:pen-line" />
        </div>
        <div>
          <p class="workers__eyebrow">ANNOTATOR</p>
          <h3>创建标注员</h3>
          <p>系统自动生成随机邮箱和密码，账号会持久保存并可直接登录。</p>
        </div>
        <el-button
          type="primary"
          size="large"
          :loading="creatingRole === 'annotator'"
          @click="createMember('annotator')"
        >
          生成标注员账号
        </el-button>
      </el-card>

      <el-card shadow="never" class="workers__create-card">
        <div class="workers__create-icon reviewer">
          <Icon icon="lucide:scan-eye" />
        </div>
        <div>
          <p class="workers__eyebrow">REVIEWER</p>
          <h3>创建审核员</h3>
          <p>审核员与标注员角色严格分开，创建后独立进入视频审核工作台。</p>
        </div>
        <el-button
          type="primary"
          size="large"
          :loading="creatingRole === 'reviewer'"
          @click="createMember('reviewer')"
        >
          生成审核员账号
        </el-button>
      </el-card>
    </div>

    <div class="workers__tables">
      <el-card shadow="never">
        <template #header>
          <div class="workers__table-head">
            <span>标注员（{{ annotators.length }}）</span>
            <el-tag type="primary">独立角色</el-tag>
          </div>
        </template>
        <el-table :data="annotators" row-key="id" table-layout="fixed">
          <el-table-column prop="id" label="ID" width="78" />
          <el-table-column prop="email" label="登录邮箱" min-width="210" show-overflow-tooltip />
          <el-table-column label="状态" width="110">
            <template #default="{ row }">
              <el-tag :type="row.is_active ? 'success' : 'info'">{{ row.is_active ? '正常' : '停用' }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="96" fixed="right">
            <template #default="{ row }">
              <el-button type="danger" plain size="small" @click="removeMember(row)">删除</el-button>
            </template>
          </el-table-column>
          <template #empty><el-empty description="暂无标注员" /></template>
        </el-table>
      </el-card>

      <el-card shadow="never">
        <template #header>
          <div class="workers__table-head">
            <span>审核员（{{ reviewers.length }}）</span>
            <el-tag type="warning">独立角色</el-tag>
          </div>
        </template>
        <el-table :data="reviewers" row-key="id" table-layout="fixed">
          <el-table-column prop="id" label="ID" width="78" />
          <el-table-column prop="email" label="登录邮箱" min-width="210" show-overflow-tooltip />
          <el-table-column label="状态" width="110">
            <template #default="{ row }">
              <el-tag :type="row.is_active ? 'success' : 'info'">{{ row.is_active ? '正常' : '停用' }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="96" fixed="right">
            <template #default="{ row }">
              <el-button type="danger" plain size="small" @click="removeMember(row)">删除</el-button>
            </template>
          </el-table-column>
          <template #empty><el-empty description="暂无审核员" /></template>
        </el-table>
      </el-card>
    </div>

    <el-dialog v-model="credentialDialog" title="新账号已创建" width="520px">
      <el-alert
        type="success"
        :closable="false"
        title="请立即复制并妥善保存密码。密码只在这里显示一次。"
      />
      <div v-if="credentials" class="workers__credentials">
        <span>角色</span><strong>{{ roleLabel(credentials.role) }}</strong>
        <span>邮箱</span><strong>{{ credentials.email }}</strong>
        <span>密码</span><strong>{{ credentials.password }}</strong>
      </div>
      <template #footer>
        <el-button @click="credentialDialog = false">关闭</el-button>
        <el-button type="primary" @click="copyCredentials">复制账号密码</el-button>
      </template>
    </el-dialog>
  </section>
</template>

<style scoped>
.workers {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.workers__create-grid,
.workers__tables {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 18px;
}

.workers__create-card :deep(.el-card__body) {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 16px 18px;
  align-items: start;
}

.workers__create-card :deep(.el-button) {
  grid-column: 1 / -1;
  justify-self: start;
}

.workers__create-icon {
  display: grid;
  width: 52px;
  height: 52px;
  font-size: 25px;
  border-radius: 14px;
  place-items: center;
}

.workers__create-icon.annotator {
  color: var(--el-color-primary);
  background: var(--el-color-primary-light-9);
}

.workers__create-icon.reviewer {
  color: var(--el-color-warning-dark-2);
  background: var(--el-color-warning-light-9);
}

.workers__eyebrow {
  margin: 0 0 4px;
  color: var(--el-text-color-secondary);
  font: 600 var(--y-font-size-xs) var(--y-font-family-mono);
  letter-spacing: 0.1em;
}

.workers__create-card h3 {
  margin: 0 0 6px;
  font-size: var(--y-font-size-xl);
}

.workers__create-card p {
  margin: 0;
  color: var(--el-text-color-secondary);
  line-height: 1.65;
}

.workers__table-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.workers__credentials {
  display: grid;
  grid-template-columns: 70px minmax(0, 1fr);
  gap: 12px;
  padding: 20px 0;
}

.workers__credentials span {
  color: var(--el-text-color-secondary);
}

.workers__credentials strong {
  font-family: var(--y-font-family-mono);
  word-break: break-all;
}

@media (max-width: 980px) {
  .workers__create-grid,
  .workers__tables {
    grid-template-columns: 1fr;
  }
}
</style>
