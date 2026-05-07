<script setup lang="ts">
import { computed } from 'vue'

import BaseCard from '../../../components/ui/BaseCard.vue'
import type { KpiMetric, TrendPoint } from '../types'

const props = defineProps<{
  kpis: KpiMetric[]
  trends: TrendPoint[]
}>()

const healthScore = computed(() => {
  const raw = props.kpis.find((k) => k.label === 'Health Score')?.value ?? '0'
  const n = Number(raw)
  return Number.isFinite(n) ? n : 0
})

const delta = computed(() => {
  const raw = props.kpis.find((k) => k.label === 'Health Score')?.delta
  if (!raw) return null
  return raw
})

const latestTrend = computed(() => props.trends[props.trends.length - 1]?.score ?? 0)
const previousTrend = computed(
  () => props.trends[Math.max(props.trends.length - 2, 0)]?.score ?? 0,
)
const computedTrendDelta = computed(() => {
  const d = latestTrend.value - previousTrend.value
  if (!Number.isFinite(d)) return null
  return d === 0 ? null : `+${d}`
})
</script>

<template>
  <BaseCard>
    <div class="flex items-start justify-between gap-4 p-6 transition-colors hover:bg-accent/10">
      <div>
        <p class="text-xs font-medium uppercase tracking-wide text-muted-foreground">
          Health score
        </p>
        <h2 class="mt-2 text-3xl font-semibold tracking-tight text-foreground">
          {{ healthScore }}
        </h2>
        <p class="mt-1 text-sm text-muted-foreground">
          {{ delta ?? computedTrendDelta ?? 'Up to date' }}
          <span v-if="computedTrendDelta" class="text-muted-foreground">vs last scan</span>
        </p>
      </div>

      <div class="min-w-[140px] rounded-xl border border-border/70 bg-card px-4 py-3">
        <p class="text-xs font-medium uppercase tracking-wide text-muted-foreground">Trend</p>
        <div class="mt-3 flex gap-1.5">
          <div
            v-for="(t, idx) in trends.slice(-7)"
            :key="idx"
            :class="idx === trends.slice(-7).length - 1 ? 'bg-accent' : 'bg-border/50'"
            :style="{
              height: `${Math.max(6, Math.round((t.score / 100) * 22))}px`,
            }"
          />
        </div>
      </div>
    </div>
  </BaseCard>
</template>

