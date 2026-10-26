import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import DemoLoginPanel from './DemoLoginPanel.vue'

const ButtonStub = {
  props: ['loading'],
  emits: ['click'],
  template: '<button :disabled="loading" @click="$emit(\'click\')"><slot /></button>',
}

describe('DemoLoginPanel', () => {
  it('renders all three demo identities', () => {
    const wrapper = mount(DemoLoginPanel, {
      global: { stubs: { ElButton: ButtonStub, Icon: true } },
    })

    expect(wrapper.text()).toContain('平台管理员')
    expect(wrapper.text()).toContain('租户管理员')
    expect(wrapper.text()).toContain('标注员')
    expect(wrapper.text()).toContain('审核员')
  })

  it('emits the selected identity', async () => {
    const wrapper = mount(DemoLoginPanel, {
      global: { stubs: { ElButton: ButtonStub, Icon: true } },
    })

    await wrapper.get('[data-testid="demo-login-annotator"]').trigger('click')

    expect(wrapper.emitted('select')).toEqual([['annotator']])
  })

  it('disables the active identity while logging in', () => {
    const wrapper = mount(DemoLoginPanel, {
      props: { loadingIdentity: 'tenant-admin' },
      global: { stubs: { ElButton: ButtonStub, Icon: true } },
    })

    expect(
      wrapper.get('[data-testid="demo-login-tenant-admin"]').attributes('disabled'),
    ).toBeDefined()
  })
})
