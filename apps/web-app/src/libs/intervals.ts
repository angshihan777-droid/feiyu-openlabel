export interface VideoInterval {
  start: number
  end: number
  label?: string
}

export interface IntervalValidation {
  valid: boolean
  error?: string
}

export function withObjectIds(
  objects: Array<Record<string, any>>,
): Array<Record<string, any>> {
  return (objects || []).map((object) => {
    if (object.id != null) return { ...object }
    if (object.label_uuid == null) return { ...object }
    return { ...object, id: String(object.label_uuid) }
  })
}

function asSeconds(value: unknown): number | null {
  if (typeof value === 'boolean') return null
  const number = Number(value)
  return Number.isFinite(number) ? number : null
}

export function extractIntervals(objects: Array<Record<string, any>>): VideoInterval[] {
  const result: VideoInterval[] = []
  for (const object of objects || []) {
    if (object?.attributes?.opType === 'remove') continue
    const ranges = Array.isArray(object?.frame_intervals)
      ? object.frame_intervals
      : object?.start != null && object?.end != null
        ? [object]
        : []
    const rawLabel =
      object?.attributes?.label ??
      object?.attributes?.name ??
      object?.attributes?.value ??
      object?.label ??
      object?.object_type ??
      object?.ol_type_
    const label = typeof rawLabel === 'string' && rawLabel.trim() ? rawLabel.trim() : undefined
    for (const range of ranges) {
      const start = asSeconds(range?.time_start ?? range?.start)
      const end = asSeconds(range?.time_end ?? range?.end)
      if (start == null || end == null) continue
      result.push(label ? { start, end, label } : { start, end })
    }
  }
  return result
}

export function validateIntervals(
  intervals: VideoInterval[],
  duration?: number,
): IntervalValidation {
  if (!Array.isArray(intervals) || intervals.length === 0) {
    return { valid: false, error: '至少需要一个有效区间' }
  }
  const normalized = [...intervals]
    .map((interval) => ({
      ...interval,
      start: asSeconds(interval.start),
      end: asSeconds(interval.end),
    }))
    .sort((a, b) => (a.start ?? 0) - (b.start ?? 0))

  for (const interval of normalized) {
    if (interval.start == null || interval.end == null) {
      return { valid: false, error: '时间必须是有限数字' }
    }
    if (interval.start < 0) {
      return { valid: false, error: '区间起点不能小于 0' }
    }
    if (interval.end <= interval.start) {
      return { valid: false, error: '区间结束时间必须大于开始时间' }
    }
    if (duration != null && interval.end > duration) {
      return { valid: false, error: '区间超出视频时长' }
    }
  }

  for (let index = 0; index < normalized.length - 1; index += 1) {
    const previous = normalized[index]!
    const current = normalized[index + 1]!
    if (previous.end! >= current.start!) {
      return {
        valid: false,
        error:
          `区间重叠: [${previous.start}, ${previous.end}] ` +
          `与 [${current.start}, ${current.end}]`,
      }
    }
  }
  return { valid: true }
}

export function totalDuration(intervals: VideoInterval[]): number {
  return intervals.reduce((total, interval) => total + interval.end - interval.start, 0)
}
