<template>
        <el-row style="width: 100%">
            <el-col :span="24">
                <el-descriptions title="任务信息" :column="1" :size="size" border direction="vertical">
                    <el-descriptions-item label="任务 ID">{{ jobConfig.unit_id }}</el-descriptions-item>
                    <el-descriptions-item label="视频">{{ jobConfig.stream }}</el-descriptions-item>
                    <el-descriptions-item label="任务类型">视频片段标注</el-descriptions-item>
                    <el-descriptions-item label="状态">{{ jobConfig.status || '进行中' }}</el-descriptions-item>
                </el-descriptions>
            </el-col>
        </el-row>
</template>
<script lang="tsx" setup>
import { ref } from 'vue'
import { jobConfig } from '@/states/job-config'
import {
    ElDescriptions,
    ElDescriptionsItem,
    ElCol,
    ElRow,
} from 'element-plus'
import type { ComponentSize } from 'element-plus'

const size = ref<ComponentSize>('default')

</script>
<style scoped>
:deep(.el-descriptions__content) {
  word-break: break-all;
}
</style>
