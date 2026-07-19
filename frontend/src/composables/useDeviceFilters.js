import { computed, ref } from 'vue'

export const STATUS_OPTIONS = ['All', 'Available', 'In Use', 'Repair']

/**
 * Shared "Smart Dashboard" toolbar logic (search + status/brand/category
 * filters) used by both `HardwareListView` and `AdminHardwareTab` - keeps
 * their filtering behavior (and the exact set of fields it matches on)
 * identical without duplicating it in both places.
 *
 * @param {import('vue').Ref<Array>} devicesRef - ref/computed holding the
 *   full, unfiltered device list.
 */
export function useDeviceFilters(devicesRef) {
  const searchQuery = ref('')
  const statusFilter = ref('All')
  const brandFilter = ref('All')
  const categoryFilter = ref('All')

  const brandOptions = computed(() => {
    const brands = new Set(devicesRef.value.map((device) => device.brand).filter(Boolean))
    return ['All', ...Array.from(brands).sort((a, b) => a.localeCompare(b))]
  })

  const categoryOptions = computed(() => {
    const categories = new Set(devicesRef.value.map((device) => device.category).filter(Boolean))
    return ['All', ...Array.from(categories).sort((a, b) => a.localeCompare(b))]
  })

  const filteredDevices = computed(() => {
    const query = searchQuery.value.trim().toLowerCase()
    return devicesRef.value.filter((device) => {
      const matchesStatus = statusFilter.value === 'All' || device.status === statusFilter.value
      const matchesBrand = brandFilter.value === 'All' || device.brand === brandFilter.value
      const matchesCategory = categoryFilter.value === 'All' || device.category === categoryFilter.value
      const matchesSearch =
        !query ||
        (device.name || '').toLowerCase().includes(query) ||
        (device.brand || '').toLowerCase().includes(query)
      return matchesStatus && matchesBrand && matchesCategory && matchesSearch
    })
  })

  const hasActiveFilters = computed(
    () =>
      !!searchQuery.value.trim() ||
      statusFilter.value !== 'All' ||
      brandFilter.value !== 'All' ||
      categoryFilter.value !== 'All'
  )

  function clearFilters() {
    searchQuery.value = ''
    statusFilter.value = 'All'
    brandFilter.value = 'All'
    categoryFilter.value = 'All'
  }

  return {
    STATUS_OPTIONS,
    searchQuery,
    statusFilter,
    brandFilter,
    categoryFilter,
    brandOptions,
    categoryOptions,
    filteredDevices,
    hasActiveFilters,
    clearFilters,
  }
}
