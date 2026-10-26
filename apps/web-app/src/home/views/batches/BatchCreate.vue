<template>
  <div class="batch-create">
    <div class="batch-create__header">
      <el-button  link @click="$router.back()"><Icon icon="lucide:arrow-left" />返回</el-button>
      <div class="batch-create__title">
        <Icon icon="lucide:layers" :width="22" />
        <span>新建批次</span>
      </div>
    </div>

    <el-card shadow="never" class="batch-create__card" v-loading="initialLoading">
      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-width="120"
        label-position="right"
        style="max-width: 720px"
      >
        <el-form-item label="所属项目" prop="project_id">
          <div class="batch-create__project">
            <el-select
              v-model="form.project_id"
              placeholder="选择项目"
              :loading="projectLoading"
              @change="onProjectChange"
            >
              <el-option v-for="p in projects" :key="p.id" :label="p.name" :value="p.id" />
            </el-select>
            <el-button v-if="projects.length === 0" @click="createDefaultProject">
              创建默认项目
            </el-button>
          </div>
        </el-form-item>

        <el-form-item label="批次名称" prop="name">
          <el-input v-model="form.name" placeholder="如:第1期-东城路采" maxlength="128" show-word-limit />
        </el-form-item>

        <el-form-item label="Slug" prop="slug">
          <el-input
            v-model="form.slug"
            placeholder="小写字母数字短横线,项目内唯一,如:east-rd-round-1"
            maxlength="64"
          />
        </el-form-item>

        <el-form-item label="任务类型" prop="mission">
          <el-input :model-value="missionLabel" disabled />
        </el-form-item>

        <el-form-item label="上传视频">
          <ChallengeVideoUpload
            :project-id="form.project_id"
            @uploaded="onVideosUploaded"
          />
        </el-form-item>

        <el-form-item label="已上传视频" prop="media_ids">
          <el-select
            v-model="form.media_ids"
            multiple
            filterable
            placeholder="选择本轮标注的视频"
            style="width: 100%"
          >
            <el-option
              v-for="media in mediaOptions"
              :key="media.id"
              :label="`${media.filename}${media.duration ? ` (${Math.round(media.duration)}s)` : ''}`"
              :value="media.id"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="分派策略">
          <el-tag type="success">轮询自动分配</el-tag>
        </el-form-item>

        <el-form-item label="标注员池" prop="assignees">
          <el-select
            v-model="form.assignees"
            multiple
            filterable
            placeholder="标注员 user_id 列表"
            style="width: 100%"
          >
            <el-option v-for="u in annotatorOptions" :key="u.id" :label="`#${u.id} ${u.name || u.email || ''}`" :value="u.id" />
          </el-select>
        </el-form-item>

        <el-form-item label="审核员池" prop="reviewers">
          <el-select v-model="form.reviewers" multiple filterable placeholder="可选" style="width: 100%">
            <el-option v-for="u in reviewerOptions" :key="u.id" :label="`#${u.id} ${u.name || u.email || ''}`" :value="u.id" />
          </el-select>
        </el-form-item>

        <el-form-item>
          <el-button type="primary" :loading="submitting" @click="onSubmit">创建</el-button>
          <el-button @click="$router.back()">取消</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { Icon } from '@iconify/vue'
import { batchesApi, challengeApi, projectsApi } from '@/api'
import { Mission } from '@/constants'
import { useBatchProject } from './useBatchProject'
import ChallengeVideoUpload from '@/components/challenge/ChallengeVideoUpload.vue'

const route = useRoute()
const router = useRouter()
const {
  projects,
  loading: projectLoading,
  init: initProject,
  loadProjects,
  selectProject,
} = useBatchProject()

const formRef = ref<FormInstance | null>(null)
const submitting = ref(false)
const initialLoading = ref(false)
const mediaOptions = ref<any[]>([])
const annotatorOptions = ref<any[]>([])
const reviewerOptions = ref<any[]>([])

const form = reactive({
  project_id: null as number | null,
  name: '',
  slug: '',
  mission: Mission.VideoEvents,
  media_ids: [] as number[],
  assignee_strategy: 'round_robin',
  assignees: [] as number[],
  reviewers: [] as number[],
  qa_pool: [] as number[],
})

const missionLabel = computed(() => '视频片段标注')

