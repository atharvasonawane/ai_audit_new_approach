<script setup lang="ts">
import { computed } from 'vue'

import RiskTable from '../../../components/dashboard/RiskTable.vue'
import type { DefectPoint } from '../types'
import { useRiskyFiles } from '../composables/useRiskyFiles'

const props = defineProps<{
  defects: DefectPoint[]
  limit?: number
}>()

const limit = computed(() => props.limit ?? 5)
const { riskyFiles } = useRiskyFiles(computed(() => props.defects), limit.value)
</script>

<template>
  <RiskTable
    title="Top risky files"
    description="Weighted by severity counts."
    :rows="riskyFiles"
  />
</template>

