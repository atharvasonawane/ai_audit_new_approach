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
  <InsightPanel title="Issue Severity Breakdown" description="Distribution of defect signals by impact level.">
    <template #meta>
      <div class="px-3 py-1 bg-accent/30 rounded-full border border-border">
        <p class="text-[11px] font-bold tracking-wider text-muted-foreground uppercase text-right">
          Total Signals: <span class="text-foreground ml-1">{{ total }}</span>
        </p>
      </div>
    </template>
    <div class="p-6 md:p-8 flex flex-col justify-center h-full">
      <div class="flex h-3 md:h-4 w-full overflow-hidden rounded-full border border-border bg-card">
        <div
          v-for="row in bySeverity"
          :key="row.severity"
          :class="barClass(row.severity)"
          class="transition-all duration-300"
          :style="{ width: `${row.percent}%` }"
        />
      </div>

      <div class="mt-8 grid grid-cols-2 md:grid-cols-4 gap-6">
        <div
          v-for="row in bySeverity"
          :key="row.severity"
          class="flex flex-col gap-2 p-4 rounded-lg border border-border/50 bg-card/30"
        >
          <div class="flex items-center gap-2">
            <span class="inline-flex h-2.5 w-2.5 rounded-full" :class="barClass(row.severity)" />
            <span :class="labelClass">{{ row.severity }}</span>
          </div>
          <div class="flex items-end justify-between mt-1">
            <span class="text-2xl font-bold tracking-tight text-foreground">{{ row.count }}</span>
            <span class="text-sm font-medium text-muted-foreground mb-0.5">{{ row.percent }}%</span>
          </div>
        </div>
      </div>
    </div>
  </InsightPanel>
</template>

