<script setup lang="ts">
import { computed, ref } from 'vue'
import type { A11yDefect } from '../types'
import { cn } from '../../../lib/utils'
import InsightPanel from '../../../components/dashboard/InsightPanel.vue'
import SeverityBadge from '../../../components/dashboard/SeverityBadge.vue'

const props = defineProps<{
  defects: A11yDefect[]
}>()

const sortCol = ref<keyof A11yDefect | null>('severity')
const sortDesc = ref(true)
const searchQuery = ref('')

const sortedAndFiltered = computed(() => {
  let data = [...props.defects]
  
  if (searchQuery.value) {
    const q = searchQuery.value.toLowerCase()
    data = data.filter(d => 
      d.file_path.toLowerCase().includes(q) || 
      d.rule_name.toLowerCase().includes(q) ||
      d.message.toLowerCase().includes(q)
    )
  }
  
  if (sortCol.value) {
    const severityWeights = { critical: 4, high: 3, medium: 2, low: 1 }
    data.sort((a, b) => {
      let valA: any = a[sortCol.value as keyof A11yDefect]
      let valB: any = b[sortCol.value as keyof A11yDefect]
      
      if (sortCol.value === 'severity') {
        valA = severityWeights[a.severity]
        valB = severityWeights[b.severity]
      }
      
      if (valA < valB) return sortDesc.value ? 1 : -1
      if (valA > valB) return sortDesc.value ? -1 : 1
      return 0
    })
  }

  return data
})

function setSort(col: keyof A11yDefect) {
  if (sortCol.value === col) {
    sortDesc.value = !sortDesc.value
  } else {
    sortCol.value = col
    sortDesc.value = col === 'severity'
  }
}
</script>

<template>
  <div class="flex flex-col gap-4 h-full">
    <!-- Search Controls -->
    <div class="flex items-center justify-between">
      <div class="relative w-96">
        <svg xmlns="http://www.w3.org/2000/svg" class="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>
        <input 
          v-model="searchQuery" 
          type="text" 
          placeholder="Filter by file, rule, or message..." 
          class="w-full bg-card border border-border rounded-md pl-10 pr-4 py-2 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
        />
      </div>
      <div class="text-xs text-muted-foreground font-mono">
        {{ sortedAndFiltered.length }} DEFECT(S) MATCHING
      </div>
    </div>

    <InsightPanel title="Defect Inventory" description="Comprehensive list of accessibility line-level findings" class="flex-1 overflow-hidden flex flex-col">
      <div class="flex-1 overflow-auto bg-card">
        <table class="w-full border-collapse text-left">
          <thead class="sticky top-0 z-10 bg-card/95 backdrop-blur-xs border-b border-border shadow-sm">
            <tr class="text-[11px] uppercase tracking-wider text-muted-foreground">
              <th class="px-5 py-3 font-bold cursor-pointer hover:text-foreground w-28" @click="setSort('severity')">Severity <span v-if="sortCol === 'severity'">{{ sortDesc ? '↓' : '↑' }}</span></th>
              <th class="px-5 py-3 font-bold cursor-pointer hover:text-foreground w-64" @click="setSort('rule_name')">Rule Category <span v-if="sortCol === 'rule_name'">{{ sortDesc ? '↓' : '↑' }}</span></th>
              <th class="px-5 py-3 font-bold cursor-pointer hover:text-foreground" @click="setSort('file_path')">File Location <span v-if="sortCol === 'file_path'">{{ sortDesc ? '↓' : '↑' }}</span></th>
            </tr>
          </thead>
          <tbody class="divide-y divide-border">
            <template v-for="defect in sortedAndFiltered" :key="defect.id">
              <!-- Primary Row -->
              <tr class="hover:bg-accent/30 transition-colors group">
                <td class="px-5 py-4 align-top pt-5">
                  <SeverityBadge :severity="defect.severity" />
                </td>
                <td class="px-5 py-4 align-top">
                  <span class="inline-block px-1.5 py-0.5 rounded border border-border bg-background text-[11px] font-mono text-muted-foreground">
                    {{ defect.rule_name }}
                  </span>
                </td>
                <td class="px-5 py-4">
                  <div class="flex flex-col gap-2">
                    <div class="flex items-center gap-3">
                      <span class="font-mono text-[13px] text-foreground">{{ defect.file_path }}</span>
                      <span class="text-xs font-mono text-muted-foreground">Line {{ defect.line }}</span>
                    </div>
                    <p class="text-sm text-foreground/80 leading-relaxed">
                      {{ defect.message }}
                    </p>
                    <div v-if="defect.snippet" class="mt-1 bg-black/40 border border-border/60 rounded p-2 overflow-x-auto">
                      <code class="text-[11px] font-mono text-muted-foreground whitespace-pre">{{ defect.snippet }}</code>
                    </div>
                  </div>
                </td>
              </tr>
            </template>
            <tr v-if="sortedAndFiltered.length === 0">
              <td colspan="3" class="p-8 text-center text-sm font-medium text-muted-foreground">
                No defects match your criteria.
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </InsightPanel>
  </div>
</template>
