import { onUnmounted, ref } from 'vue'

/**
 * Shared "locate + highlight a table row" behavior, used by both
 * `HardwareListView` and `AdminHardwareTab` (e.g. from the Inventory
 * Auditor's "locate" icon): smooth-scrolls to a device's row by DOM id
 * (`device-<id>`) and briefly highlights it, fading back out on its own.
 *
 * `attempt` retries a few times before giving up, since the row may not
 * exist in the DOM yet right after mount (data still loading).
 */
export function useRowHighlight() {
  const highlightedId = ref(null)
  let highlightTimeoutId = null

  function scrollToDevice(deviceId, attempt = 0) {
    const row = document.getElementById(`device-${deviceId}`)
    if (!row) {
      if (attempt < 10) setTimeout(() => scrollToDevice(deviceId, attempt + 1), 150)
      return
    }

    row.scrollIntoView({ behavior: 'smooth', block: 'center' })

    highlightedId.value = deviceId
    clearTimeout(highlightTimeoutId)
    highlightTimeoutId = setTimeout(() => {
      highlightedId.value = null
    }, 2000)
  }

  onUnmounted(() => clearTimeout(highlightTimeoutId))

  return { highlightedId, scrollToDevice }
}