const rules: FormRules = {
  project_id: [{ required: true, message: '请选择项目', trigger: 'change' }],
  name: [{ required: true, message: '请输入批次名称', trigger: 'blur' }],
  slug: [
    { required: true, message: '请输入 slug', trigger: 'blur' },
    {
      pattern: /^[a-z0-9][a-z0-9-]*$/,
      message: '小写字母数字短横线,字母数字开头',
      trigger: 'blur',
    },
  ],
  mission: [{ required: true, message: '请选择 mission', trigger: 'change' }],
  media_ids: [
    {
      validator: (_r, value, cb) => {
        if (!value || value.length === 0) {
          cb(new Error('请至少上传并选择一个视频'))
        } else {
          cb()
        }
      },
      trigger: 'change',
    },
  ],
  assignees: [
    {
      validator: (_r, value, cb) => {
        if (!value || value.length === 0) {
          cb(new Error('请配置标注员池'))
        } else {
          cb()
        }
      },
      trigger: 'change',
    },
  ],
  reviewers: [
    {
      validator: (_r, value, cb) => {
        if (!value || value.length === 0) {
          cb(new Error('请配置审核员池'))
        } else {
          cb()
        }
      },
      trigger: 'change',
    },
  ],
}

const onProjectChange = async (pid: number | null) => {
  if (pid == null) return
  await selectProject(pid)
  await Promise.all([loadRolePools(), loadMedia(pid)])
}

const createDefaultProject = async () => {
  const suffix = Date.now().toString(36)
  const project = await projectsApi.create({
    name: '视频片段标注项目',
    slug: `video-annotation-${suffix}`,
  })
  await loadProjects()
  form.project_id = project.id
  await onProjectChange(project.id)
  ElMessage.success('项目已创建')
}

const loadRolePools = async () => {
  const res = await challengeApi.userPools()
  annotatorOptions.value = res.annotators ?? []
  reviewerOptions.value = res.reviewers ?? []
}

const loadMedia = async (pid: number) => {
  const res = await challengeApi.listMedia(pid)
  mediaOptions.value = res.items ?? []
}

const onVideosUploaded = async (media: any[]) => {
  const ids = media.map((item) => item.media_id ?? item.id).filter(Boolean)
  form.media_ids = [...new Set([...form.media_ids, ...ids])]
  if (form.project_id) await loadMedia(form.project_id)
}

const onSubmit = async () => {
  if (!formRef.value) return
  try {
    await formRef.value.validate()
  } catch {
    return
  }
  const payload: any = {
    name: form.name.trim(),
    slug: form.slug.trim(),
    mission: form.mission,
    media_ids: form.media_ids,
    assignee_strategy: form.assignee_strategy,
    assignees: form.assignees,
    reviewers: form.reviewers,
    qa_pool: [],
    frame_range: {},
    sampling_rate: 1.0,
  }

  submitting.value = true
  try {
    const rec = await batchesApi.createBatch(form.project_id as number, payload)
    const spawned = await batchesApi.spawnBatch(rec.id, {})
    ElMessage.success(`已创建并发布 ${spawned.created ?? spawned.total ?? 0} 个任务`)
    router.push({ name: 'batches-detail', params: { id: rec.id } })
  } finally {
    submitting.value = false
  }
}

watch(
  () => route.query.project_id,
  (v) => {
    if (v != null && !form.project_id) {
      form.project_id = Number(v)
    }
  },
  { immediate: true },
)

onMounted(async () => {
  initialLoading.value = true
  try {
    await initProject()
    const initialProjectId = route.query.project_id
      ? Number(route.query.project_id)
      : projects.value[0]?.id
    if (initialProjectId) {
      form.project_id = initialProjectId
      await selectProject(initialProjectId)
      await Promise.all([loadRolePools(), loadMedia(form.project_id as number)])
    } else {
      // A new tenant should be able to upload immediately; create the single
      // default project instead of leaving the upload control disabled.
      await createDefaultProject()
    }
  } finally {
    initialLoading.value = false
  }
})
</script>

<style scoped>
.batch-create {
  padding: 16px 24px;
}

.batch-create__header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.batch-create__title {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 18px;
  font-weight: 600;
}

.batch-create__card {
  border: 1px solid var(--y-color-divider);
}

.batch-create__project {
  display: flex;
  gap: 8px;
  width: 100%;
}

.batch-create__project :deep(.el-select) {
  flex: 1;
}

.batch-create__hint {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  margin-top: 4px;
  line-height: 1.5;
}
</style>
