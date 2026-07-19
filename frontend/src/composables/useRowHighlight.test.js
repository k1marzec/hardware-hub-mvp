import { mount } from '@vue/test-utils'
import { defineComponent } from 'vue'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { useRowHighlight } from './useRowHighlight'

// A minimal host component: `onUnmounted` (used internally for cleanup)
// only works inside an active component instance, so the composable can't
// be called directly at the top level of a test.
function mountHarness() {
  return mount(
    defineComponent({
      setup() {
        return useRowHighlight()
      },
      template: '<div></div>',
    }),
  )
}

describe('useRowHighlight', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    Element.prototype.scrollIntoView = vi.fn()
  })

  afterEach(() => {
    vi.useRealTimers()
    document.body.innerHTML = ''
  })

  it('scrolls to and highlights a row that already exists in the DOM', () => {
    const row = document.createElement('div')
    row.id = 'device-42'
    document.body.appendChild(row)

    const wrapper = mountHarness()
    wrapper.vm.scrollToDevice(42)

    expect(row.scrollIntoView).toHaveBeenCalledWith({ behavior: 'smooth', block: 'center' })
    expect(wrapper.vm.highlightedId).toBe(42)
  })

  it('fades the highlight back out on its own after 2s', () => {
    const row = document.createElement('div')
    row.id = 'device-7'
    document.body.appendChild(row)

    const wrapper = mountHarness()
    wrapper.vm.scrollToDevice(7)
    expect(wrapper.vm.highlightedId).toBe(7)

    vi.advanceTimersByTime(2000)
    expect(wrapper.vm.highlightedId).toBe(null)
  })

  it('retries until the row appears in the DOM instead of giving up immediately', () => {
    const wrapper = mountHarness()
    wrapper.vm.scrollToDevice(99)
    expect(wrapper.vm.highlightedId).toBe(null) // row not mounted yet

    const row = document.createElement('div')
    row.id = 'device-99'
    document.body.appendChild(row)

    vi.advanceTimersByTime(150) // next retry now finds it
    expect(wrapper.vm.highlightedId).toBe(99)
  })

  it('gives up after 10 retries if the row never appears', () => {
    const wrapper = mountHarness()
    wrapper.vm.scrollToDevice(123)

    vi.advanceTimersByTime(150 * 10)
    expect(wrapper.vm.highlightedId).toBe(null)
  })
})
