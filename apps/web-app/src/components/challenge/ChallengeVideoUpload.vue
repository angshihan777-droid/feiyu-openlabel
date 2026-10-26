<script setup lang="ts">
import { computed, ref } from 'vue'
import { ElMessage, type UploadFile, type UploadUserFile } from 'element-plus'
import { challengeApi } from '@/api'

const MAX_VIDEO_BYTES = 500 * 1024 * 1024

const props = defineProps<{
  projectId: number | null
}>()

const emit = defineEmits<{
  uploaded: [media: Array<Record<string, any>>]
}>()

const files = ref<UploadUserFile[]>([])
const uploading = ref(false)
const completed = ref(0)

const progress = computed(() => {
  if (!files.value.length) return 0
  return Math.round((completed.value / files.value.length) * 100)
})

function beforeUpload(file: UploadFile) {
  if (props.projectId == null) {
    ElMessage.warning('请先选择项目')
    return false
  }
  if (file.size != null && file.size > MAX_VIDEO_BYTES) {
    ElMessage.error('单个视频不能超过 500MB')
    return false
  }
  return true
}

async function uploadAll() {
  if (props.projectId == null) {
    ElMessage.warning('请先选择项目')
    return
  }
  const candidates: File[] = files.value.flatMap((item) =>
    item.raw ? [item.raw as File] : [],
  )
  if (!candidates.length) {
    ElMessage.warning('请选择视频')
    return
  }

  uploading.value = true
  completed.value = 0
  const uploaded: Array<Record<string, any>> = []
  try {
    for (const file of candidates) {
      if (file.size > MAX_VIDEO_BYTES) {
        throw new Error(`${file.name} 超过 500MB`)
      }
      const media = await challengeApi.uploadVideo(file, props.projectId)
      uploaded.push(media)
      completed.value += 1
    }
    emit('uploaded', uploaded)
    files.value = []
    ElMessage.success(`已上传 ${uploaded.length} 个视频`)
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '上传失败')
  } finally {
    uploading.value = false
  }
}
</script>

<template>
  <div class="video-upload">
    <el-upload
      v-model:file-list="files"
      :auto-upload="false"
      :before-upload="beforeUpload"
      :disabled="uploading || projectId == null"
      accept="video/mp4,video/webm,video/quicktime,video/x-matroska,video/x-msvideo"
      multiple
      drag
    >
      <div class="video-upload__drop">拖入视频，或点击选择。单文件上限 500MB</div>
    </el-upload>
    <div class="video-upload__actions">
      <el-progress
        v-if="uploading"
        :percentage="progress"
        :stroke-width="8"
        class="video-upload__progress"
      />
      <el-button
        type="primary"
        :loading="uploading"
        :disabled="projectId == null || files.length === 0"
        @click="uploadAll"
      >
        上传 {{ files.length || '' }} 个视频
      </el-button>
    </div>
  </div>
</template>

<style scoped>
.video-upload {
  width: 100%;
}

.video-upload__drop {
  padding: 20px;
  color: var(--el-text-color-secondary);
}

.video-upload__actions {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 10px;
}

.video-upload__progress {
  flex: 1;
  max-width: 360px;
}
</style>
