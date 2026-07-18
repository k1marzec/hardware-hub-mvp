<script setup>
import { computed } from 'vue'

const props = defineProps({
  status: {
    type: String,
    default: 'Unknown',
  },
})

// Maps raw backend status values to the label/color shown in the UI.
const STYLES = {
  Available: { label: 'Available', classes: 'bg-gray-900 text-white' },
  'In Use': { label: 'In Use', classes: 'bg-gray-200 text-gray-600' },
  Repair: { label: 'In Repair', classes: 'bg-red-600 text-white' },
}

const config = computed(
  () => STYLES[props.status] ?? { label: props.status || 'Unknown', classes: 'bg-gray-100 text-gray-500' },
)
</script>

<template>
  <span class="inline-flex items-center rounded-full px-3 py-1 text-xs font-semibold" :class="config.classes">
    {{ config.label }}
  </span>
</template>
