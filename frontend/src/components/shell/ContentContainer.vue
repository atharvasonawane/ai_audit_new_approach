<script setup lang="ts">
import { cn } from '../../lib/utils'

defineProps<{
  class?: string
}>()
</script>

<template>
  <div :class="cn('mx-auto w-full max-w-[1200px] px-5 py-6 md:px-8', $props.class)">
    <slot />
  </div>
</template>

