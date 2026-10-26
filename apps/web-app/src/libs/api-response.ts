export interface BusinessEnvelope {
  status: number
  statusText?: string
  data?: unknown
}

export function isBusinessEnvelope(value: unknown): value is BusinessEnvelope {
  return Boolean(
    value
    && typeof value === 'object'
    && typeof (value as { status?: unknown }).status === 'number',
  )
}
