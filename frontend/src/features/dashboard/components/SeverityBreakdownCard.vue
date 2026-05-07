<script setup lang="ts">
import { computed } from 'vue'

import InsightPanel from '../../../components/dashboard/InsightPanel.vue'
import type { DefectPoint } from '../types'
import { useSeverityBreakdown } from '../composables/useSeverityBreakdown'

const props = defineProps<{
  defects: DefectPoint[]
}>()

const { bySeverity, total } = useSeverityBreakdown(computed(() => props.defects))

function barClass(severity: DefectPoint['severity']) {
  switch (severity) {
    case 'critical':
      return 'bg-destructive'
    case 'high':
      return 'bg-accent'
    case 'medium':
      return 'bg-secondary'
    case 'low':
    default:
      return 'bg-border/50'
  }
}

const labelClass = 'text-xs font-medium uppercase tracking-wide'
</script>

<template>
  <InsightPanel title="Issue severity breakdown" description="Distribution of defect signals by severity.">
    <template #meta>
      <p class="text-xs text-muted-foreground">
        Total: <span class="text-foreground">{{ total }}</span>
      </p>
    </template>
    <div class="px-6 pb-6 pt-2">
      <div class="flex h-2 overflow-hidden rounded-full border border-border/70 bg-card">
        <div
          v-for="row in bySeverity"
          :key="row.severity"
          :class="barClass(row.severity)"
          :style="{ width: `${row.percent}%` }"
        />
      </div>

      <div class="mt-4 space-y-3">
        <div
          v-for="row in bySeverity"
          :key="row.severity"
          class="flex items-center justify-between gap-4"
        >
          <div class="flex items-center gap-2">
            <span class="inline-flex h-2.5 w-2.5 rounded-full" :class="barClass(row.severity)" />
            <span :class="labelClass">{{ row.severity }}</span>
          </div>
          <div class="text-sm">
            <span class="font-medium text-foreground">{{ row.count }}</span>
            <span class="ml-2 text-xs text-muted-foreground">{{ row.percent }}%</span>
          </div>
        </div>
      </div>
    </div>
  </InsightPanel>
</template>

