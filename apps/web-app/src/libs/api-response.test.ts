import { describe, expect, it } from 'vitest'

import { isBusinessEnvelope } from './api-response'

describe('business response detection', () => {
  it('treats numeric status payloads as response envelopes', () => {
    expect(isBusinessEnvelope({ status: 0, data: {} })).toBe(true)
    expect(isBusinessEnvelope({ status: 500, statusText: '失败' })).toBe(true)
  })

  it('does not treat task status strings as response envelopes', () => {
    expect(isBusinessEnvelope({ unit_id: 7, status: 'assigned' })).toBe(false)
    expect(isBusinessEnvelope({ unit_id: 7, status: 'under_review' })).toBe(false)
  })
})
