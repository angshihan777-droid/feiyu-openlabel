export type FrameInterval = {
  frame_start: number
  frame_end: number
  time_start: number
  time_end: number
}

type BaseObject = {
  id?: string
  label_uuid: string
  object_id?: string
  object_type?: string
  object_uuid?: string
  object_attributes?: Record<string, any>
  frame_intervals: FrameInterval[]
  attributes: Record<string, any>
}

type Event = BaseObject & {
  ol_type_: 'Event'
  event_data?: Record<string, any>
}

type Action = BaseObject & {
  ol_type_: 'Action'
  action_data?: Record<string, any>
}

type Context = BaseObject & {
  ol_type_: 'Context'
  context_data?: Record<string, any>
}

export type { Action, Context, Event }
