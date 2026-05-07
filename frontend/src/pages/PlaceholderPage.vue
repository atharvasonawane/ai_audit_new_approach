<script setup lang="ts">
defineProps<{
  title: string
  description?: string
}>()
</script>

<template>
  <section class="space-y-2">
    <h1 class="text-xl font-semibold tracking-tight">{{ title }}</h1>
    <p class="max-w-prose text-sm text-muted-foreground">
      {{ description ?? 'This area is scaffolding for the dashboard module.' }}
    </p>
  </section>
</template>

