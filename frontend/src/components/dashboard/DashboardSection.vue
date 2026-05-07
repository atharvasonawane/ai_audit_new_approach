<script setup lang="ts">
import { cn } from '../../lib/utils'

defineProps<{
  title: string
  description?: string
  class?: string
}>()
</script>

<template>
  <section :class="cn('space-y-3', $props.class)">
    <header class="flex items-end justify-between gap-4">
      <div class="min-w-0">
        <h2 class="truncate text-sm font-semibold tracking-tight text-foreground">{{ title }}</h2>
        <p v-if="description" class="mt-1 text-xs text-muted-foreground">
          {{ description }}
        </p>
      </div>
      <div class="shrink-0">
        <slot name="action" />
      </div>
    </header>
    <div>
      <slot />
    </div>
  </section>
</template>

