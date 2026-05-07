<script setup lang="ts">
import { computed } from 'vue'

import BaseCard from '../../../components/ui/BaseCard.vue'
import type { KpiMetric } from '../types'

const props = defineProps<{
  kpis: KpiMetric[]
}>()

function valueFor(label: string) {
  return props.kpis.find((k) => k.label === label)?.value ?? '0'
}

const healthScore = computed(() => Number(valueFor('Health Score')) || 0)
const openDefects = computed(() => Number(valueFor('Open Defects')) || 0)
const highRiskFiles = computed(() => Number(valueFor('High Risk Files')) || 0)
</script>

<template>
  <BaseCard>
    <div class="p-6">
      <div class="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
      <div class="max-w-[560px]">
        <p class="text-xs font-medium uppercase tracking-wide text-muted-foreground">
          Engineering intelligence
        </p>
        <h1 class="mt-2 text-2xl font-semibold tracking-tight md:text-[28px]">
          Audit health, risk signals, and actionable defects.
        </h1>
        <p class="mt-2 text-sm leading-relaxed text-muted-foreground">
          Minimal, high-signal summaries for engineers and QA leads. Prioritize the issues that move
          quality and reduce regressions.
        </p>
      </div>

      <div class="grid gap-3 md:min-w-[420px] md:grid-cols-3">
        <div class="rounded-xl border border-border/70 bg-card px-4 py-3 transition-colors hover:bg-accent/10">
          <p class="text-xs font-medium uppercase tracking-wide text-muted-foreground">Health</p>
          <p class="mt-2 text-2xl font-semibold tracking-tight text-foreground">
            {{ healthScore }}
          </p>
        </div>
        <div class="rounded-xl border border-border/70 bg-card px-4 py-3 transition-colors hover:bg-accent/10">
          <p class="text-xs font-medium uppercase tracking-wide text-muted-foreground">Open defects</p>
          <p class="mt-2 text-2xl font-semibold tracking-tight text-foreground">
            {{ openDefects }}
          </p>
        </div>
        <div class="rounded-xl border border-border/70 bg-card px-4 py-3 transition-colors hover:bg-accent/10">
          <p class="text-xs font-medium uppercase tracking-wide text-muted-foreground">High risk files</p>
          <p class="mt-2 text-2xl font-semibold tracking-tight text-foreground">
            {{ highRiskFiles }}
          </p>
        </div>
      </div>
    </div>
    </div>
  </BaseCard>
</template>

