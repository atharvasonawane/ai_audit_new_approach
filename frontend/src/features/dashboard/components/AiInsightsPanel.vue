<script setup lang="ts">
import InsightPanel from '../../../components/dashboard/InsightPanel.vue'
import { Sparkles, ArrowRight, CheckCircle2, AlertTriangle } from 'lucide-vue-next'

const insights = [
  {
    id: 1,
    type: 'critical',
    title: 'High Complexity in Data Grids',
    description: 'OrdersList.vue and FindingsTable.vue account for 45% of total cyclomatic complexity. Extracting column definitions to pure TS constants could reduce block size by 30%.',
    icon: AlertTriangle,
    color: 'text-destructive',
    bg: 'bg-destructive/10 border-destructive/20'
  },
  {
    id: 2,
    type: 'warning',
    title: 'A11y Label Deficits',
    description: 'Multiple inputs lack aria-labels or associated <label> tags across the settings components. Addressing this will clear 14 high-severity accessibility flags.',
    icon: AlertTriangle,
    color: 'text-amber-500',
    bg: 'bg-amber-500/10 border-amber-500/20'
  },
  {
    id: 3,
    type: 'positive',
    title: 'API Chaining Improved',
    description: 'Network redundant calls have dropped by 12% since the last scan. The refactor of the composables layer successfully collapsed 3 MQL request chains.',
    icon: CheckCircle2,
    color: 'text-emerald-500',
    bg: 'bg-emerald-500/10 border-emerald-500/20'
  }
]
</script>

<template>
  <InsightPanel title="AI Diagnostics" description="Synthesized recommendations from code patterns.">
    <template #meta>
      <div class="px-2.5 py-1 bg-accent/40 rounded-md border border-border flex items-center gap-1.5">
        <Sparkles class="w-3.5 h-3.5 text-primary" />
        <span class="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">Auto-generated</span>
      </div>
    </template>
    
    <div class="flex flex-col h-full divide-y divide-border/50 bg-card/20">
      <div 
        v-for="insight in insights" 
        :key="insight.id"
        class="p-5 transition-colors hover:bg-accent/20 group"
      >
        <div class="flex gap-4">
          <div :class="['w-8 h-8 rounded-md flex items-center justify-center shrink-0 border shadow-sm', insight.bg]">
            <component :is="insight.icon" :class="['w-4 h-4', insight.color]" />
          </div>
          <div class="flex-1 min-w-0">
            <h4 class="text-sm font-semibold tracking-tight text-foreground">{{ insight.title }}</h4>
            <p class="mt-1.5 text-sm leading-relaxed text-muted-foreground">
              {{ insight.description }}
            </p>
            <div class="mt-3 flex items-center">
              <button class="text-[11px] font-bold uppercase tracking-wider text-primary flex items-center gap-1 opacity-80 transition-opacity hover:opacity-100">
                View trace <ArrowRight class="w-3 h-3" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </InsightPanel>
</template>
