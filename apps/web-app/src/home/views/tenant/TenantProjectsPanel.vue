<script setup lang="ts">
import { onMounted, reactive, ref, shallowRef } from 'vue'
import { ElMessage } from 'element-plus'
import { useRouter } from 'vue-router'
import { Icon } from '@iconify/vue'
import { projectsApi, tenantAdminApi } from '@/api'

interface Project {
  id: number
  name: string
  slug: string
  status: string
}

interface ReturnReason {
  code: string
  label: string
}

const router = useRouter()
const loading = shallowRef(false)
const saving = shallowRef(false)
const projects = ref<Project[]>([])
const selectedProjectId = ref<number | null>(null)
const newLabel = ref('')
const newReason = ref('')
const form = reactive({
  instructions: '',
  require_label: true,
  min_interval_seconds: 0.1,
  label_mode: 'free' as 'preset' | 'free',
  labels: [] as string[],
  label_template: '',
  fps: 30,
  return_reasons: [] as ReturnReason[],
})

const templates = {
  robotics: {
    label: '机械臂 / 机器人示教',
    labels: ['抓取', '放置', '移动', '装配', '检测', '等待', '异常'],
  },
  medical: {
    label: '医疗手术视频',
    labels: ['夹取', '剪切', '缝合', '打结', '冲洗', '吸引', '出血', '其他'],
  },
}

async function loadProjects() {
  loading.value = true
  try {
    const response = await projectsApi.list({ page_size: 200, status: 'active' })
    projects.value = response.items ?? []
    if (!selectedProjectId.value && projects.value[0]) {
      selectedProjectId.value = projects.value[0].id
    }
    if (selectedProjectId.value) await loadConfig(selectedProjectId.value)
  } finally {
    loading.value = false
  }
}

async function loadConfig(projectId: number) {
  const response = await tenantAdminApi.projectVideoConfig(projectId)
  Object.assign(form, response)
}

function applyTemplate(key: keyof typeof templates) {
  form.label_template = key
  form.labels = [...templates[key].labels]
  form.label_mode = 'preset'
}

function applyTemplateKey(key: string) {
  applyTemplate(key as keyof typeof templates)
}

function addLabel() {
  const label = newLabel.value.trim()
  if (!label) return
  if (!form.labels.includes(label)) form.labels.push(label)
  newLabel.value = ''
}

function removeLabel(label: string) {
  form.labels = form.labels.filter((item) => item !== label)
}

function addReason() {
  const label = newReason.value.trim()
  if (!label) return
  const code = `custom-${Date.now()}`
  form.return_reasons.push({ code, label })
  newReason.value = ''
}

function removeReason(code: string) {
  form.return_reasons = form.return_reasons.filter((item) => item.code !== code)
}

async function saveConfig() {
  if (!selectedProjectId.value) return
  saving.value = true
  try {
    await tenantAdminApi.saveProjectVideoConfig(selectedProjectId.value, { ...form })
    ElMessage.success('项目视频标签与标注规则已保存')
  } finally {
    saving.value = false
  }
}

onMounted(loadProjects)
</script>

