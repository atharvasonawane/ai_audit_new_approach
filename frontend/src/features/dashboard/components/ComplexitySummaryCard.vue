<script setup lang="ts">
import InsightPanel from '../../../components/dashboard/InsightPanel.vue'
import StatCard from '../../../components/dashboard/StatCard.vue'
import type { ComplexitySummary } from '../types'

defineProps<{
  summary: ComplexitySummary | null
}>()
</script>

<template>
  <InsightPanel title="Complexity summary" description="High-level complexity signals across components.">
    <div class="grid gap-3 px-6 py-4 md:grid-cols-2">
      <StatCard
        label="Components analyzed"
        :value="summary?.componentsAnalyzed ?? '—'"
        hint="Parsed Vue SFCs and scripts."
        class="p-4"
      />
      <StatCard
        label="Avg complexity"
        :value="summary?.avgComplexity ?? '—'"
        hint="Average weighted complexity."
        class="p-4"
      />
      <StatCard
        label="P95 complexity"
        :value="summary?.p95Complexity ?? '—'"
        hint="Tail risk for large files."
        class="p-4"
      />
      <StatCard
        label="High complexity files"
        :value="summary?.highComplexityCount ?? '—'"
        hint="Needs refactor attention."
        class="p-4"
      />
    </div>
  </InsightPanel>
</template>

