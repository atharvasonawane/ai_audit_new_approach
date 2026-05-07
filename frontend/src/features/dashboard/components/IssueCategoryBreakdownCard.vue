<script setup lang="ts">
import { computed } from 'vue'
import InsightPanel from '../../../components/dashboard/InsightPanel.vue'
import type { DefectPoint } from '../types'

const props = defineProps<{
  defects: DefectPoint[]
}>()

// Real-world categories map
const CATEGORY_MAP: Record<string, string> = {
  'Accessibility': 'accessibility',
  'Complexity': 'complexity',
  'UI Consistency': 'ui consistency',
  'Vue Anti-patterns': 'vue anti-patterns',
  'API Risks': 'api risks'
}

type CategoryRow = {
  label: string
  count: number
  percent: number
  trend: 'up' | 'down' | 'flat'
}

const breakdown = computed<CategoryRow[]>(() => {
  const counts: Record<string, number> = {
    'Accessibility': 0,
    'Complexity': 0,
    'API Risks': 0,
    'Vue Anti-patterns': 0,
    'UI Consistency': 0,
  }
  
  let total = 0
  for (const d of props.defects) {
    if (counts[d.category] !== undefined) {
      counts[d.category] += d.count
    } else {
      // Catch-all or auto-fill for mock mapping if necessary
      counts[d.category] = (counts[d.category] || 0) + d.count
    }
    total += d.count
  }
  
  if (total === 0) return []
  
  return Object.entries(counts)
    .filter(([_, count]) => count > 0 || true) // keep all 5 keys visible for scaffolding
    .map(([key, count]) => ({
      label: key,
      count,
      percent: total > 0 ? Math.round((count / total) * 100) : 0,
      trend: count > 10 ? 'up' : count === 0 ? 'flat' : 'down' // Mock trend logic
    }))
    .sort((a, b) => b.count - a.count)
})
</script>

<template>
  <InsightPanel title="Issue Categories" description="Defect breakdown by architectural domain." class="h-full">
    <div class="px-6 py-4 h-full flex flex-col justify-center space-y-4">
      <div 
        v-for="item in breakdown" 
        :key="item.label"
        class="group flex items-center justify-between gap-4 p-3 rounded-md transition-colors hover:bg-accent/40"
      >
        <div class="flex items-center gap-3 w-1/3">
          <div class="h-8 w-8 rounded bg-background border border-border flex items-center justify-center shrink-0 shadow-sm text-muted-foreground font-mono text-[10px] uppercase">
            {{ item.label.slice(0,2) }}
          </div>
          <span class="text-sm font-semibold tracking-tight">{{ item.label }}</span>
        </div>
        
        <div class="flex-1 flex items-center gap-3">
          <div class="h-1.5 w-full bg-card border border-border/50 rounded-full overflow-hidden">
            <div 
              class="h-full bg-primary/70 transition-all rounded-full"
              :style="{ width: `${item.percent}%` }"
            />
          </div>
        </div>
        
        <div class="w-1/4 flex items-center justify-end gap-4 text-right">
          <span class="text-sm font-mono font-medium text-muted-foreground">{{ item.percent }}%</span>
          <span class="text-sm font-bold text-foreground w-8">{{ item.count }}</span>
        </div>
      </div>
      
      <div v-if="breakdown.length === 0" class="py-12 text-center text-sm text-muted-foreground font-medium">
        No category data available.
      </div>
    </div>
  </InsightPanel>
</template>
