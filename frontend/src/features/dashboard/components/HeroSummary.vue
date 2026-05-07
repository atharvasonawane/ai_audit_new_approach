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
      <div class="max-w-[560px] flex flex-col justify-center">
        <p class="text-[11px] font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
          <span class="w-2 h-2 rounded-full bg-emerald-500"></span>
          Engineering intelligence platform
        </p>
        <h1 class="mt-3 text-3xl font-bold tracking-tight md:text-4xl">
          Audit health, risk signals, and actionable defects.
        </h1>
        <p class="mt-4 text-base leading-relaxed text-muted-foreground">
          Minimal, high-signal summaries for engineers and QA leads. Prioritize the issues that move
          quality and reduce regressions.
        </p>
      </div>

      <div class="grid gap-3 md:min-w-[420px] md:grid-cols-3">
        <div class="rounded-xl border border-border/70 bg-card px-5 py-4 transition-all hover:bg-accent hover:border-accent-foreground/10 duration-200">
          <p class="text-[11px] font-bold uppercase tracking-wider text-muted-foreground mb-1">Health Score</p>
          <div class="flex items-baseline gap-2">
            <p class="text-3xl font-bold tracking-tight text-foreground">
              {{ healthScore }}
            </p>
            <span class="text-sm font-medium text-emerald-500">/ 100</span>
          </div>
        </div>
        <div class="rounded-xl border border-border/70 bg-card px-5 py-4 transition-all hover:bg-accent hover:border-accent-foreground/10 duration-200">
          <p class="text-[11px] font-bold uppercase tracking-wider text-muted-foreground mb-1">Open Defects</p>
          <div class="flex items-baseline gap-2">
            <p class="text-3xl font-bold tracking-tight text-foreground">
              {{ openDefects }}
            </p>
          </div>
        </div>
        <div class="rounded-xl border border-border/70 bg-card px-5 py-4 transition-all hover:bg-accent hover:border-accent-foreground/10 duration-200">
          <p class="text-[11px] font-bold uppercase tracking-wider text-muted-foreground mb-1">High Risk Files</p>
          <div class="flex items-baseline gap-2">
            <p class="text-3xl font-bold tracking-tight text-foreground">
              {{ highRiskFiles }}
            </p>
          </div>
        </div>
      </div>
    </div>
    </div>
  </BaseCard>
</template>

