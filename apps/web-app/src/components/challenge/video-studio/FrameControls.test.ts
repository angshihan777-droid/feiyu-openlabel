import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import FrameControls from './FrameControls.vue'

const ButtonStub = {
  emits: ['click'],
  template: '<button v-bind="$attrs" @click="$emit(\'click\')"><slot /></button>',
}

const InputNumberStub = {
  inheritAttrs: false,
  props: ['modelValue'],
  emits: ['update:modelValue'],
  template: '<input :value="modelValue" />',
}

describe('FrameControls', () => {
  it('keeps transport controls independent from interval editing', async () => {
    const wrapper = mount(FrameControls, {
      props: {
        currentFrame: 12,
        totalFrames: 100,
        currentTime: 1.2,
        previewUrl: '',
        selectionHint: '空格设置起止',
        isPlaying: false,
        fps: 10,
      },
      global: {
        stubs: {
          ElButton: ButtonStub,
          ElInputNumber: InputNumberStub,
          Icon: true,
        },
      },
    })

    const buttons = wrapper.findAll('button')
    await buttons[0]!.trigger('click')
    await buttons[1]!.trigger('click')
    await buttons[2]!.trigger('click')

    expect(wrapper.text()).toContain('帧 12 / 100')
    expect(wrapper.emitted('previousFrame')).toHaveLength(1)
    expect(wrapper.emitted('togglePlayback')).toHaveLength(1)
    expect(wrapper.emitted('nextFrame')).toHaveLength(1)
  })
})
