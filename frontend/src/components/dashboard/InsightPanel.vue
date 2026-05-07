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
  <BaseCard :class="cn('p-0 overflow-hidden', $props.class)">
    <div class="flex items-start justify-between gap-4 p-6">
      <div>
        <p class="text-sm font-medium tracking-tight text-foreground">{{ title }}</p>
        <p v-if="description" class="mt-1 text-xs text-muted-foreground">{{ description }}</p>
      </div>
      <slot name="meta" />
    </div>
    <div class="border-t border-border/70">
      <slot />
    </div>
  </BaseCard>
</template>

