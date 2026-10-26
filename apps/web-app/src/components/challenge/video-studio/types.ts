import type { VideoInterval } from '@/libs/intervals'

export type PanelMode = 'annotate' | 'review' | 'admin'

export interface ReturnReason {
  code: string
  label: string
}

export interface AnnotationConfig {
  instructions: string
  require_label: boolean
  min_interval_seconds: number
  label_mode: 'preset' | 'free'
  labels: string[]
  label_template: string
  fps: number
  return_reasons: ReturnReason[]
}

export interface UnitDetail {
  unit_id: number
  status: string
  reject_count: number
  reject_reason: string | null
  video: {
    id: number | null
    filename: string
    path: string | null
    duration: number | null
  }
  current_label: {
    intervals: VideoInterval[]
    version: number
  }
  annotation_config?: AnnotationConfig
  annotation_settings?: AnnotationConfig
  annotator_name?: string
  reviewer_name?: string
}

export interface RejectHistoryItem {
  rejected_at: string
  reason: string
}

export interface WorkerOption {
  id: number
  name?: string
  email?: string
}
