import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import StatusBadge from './StatusBadge.vue'

describe('StatusBadge', () => {
  it('renders "Available" with its dark style', () => {
    const wrapper = mount(StatusBadge, { props: { status: 'Available' } })
    expect(wrapper.text()).toBe('Available')
    expect(wrapper.classes()).toContain('bg-gray-900')
  })

  it('renders "In Use" as-is with a light style', () => {
    const wrapper = mount(StatusBadge, { props: { status: 'In Use' } })
    expect(wrapper.text()).toBe('In Use')
    expect(wrapper.classes()).toContain('bg-gray-200')
  })

  it('relabels "Repair" as "In Repair" with a red style', () => {
    const wrapper = mount(StatusBadge, { props: { status: 'Repair' } })
    expect(wrapper.text()).toBe('In Repair')
    expect(wrapper.classes()).toContain('bg-red-600')
  })

  it('falls back to the raw value for an unrecognized status (e.g. dirty seed data)', () => {
    const wrapper = mount(StatusBadge, { props: { status: 'Unknown' } })
    expect(wrapper.text()).toBe('Unknown')
    expect(wrapper.classes()).toContain('bg-gray-100')
  })

  it('falls back to "Unknown" when no status prop is given at all', () => {
    const wrapper = mount(StatusBadge)
    expect(wrapper.text()).toBe('Unknown')
  })
})
