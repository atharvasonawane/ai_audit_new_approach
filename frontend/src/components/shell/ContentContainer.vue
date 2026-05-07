<script setup lang="ts">
import { cn } from '../../lib/utils'

defineProps<{
  class?: string
}>()
</script>

<template>
  <div :class="cn('mx-auto w-full max-w-[1200px] px-6 py-8 md:px-8 md:py-10', $props.class)">
    <slot />
  </div>
</template>

