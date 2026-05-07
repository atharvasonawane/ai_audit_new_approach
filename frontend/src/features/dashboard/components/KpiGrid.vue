<script setup lang="ts">
import BaseCard from '../../../components/ui/BaseCard.vue'
import type { KpiMetric } from '../types'

defineProps<{
  items: KpiMetric[]
}>()
</script>

<template>
  <section class="grid gap-4 md:grid-cols-3">
    <BaseCard v-for="item in items" :key="item.label">
      <p class="text-xs uppercase tracking-wide text-zinc-500">{{ item.label }}</p>
      <p class="mt-2 text-3xl font-semibold tracking-tight">{{ item.value }}</p>
      <p v-if="item.delta" class="mt-2 text-sm text-emerald-600">{{ item.delta }}</p>
    </BaseCard>
  </section>
</template>
