<script setup lang="ts">
import { computed } from 'vue'
import { defineProps } from 'vue'
import BaseCard from '../../../components/ui/BaseCard.vue'

const props = defineProps<{
  label: string
  value: number | string
  sublabel?: string
  trend?: 'up' | 'down' | 'neutral'
  status?: 'good' | 'warning' | 'critical' | 'neutral'
}>()

const statusColor = computed(() => {
  switch (props.status) {
    case 'good': return 'text-emerald-500'
    case 'warning': return 'text-amber-500'
    case 'critical': return 'text-destructive'
    default: return 'text-foreground'
  }
})
</script>

<template>
  <BaseCard class="p-5 flex flex-col gap-2 items-start justify-center overflow-hidden relative">
    <div class="text-xs font-semibold text-muted-foreground uppercase tracking-widest z-10">{{ label }}</div>
    <div class="flex items-baseline gap-2 z-10">
      <span class="text-3xl font-mono tracking-tight font-bold" :class="statusColor">{{ value }}</span>
      <span v-if="sublabel" class="text-xs text-muted-foreground font-mono uppercase">{{ sublabel }}</span>
    </div>
    
    <!-- Optional decorative background element based on status -->
    <div v-if="status === 'critical'" class="absolute -right-4 -bottom-4 w-24 h-24 bg-destructive/5 rounded-full blur-2xl"></div>
    <div v-if="status === 'warning'" class="absolute -right-4 -bottom-4 w-24 h-24 bg-amber-500/5 rounded-full blur-2xl"></div>
  </BaseCard>
</template>
