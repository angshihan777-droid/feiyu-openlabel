<script setup lang="ts">
import { shallowRef } from 'vue'
import { ElMessage } from 'element-plus'
import type { PanelMode, ReturnReason, WorkerOption } from './types'

const props = defineProps<{
  mode: PanelMode
  saving: boolean
  submitting: boolean
  reviewing: boolean
  canSubmit: boolean
  total: number
  count: number
  returnReasons: ReturnReason[]
  annotators: WorkerOption[]
}>()

const emit = defineEmits<{
  save: []
  submit: []
  approve: []
  reject: []
  returnVideo: [payload: { code: string; detail: string }]
  adminAction: [payload: { action: 'confirm_issue' | 'return_to_annotator' | 'void'; reason: string }]
  reassign: [payload: { newAssigneeId: number; reason: string }]
}>()

const returnDialogOpen = shallowRef(false)
const returnReasonCode = shallowRef('')
const returnReasonDetail = shallowRef('')
const adminReason = shallowRef('')
const adminReassignId = shallowRef<number | null>(null)

function openReturnDialog() {
  returnReasonCode.value = props.returnReasons[0]?.code ?? 'other'
  returnReasonDetail.value = ''
  returnDialogOpen.value = true
}

function confirmReturn() {
  if (returnReasonCode.value === 'other' && !returnReasonDetail.value.trim()) {
    ElMessage.warning('选择“其他原因”时必须填写说明')
    return
  }
  emit('returnVideo', {
    code: returnReasonCode.value,
    detail: returnReasonDetail.value,
  })
  returnDialogOpen.value = false
}

function reassign() {
  if (adminReassignId.value == null) {
    ElMessage.warning('请选择新的标注员')
    return
  }
  emit('reassign', {
    newAssigneeId: adminReassignId.value,
    reason: adminReason.value.trim(),
  })
}
</script>

<template>
  <section v-if="mode === 'admin'" class="review-actions__admin">
    <h3>管理员复核</h3>
    <el-input
      v-model="adminReason"
      type="textarea"
      :rows="3"
      placeholder="填写复核说明（可选）"
    />
    <div class="review-actions__inline">
      <el-button
        type="success"
        :loading="reviewing"
        @click="emit('adminAction', { action: 'confirm_issue', reason: adminReason.trim() })"
      >
        确认视频有问题
      </el-button>
      <el-button
        :loading="reviewing"
        @click="emit('adminAction', { action: 'return_to_annotator', reason: adminReason.trim() })"
      >
        退回标注员
      </el-button>
      <el-button
        type="danger"
        plain
        :loading="reviewing"
        @click="emit('adminAction', { action: 'void', reason: adminReason.trim() })"
      >
        作废任务
      </el-button>
    </div>
    <div class="review-actions__reassign">
      <el-select v-model="adminReassignId" placeholder="选择新的标注员" filterable>
        <el-option
          v-for="worker in annotators"
          :key="worker.id"
          :label="worker.name || worker.email || `#${worker.id}`"
          :value="worker.id"
        />
      </el-select>
      <el-button :loading="reviewing" @click="reassign">重新分配</el-button>
    </div>
  </section>

  <footer class="review-actions__footer">
    <div>
      <strong>有效时长 {{ total.toFixed(2) }} 秒</strong>
      <small>共 {{ count }} 个区间</small>
    </div>
    <div class="review-actions__footer-actions">
      <template v-if="mode === 'annotate'">
        <el-button type="warning" plain @click="openReturnDialog">回退视频</el-button>
        <el-button :loading="saving" @click="emit('save')">保存草稿</el-button>
        <el-button
          type="primary"
          :loading="submitting"
          :disabled="!canSubmit"
          @click="emit('submit')"
        >
          提交标注
        </el-button>
      </template>
      <template v-else-if="mode === 'review'">
        <el-button type="danger" :loading="reviewing" @click="emit('reject')">驳回</el-button>
        <el-button type="success" :loading="reviewing" @click="emit('approve')">通过</el-button>
      </template>
    </div>
  </footer>

  <el-dialog v-model="returnDialogOpen" title="回退视频给管理员" width="520px">
    <p class="review-actions__dialog-hint">
      回退后任务不进入普通审核，由租户管理员确认视频是否确实有问题。
    </p>
    <el-radio-group v-model="returnReasonCode" class="review-actions__reason-list">
      <el-radio
        v-for="reason in returnReasons"
        :key="reason.code"
        :value="reason.code"
        border
      >
        {{ reason.label }}
      </el-radio>
    </el-radio-group>
    <el-input
      v-if="returnReasonCode === 'other'"
      v-model="returnReasonDetail"
      type="textarea"
      :rows="3"
      placeholder="请填写具体原因"
    />
    <template #footer>
      <el-button @click="returnDialogOpen = false">取消</el-button>
      <el-button type="warning" @click="confirmReturn">确认回退</el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.review-actions__admin {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 14px;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 10px;
}

.review-actions__admin h3 {
  margin: 0;
  font-size: var(--y-font-size-lg);
}

.review-actions__inline,
.review-actions__footer,
.review-actions__footer-actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px;
}

.review-actions__reassign {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 12px;
}

.review-actions__footer {
  justify-content: space-between;
  padding-top: 18px;
  margin-top: 18px;
  border-top: 1px solid var(--el-border-color-lighter);
}

.review-actions__footer > div:first-child {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.review-actions__footer small,
.review-actions__dialog-hint {
  color: var(--el-text-color-secondary);
}

.review-actions__reason-list {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  margin: 14px 0;
}

.review-actions__reason-list :deep(.el-radio) {
  margin-right: 0;
}

@media (max-width: 680px) {
  .review-actions__footer {
    align-items: flex-start;
    flex-direction: column;
  }

  .review-actions__reason-list {
    grid-template-columns: 1fr;
  }
}
</style>
