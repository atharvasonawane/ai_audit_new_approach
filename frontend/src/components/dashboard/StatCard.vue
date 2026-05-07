<script setup lang="ts">
import { cn } from '../../lib/utils'
import BaseCard from '../ui/BaseCard.vue'

defineProps<{
  label: string
  value: string | number
  hint?: string
  delta?: string
  class?: string
}>()
</script>

<template>
  <BaseCard :class="cn('p-6 transition-all duration-200 hover:bg-accent/40 hover:border-accent-foreground/20', $props.class)">
    <p class="text-[11px] font-bold uppercase tracking-wider text-muted-foreground mb-2">{{ label }}</p>
    <div class="flex items-baseline justify-between gap-3">
      <p class="text-3xl font-bold tracking-tight text-foreground">{{ value }}</p>
      <p v-if="delta" class="text-sm font-medium text-emerald-500">{{ delta }}</p>
    </div>
    <p v-if="hint" class="mt-2 text-sm text-muted-foreground">{{ hint }}</p>
    <slot />
  </BaseCard>
</template>

