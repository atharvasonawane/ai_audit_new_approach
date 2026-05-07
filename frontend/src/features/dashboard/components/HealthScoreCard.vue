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
  <BaseCard class="h-full">
    <div class="flex flex-col h-full justify-between gap-6 p-8 transition-all duration-200">
      <div>
        <p class="text-[11px] font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5 mb-2">
          <span class="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
          Overall Health Score
        </p>
        <div class="flex items-baseline gap-2 mt-4">
          <h2 class="text-[3.5rem] leading-none font-bold tracking-tighter text-foreground">
            {{ healthScore }}
          </h2>
          <span class="text-xl font-semibold text-muted-foreground">/ 100</span>
        </div>
        <p class="mt-3 text-sm font-medium text-emerald-500">
          {{ delta ?? computedTrendDelta ?? 'Stable trends' }}
          <span class="text-muted-foreground ml-1">vs last scan</span>
        </p>
      </div>

      <div class="rounded-xl border border-border bg-card/50 p-5 mt-auto shadow-sm">
        <div class="flex items-center justify-between mb-3">
          <p class="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">Historical Trend</p>
          <span class="text-xs text-muted-foreground">Last 7 scans</span>
        </div>
        <div class="mt-4 flex items-end gap-2 h-10 w-full">
          <div
            v-for="(t, idx) in trends.slice(-7)"
            :key="idx"
            class="flex-1 rounded-t-sm transition-all"
            :class="idx === trends.slice(-7).length - 1 ? 'bg-primary' : 'bg-border/60 hover:bg-border'"
            :style="{
              height: `${Math.max(10, Math.round((t.score / 100) * 100))}%`,
              opacity: idx === trends.slice(-7).length - 1 ? '1' : '0.5'
            }"
            :title="`Score: ${t.score}`"
          />
        </div>
      </div>
    </div>
  </BaseCard>
</template>

