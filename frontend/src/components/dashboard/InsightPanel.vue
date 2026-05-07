<script setup lang="ts">
import { cn } from '../../lib/utils'
import BaseCard from '../ui/BaseCard.vue'

defineProps<{
  title: string
  description?: string
  class?: string
}>()
</script>

<template>
  <BaseCard :class="cn('p-0 overflow-hidden flex flex-col', $props.class)">
    <div class="flex items-start justify-between gap-4 p-6 bg-card/50">
      <div>
        <h3 class="text-base font-semibold tracking-tight text-foreground">{{ title }}</h3>
        <p v-if="description" class="mt-1.5 text-sm text-muted-foreground">{{ description }}</p>
      </div>
      <slot name="meta" />
    </div>
    <div class="border-t border-border flex-1 bg-card">
      <slot />
    </div>
  </BaseCard>
</template>

