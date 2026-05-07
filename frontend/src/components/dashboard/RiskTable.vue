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

function healthColor(score: number) {
  if (score > 80) return 'bg-destructive shadow-[0_0_8px_rgba(220,38,38,0.5)]'
  if (score > 40) return 'bg-amber-500 shadow-[0_0_8px_rgba(245,158,11,0.5)]'
  return 'bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]'
}
</script>

<template>
  <InsightPanel :title="title" :description="description" :class="cn('h-full', $props.class)">
    <div class="overflow-x-auto h-full">
      <table class="w-full border-collapse text-sm">
        <thead>
          <tr class="text-[11px] uppercase tracking-wider text-muted-foreground border-b border-border bg-card/40">
            <th class="px-6 pb-3 pt-4 text-left font-bold w-12 text-center">Health</th>
            <th class="px-4 pb-3 pt-4 text-left font-bold">File Target</th>
            <th class="px-6 pb-3 pt-4 text-left font-bold w-40">Risk Level</th>
            <th class="px-6 pb-3 pt-4 text-right font-bold w-32">Issue Count</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="row in rows"
            :key="row.file"
            class="border-b border-border bg-card transition-all duration-200 hover:bg-accent/40 group"
          >
            <td class="px-6 py-3.5 flex justify-center items-center h-full pt-5">
              <div :class="['w-2 h-2 rounded-full', healthColor(row.score)]"></div>
            </td>
            <td class="px-4 py-3.5 text-foreground">
              <div class="flex items-center gap-3">
                <span class="block max-w-[420px] truncate font-mono text-[13px] bg-background px-1.5 py-0.5 rounded-sm border border-border">{{ row.file }}</span>
              </div>
            </td>
            <td class="px-6 py-3.5">
              <SeverityBadge :severity="row.topSeverity" class="shadow-sm" />
            </td>
            <td class="px-6 py-3.5 text-right flex flex-col items-end gap-1">
              <span class="font-mono text-base font-bold text-foreground leading-none">{{ row.defects }}</span>
              <span class="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground leading-none">signals</span>
            </td>
          </tr>
          <tr v-if="rows.length === 0">
            <td colspan="4" class="px-8 py-8 text-center text-sm font-medium text-muted-foreground">No risk data available for this view.</td>
          </tr>
        </tbody>
      </table>
    </div>
  </InsightPanel>
</template>

