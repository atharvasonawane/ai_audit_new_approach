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
  <BaseCard :class="cn('p-5 transition-colors hover:bg-accent/20', $props.class)">
    <p class="text-xs font-medium uppercase tracking-wide text-muted-foreground">{{ label }}</p>
    <div class="mt-2 flex items-baseline justify-between gap-3">
      <p class="text-2xl font-semibold tracking-tight text-foreground">{{ value }}</p>
      <p v-if="delta" class="text-xs font-medium text-muted-foreground">{{ delta }}</p>
    </div>
    <p v-if="hint" class="mt-2 text-xs text-muted-foreground">{{ hint }}</p>
    <slot />
  </BaseCard>
</template>

