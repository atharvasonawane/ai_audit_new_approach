<script setup lang="ts">
import { cn } from '../../lib/utils'
import type { Severity } from '../../features/dashboard/types'

defineProps<{
  severity: Severity
  class?: string
}>()

function badgeClass(severity: Severity) {
  switch (severity) {
    case 'critical':
      return 'border-destructive/40 bg-destructive/15 text-destructive-foreground'
    case 'high':
      return 'border-accent/40 bg-accent/15 text-accent-foreground'
    case 'medium':
      return 'border-secondary/60 bg-secondary/40 text-secondary-foreground'
    case 'low':
    default:
      return 'border-border/60 bg-border/20 text-muted-foreground'
  }
}
</script>

<template>
  <span
    :class="
      cn(
        'inline-flex h-7 items-center rounded-lg border px-2 text-xs font-medium capitalize tracking-tight',
        badgeClass(severity),
        $props.class,
      )
    "
  >
    <slot>{{ severity }}</slot>
  </span>
</template>

