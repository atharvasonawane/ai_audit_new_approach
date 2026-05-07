<script setup lang="ts">
import { cn } from '../../lib/utils'
import InsightPanel from './InsightPanel.vue'
import SeverityBadge from './SeverityBadge.vue'
import type { Severity } from '../../features/dashboard/types'

export type RiskRow = {
  file: string
  score: number
  defects: number
  topSeverity: Severity
}

defineProps<{
  title: string
  description?: string
  rows: RiskRow[]
  class?: string
}>()
</script>

<template>
  <InsightPanel :title="title" :description="description" :class="cn('', $props.class)">
    <div class="overflow-x-auto">
      <table class="w-full border-collapse text-sm">
        <thead>
          <tr class="text-xs text-muted-foreground">
            <th class="px-6 pb-3 pt-2 text-left font-medium">File</th>
            <th class="px-6 pb-3 pt-2 text-left font-medium">Top severity</th>
            <th class="px-6 pb-3 pt-2 text-right font-medium">Risk</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="row in rows"
            :key="row.file"
            class="border-t border-border/70 transition-colors hover:bg-accent/10"
          >
            <td class="px-6 py-3 text-foreground">
              <span class="block max-w-[520px] truncate">{{ row.file }}</span>
              <span class="mt-1 block text-xs text-muted-foreground">{{ row.defects }} signals</span>
            </td>
            <td class="px-6 py-3">
              <SeverityBadge :severity="row.topSeverity" />
            </td>
            <td class="px-6 py-3 text-right">
              <span class="font-semibold text-foreground">{{ Math.round(row.score) }}</span>
            </td>
          </tr>
          <tr v-if="rows.length === 0">
            <td colspan="3" class="px-6 py-6 text-sm text-muted-foreground">No data</td>
          </tr>
        </tbody>
      </table>
    </div>
  </InsightPanel>
</template>

