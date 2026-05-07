<script setup lang="ts">
import InsightPanel from '../../../components/dashboard/InsightPanel.vue'
import StatCard from '../../../components/dashboard/StatCard.vue'
import type { ComplexitySummary } from '../types'

defineProps<{
  summary: ComplexitySummary | null
}>()
</script>

<template>
  <InsightPanel title="Complexity Architecture" description="Computed cyclomatic weights across Vue components.">
    <div class="grid gap-4 px-6 py-6 md:grid-cols-2 bg-muted/20">
      <StatCard
        label="Components analyzed"
        :value="summary?.componentsAnalyzed ?? '—'"
        hint="Parsed Vue SFCs and scripts."
        class="bg-card shadow-sm hover:shadow-md"
      />
      <StatCard
        label="Avg complexity"
        :value="summary?.avgComplexity ?? '—'"
        hint="Average weighted complexity."
        class="bg-card shadow-sm hover:shadow-md"
      />
      <StatCard
        label="P95 complexity"
        :value="summary?.p95Complexity ?? '—'"
        hint="Tail risk for large files."
        class="bg-card shadow-sm hover:shadow-md"
      />
      <StatCard
        label="High complexity files"
        :value="summary?.highComplexityCount ?? '—'"
        hint="Needs refactor attention."
        class="bg-card border-destructive/30 shadow-sm hover:shadow-md"
      />
    </div>
  </InsightPanel>
</template>

