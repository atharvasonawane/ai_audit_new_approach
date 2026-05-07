<script setup lang="ts">
import BaseCard from '../ui/BaseCard.vue'
import type { TrendPoint } from '../../features/dashboard/types'

defineProps<{
  points: TrendPoint[]
}>()
</script>

<template>
  <BaseCard>
    <div class="mb-3 flex items-center justify-between">
      <h2 class="text-sm font-medium">Health Trend</h2>
      <span class="text-xs text-zinc-500">Last 5 scans</span>
    </div>
    <div class="space-y-2">
      <div
        v-for="point in points"
        :key="point.date"
        class="flex items-center justify-between rounded-lg border border-zinc-100 px-3 py-2"
      >
        <span class="text-sm text-zinc-600">{{ point.date }}</span>
        <span class="text-sm font-medium">{{ point.score }}</span>
      </div>
    </div>
  </BaseCard>
</template>
