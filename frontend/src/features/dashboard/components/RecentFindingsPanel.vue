<script setup lang="ts">
import { computed } from 'vue'

import InsightPanel from '../../../components/dashboard/InsightPanel.vue'
import SeverityBadge from '../../../components/dashboard/SeverityBadge.vue'
import type { DefectPoint, Severity } from '../types'
import { useRecentFindings } from '../composables/useRecentFindings'

const props = defineProps<{
  defects: DefectPoint[]
  limit?: number
}>()

const limit = computed(() => props.limit ?? 5)
const { recent } = useRecentFindings(computed(() => props.defects), limit.value)

function severityPill(severity: Severity) {
  return severity
}

function shortDate(foundAt?: string) {
  if (!foundAt) return '—'
  const ms = Date.parse(foundAt)
  if (!Number.isFinite(ms)) return '—'
  return new Date(ms).toISOString().slice(0, 10)
}
</script>

<template>
  <InsightPanel title="Recent findings" description="Latest defect signals from the last audit run.">
    <template #meta>
      <p class="text-xs text-muted-foreground">{{ recent.length }} items</p>
    </template>
    <div class="px-6 pb-2">
      <div class="divide-y divide-border/70">
        <div
          v-for="item in recent"
          :key="item.id"
          class="flex items-start justify-between gap-4 py-5 transition-all duration-200 hover:bg-accent/40 -mx-3 px-3 rounded-md"
        >
          <div class="min-w-0">
            <div class="flex items-center gap-3">
              <SeverityBadge :severity="severityPill(item.severity)" class="shadow-sm" />
              <p class="truncate text-sm font-semibold tracking-tight">{{ item.category }}</p>
            </div>
            <p class="mt-1.5 truncate text-xs text-muted-foreground font-mono bg-card px-1.5 py-0.5 rounded-sm border border-border inline-block">{{ item.file }}</p>
            <p class="mt-2 text-xs font-medium text-muted-foreground">
              <span class="text-foreground font-semibold">{{ item.count }}</span> signals detected
            </p>
          </div>
          <div class="shrink-0 text-xs font-mono text-muted-foreground font-medium pt-1">{{ shortDate(item.foundAt) }}</div>
        </div>
        <div v-if="recent.length === 0" class="py-6 text-sm text-muted-foreground">No data</div>
      </div>
    </div>
  </InsightPanel>
</template>