<template>
  <section v-loading="loading" class="project-settings">
    <header class="project-settings__header">
      <div>
        <p>PROJECT VIDEO CONFIG</p>
        <h3>项目、视频与标签</h3>
        <span>标注说明、最短时长、预设标签和回退原因都在项目级维护。</span>
      </div>
      <div class="project-settings__links">
        <el-button @click="router.push('/batches')">批次管理</el-button>
        <el-button type="primary" @click="router.push('/batches/create')">创建视频批次</el-button>
      </div>
    </header>

    <el-card shadow="never">
      <el-form label-position="top" class="project-settings__form">
        <el-form-item label="当前项目">
          <el-select
            v-model="selectedProjectId"
            placeholder="选择项目"
            size="large"
            @change="loadConfig"
          >
            <el-option v-for="project in projects" :key="project.id" :label="project.name" :value="project.id" />
          </el-select>
        </el-form-item>

        <div class="project-settings__row">
          <el-form-item label="帧率">
            <el-input-number v-model="form.fps" :min="1" :max="120" :precision="0" />
          </el-form-item>
          <el-form-item label="最短区间（秒）">
            <el-input-number v-model="form.min_interval_seconds" :min="0" :max="3600" :precision="2" :step="0.1" />
          </el-form-item>
          <el-form-item label="标签要求">
            <el-switch v-model="form.require_label" active-text="必须填写标签" inactive-text="允许空标签" />
          </el-form-item>
        </div>

        <el-form-item label="标注说明">
          <el-input v-model="form.instructions" type="textarea" :rows="4" maxlength="4000" show-word-limit />
        </el-form-item>

        <div class="project-settings__label-box">
          <div class="project-settings__section-title">
            <div>
              <h4>标签方案</h4>
              <span>预设模式下标注员只能选择；自由模式下可以输入。</span>
            </div>
            <el-radio-group v-model="form.label_mode">
              <el-radio-button value="preset">预设标签</el-radio-button>
              <el-radio-button value="free">自由输入</el-radio-button>
            </el-radio-group>
          </div>

          <div class="project-settings__templates">
            <el-button
              v-for="(template, key) in templates"
              :key="key"
              :type="form.label_template === key ? 'primary' : 'default'"
              @click="applyTemplateKey(key)"
            >
              <Icon icon="lucide:sparkles" /> {{ template.label }}
            </el-button>
          </div>

          <template v-if="form.label_mode === 'preset'">
            <div class="project-settings__reasons">
              <el-tag
                v-for="label in form.labels"
                :key="label"
                closable
                size="large"
                type="primary"
                @close="removeLabel(label)"
              >
                {{ label }}
              </el-tag>
            </div>
            <div class="project-settings__add-reason">
              <el-input v-model="newLabel" placeholder="添加自定义标签" @keyup.enter="addLabel" />
              <el-button @click="addLabel">添加标签</el-button>
            </div>
          </template>
        </div>

        <div class="project-settings__reason-box">
          <div class="project-settings__section-title">
            <div>
              <h4>标注员回退原因池</h4>
              <span>常见问题直接选择；“其他原因”必须手动填写。</span>
            </div>
          </div>
          <div class="project-settings__reasons">
            <el-tag
              v-for="reason in form.return_reasons"
              :key="reason.code"
              closable
              size="large"
              @close="removeReason(reason.code)"
            >
              {{ reason.label }}
            </el-tag>
          </div>
          <div class="project-settings__add-reason">
            <el-input v-model="newReason" placeholder="添加新的回退原因" @keyup.enter="addReason" />
            <el-button @click="addReason">添加原因</el-button>
          </div>
        </div>

        <el-button type="primary" size="large" :loading="saving" @click="saveConfig">
          保存项目视频设置
        </el-button>
      </el-form>
    </el-card>
  </section>
</template>

<style scoped>
.project-settings {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.project-settings__header,
.project-settings__section-title,
.project-settings__add-reason {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.project-settings__header > div:first-child > p {
  margin: 0 0 4px;
  color: var(--el-color-primary);
  font: 600 var(--y-font-size-xs) var(--y-font-family-mono);
  letter-spacing: 0.1em;
}

.project-settings__header h3,
.project-settings__section-title h4 {
  margin: 0;
}

.project-settings__header h3 {
  font-size: var(--y-font-size-2xl);
}

.project-settings__header span,
.project-settings__section-title span {
  color: var(--el-text-color-secondary);
}

.project-settings__links {
  display: flex;
  gap: 10px;
}

.project-settings__row {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 18px;
}

.project-settings__label-box,
.project-settings__reason-box {
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding: 18px;
  margin-bottom: 18px;
  background: var(--el-fill-color-lighter);
  border-radius: 12px;
}

.project-settings__templates,
.project-settings__reasons {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.project-settings__add-reason :deep(.el-input) {
  max-width: 420px;
}

@media (max-width: 900px) {
  .project-settings__header,
  .project-settings__section-title {
    align-items: flex-start;
    flex-direction: column;
  }

  .project-settings__row {
    grid-template-columns: 1fr;
  }
}
</style>
