import { describe, expect, it } from 'vitest'

import {
  extractIntervals,
  totalDuration,
  validateIntervals,
  withObjectIds,
} from './intervals'

describe('video interval validation', () => {
  it('extracts time ranges from label objects and ignores removals', () => {
    expect(
      extractIntervals([
        {
          id: 'a',
          frame_intervals: [{ time_start: 0, time_end: 2.5 }],
          attributes: { label: '抓取' },
        },
        {
          id: 'removed',
          frame_intervals: [{ time_start: 2.5, time_end: 4 }],
          attributes: { opType: 'remove' },
        },
      ]),
    ).toEqual([{ start: 0, end: 2.5, label: '抓取' }])
  })

  it('uses the taxonomy category when an object has no free-text label', () => {
    expect(
      extractIntervals([
        {
          object_type: '抓取动作',
          frame_intervals: [{ time_start: 1, time_end: 2 }],
        },
      ]),
    ).toEqual([{ start: 1, end: 2, label: '抓取动作' }])
  })

  it('rejects touching intervals under the selected closed-interval rule', () => {
    const result = validateIntervals([
      { start: 0, end: 5 },
      { start: 5, end: 8 },
    ])

    expect(result.valid).toBe(false)
    expect(result.error).toContain('重叠')
  })

  it('accepts separated intervals and sums their durations', () => {
    const intervals = [
      { start: 0, end: 2.5 },
      { start: 3, end: 7.25 },
    ]
    expect(validateIntervals(intervals, 10)).toEqual({ valid: true })
    expect(totalDuration(intervals)).toBeCloseTo(6.75)
  })

  it('adds label-v2 object ids without changing the editor object', () => {
    const original = {
      label_uuid: 'editor-id',
      frame_intervals: [{ time_start: 0, time_end: 2 }],
      attributes: { label: '抓取' },
    }

    expect(withObjectIds([original])).toEqual([
      { ...original, id: 'editor-id' },
    ])
    expect(original).not.toHaveProperty('id')
  })
})
