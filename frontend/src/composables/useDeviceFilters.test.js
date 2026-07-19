import { ref } from 'vue'
import { describe, expect, it } from 'vitest'

import { useDeviceFilters } from './useDeviceFilters'

function makeDevices() {
  return ref([
    { id: 1, name: 'MacBook Pro', brand: 'Apple', category: 'Laptop', status: 'Available' },
    { id: 2, name: 'XPS 15', brand: 'Dell', category: 'Laptop', status: 'In Use' },
    { id: 3, name: 'Basilisk V2', brand: 'Razer', category: 'Mouse', status: 'Repair' },
    { id: 4, name: 'No Brand Device', brand: '', category: '', status: 'Available' },
  ])
}

describe('useDeviceFilters', () => {
  it('returns every device and no active filters by default', () => {
    const { filteredDevices, hasActiveFilters } = useDeviceFilters(makeDevices())
    expect(filteredDevices.value).toHaveLength(4)
    expect(hasActiveFilters.value).toBe(false)
  })

  it('builds sorted, deduplicated brand/category option lists prefixed with "All"', () => {
    const { brandOptions, categoryOptions } = useDeviceFilters(makeDevices())
    expect(brandOptions.value).toEqual(['All', 'Apple', 'Dell', 'Razer'])
    expect(categoryOptions.value).toEqual(['All', 'Laptop', 'Mouse'])
  })

  it('filters by status', () => {
    const { statusFilter, filteredDevices } = useDeviceFilters(makeDevices())
    statusFilter.value = 'Repair'
    expect(filteredDevices.value.map((d) => d.id)).toEqual([3])
  })

  it('filters by brand and category together', () => {
    const { brandFilter, categoryFilter, filteredDevices } = useDeviceFilters(makeDevices())
    brandFilter.value = 'Dell'
    categoryFilter.value = 'Laptop'
    expect(filteredDevices.value.map((d) => d.id)).toEqual([2])
  })

  it('search matches name or brand, case-insensitively', () => {
    const { searchQuery, filteredDevices } = useDeviceFilters(makeDevices())
    searchQuery.value = 'apple'
    expect(filteredDevices.value.map((d) => d.id)).toEqual([1])

    searchQuery.value = 'XPS'
    expect(filteredDevices.value.map((d) => d.id)).toEqual([2])
  })

  it('hasActiveFilters/clearFilters reset all filters at once', () => {
    const { searchQuery, statusFilter, brandFilter, categoryFilter, hasActiveFilters, clearFilters } =
      useDeviceFilters(makeDevices())
    searchQuery.value = 'mac'
    statusFilter.value = 'Available'
    brandFilter.value = 'Apple'
    categoryFilter.value = 'Laptop'
    expect(hasActiveFilters.value).toBe(true)

    clearFilters()

    expect(hasActiveFilters.value).toBe(false)
    expect(searchQuery.value).toBe('')
    expect(statusFilter.value).toBe('All')
    expect(brandFilter.value).toBe('All')
    expect(categoryFilter.value).toBe('All')
  })
})
