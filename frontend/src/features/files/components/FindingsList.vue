<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import BaseCard from '../../../components/ui/BaseCard.vue'
import SeverityBadge from '../../../components/dashboard/SeverityBadge.vue'
import type { FileFinding } from '../types'

const props = defineProps<{
  findings: FileFinding[]
}>()

const sortedFindings = computed(() => {
  const w = { critical: 4, high: 3, medium: 2, low: 1, info: 0 }
  return [...props.findings].sort((a, b) => {
    // Sort by severity first
    const diff = w[b.severity as keyof typeof w] - w[a.severity as keyof typeof w]
    if (diff !== 0) return diff
    // Then by line number
    return (a.line || 0) - (b.line || 0)
  })
})
</script>

<template>
  <BaseCard class="flex flex-col h-full overflow-hidden">
    <div class="px-5 py-4 border-b border-border bg-card/50">
      <h3 class="text-sm font-semibold uppercase tracking-wider text-muted-foreground">Line-Level Findings</h3>
    </div>
    
    <div class="flex-1 overflow-y-auto">
      <div v-if="sortedFindings.length === 0" class="p-8 text-center text-sm text-muted-foreground font-mono">
        No findings reported for this file.
      </div>
      
      <div class="divide-y divide-border">
        <div v-for="finding in sortedFindings" :key="finding.id" class="p-5 hover:bg-accent/20 transition-colors">
          <div class="flex items-start gap-4">
            
            <div class="flex-shrink-0 pt-0.5">
              <SeverityBadge :severity="finding.severity === 'info' ? 'low' : finding.severity" />
            </div>

            <div class="flex-1 min-w-0">
              <div class="flex items-center justify-between gap-4 mb-1">
                <span class="text-[10px] font-mono uppercase tracking-wider text-muted-foreground border border-border px-1.5 py-0.5 rounded bg-background">
                  {{ finding.category }}
                </span>
                <span v-if="finding.line" class="text-xs font-mono text-muted-foreground">
                  Line {{ finding.line }}
                </span>
              </div>
              
              <p class="text-sm text-foreground leading-relaxed">
                {{ finding.message }}
              </p>
              
              <div v-if="finding.code_snippet" class="mt-3 bg-[#0d0d0d] border border-border rounded-md p-3 overflow-x-auto">
                <pre class="text-[11px] font-mono text-muted-foreground whitespace-pre"><code>{{ finding.code_snippet }}</code></pre>
              </div>
            </div>
            
          </div>
        </div>
      </div>
    </div>
  </BaseCard>
</template>
