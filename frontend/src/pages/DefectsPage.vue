<script setup lang="ts">
import { computed } from 'vue'
import { mockA11yDefects, mockDefectSummaries } from '../features/defects/mock'
import DefectsTable from '../features/defects/components/DefectsTable.vue'
import BaseCard from '../components/ui/BaseCard.vue'

// Quick aggregations for metrics
const totalDefects = computed(() => mockA11yDefects.length)
const criticalCount = computed(() => mockA11yDefects.filter(d => d.severity === 'critical').length)
const highCount = computed(() => mockA11yDefects.filter(d => d.severity === 'high').length)
const affectedFilesCount = computed(() => new Set(mockA11yDefects.map(d => d.file_path)).size)

</script>

<template>
  <div class="h-full flex flex-col gap-6">
    <header class="flex flex-col gap-1 shrink-0">
      <h1 class="text-2xl font-bold tracking-tight text-foreground">Accessibility Dashboard</h1>
      <p class="text-sm text-muted-foreground">Audit results for WCAG compliance and UI accessibility standards.</p>
    </header>

    <!-- Top Summary Metrics -->
    <div class="grid grid-cols-2 md:grid-cols-4 gap-4 shrink-0">
      <BaseCard class="p-5 flex flex-col gap-1 items-start justify-center relative overflow-hidden">
        <div class="text-xs font-semibold text-muted-foreground uppercase tracking-widest z-10">Total Findings</div>
        <div class="text-3xl font-mono tracking-tight font-bold z-10">{{ totalDefects }}</div>
      </BaseCard>
      
      <BaseCard class="p-5 flex flex-col gap-1 items-start justify-center relative overflow-hidden">
        <div class="text-xs font-semibold text-destructive uppercase tracking-widest z-10">Critical Priority</div>
        <div class="text-3xl font-mono tracking-tight font-bold text-destructive z-10">{{ criticalCount }}</div>
        <div class="absolute -right-4 -bottom-4 w-24 h-24 bg-destructive/10 rounded-full blur-2xl"></div>
      </BaseCard>
      
      <BaseCard class="p-5 flex flex-col gap-1 items-start justify-center relative overflow-hidden">
        <div class="text-xs font-semibold text-amber-500 uppercase tracking-widest z-10">High Priority</div>
        <div class="text-3xl font-mono tracking-tight font-bold text-amber-500 z-10">{{ highCount }}</div>
        <div class="absolute -right-4 -bottom-4 w-24 h-24 bg-amber-500/10 rounded-full blur-2xl"></div>
      </BaseCard>

      <BaseCard class="p-5 flex flex-col gap-1 items-start justify-center relative overflow-hidden">
        <div class="text-xs font-semibold text-muted-foreground uppercase tracking-widest z-10">Affected Files</div>
        <div class="text-3xl font-mono tracking-tight font-bold z-10">{{ affectedFilesCount }}</div>
      </BaseCard>
    </div>

    <!-- Main 2-column layout -->
    <div class="flex-1 min-h-0 grid grid-cols-1 lg:grid-cols-3 gap-6">
      
      <!-- Pattern Summaries (Left Column) -->
      <div class="flex flex-col gap-4 overflow-hidden h-full">
        <h3 class="text-sm font-semibold uppercase tracking-wider text-muted-foreground shrink-0">Repeated Patterns</h3>
        
        <div class="flex-1 overflow-y-auto space-y-3 pr-2">
          <BaseCard 
            v-for="summary in mockDefectSummaries" 
            :key="summary.rule_name"
            class="p-4 hover:border-muted-foreground/30 transition-colors"
          >
            <div class="flex items-start justify-between gap-2 mb-2">
              <span class="inline-block px-1.5 py-0.5 rounded border border-border bg-background text-[10px] font-mono text-muted-foreground max-w-[80%] truncate" :title="summary.rule_name">
                {{ summary.rule_name }}
              </span>
              <span class="font-mono text-sm font-bold" :class="{
                'text-destructive': summary.severity === 'critical',
                'text-amber-500': summary.severity === 'high',
                'text-foreground': summary.severity === 'medium',
              }">{{ summary.count }}x</span>
            </div>
            <p class="text-xs text-foreground/80 leading-relaxed">{{ summary.description }}</p>
          </BaseCard>
        </div>
      </div>

      <!-- Detail Table (Right 2 Columns) -->
      <div class="lg:col-span-2 h-full overflow-hidden">
        <DefectsTable :defects="mockA11yDefects" />
      </div>
      
    </div>
  </div>
</template>
