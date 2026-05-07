<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import type { AuditFile } from '../types'
import { cn } from '../../../lib/utils'
import InsightPanel from '../../../components/dashboard/InsightPanel.vue'

const props = defineProps<{
  files: AuditFile[]
}>()

const router = useRouter()
const sortCol = ref<keyof AuditFile | null>('health_score')
const sortDesc = ref(false)
const searchQuery = ref('')

const filteredFiles = computed(() => {
  let data = [...props.files]
  if (searchQuery.value) {
    const q = searchQuery.value.toLowerCase()
    data = data.filter(f => f.file_path.toLowerCase().includes(q))
  }
  if (sortCol.value) {
    data.sort((a, b) => {
      const valA = a[sortCol.value as keyof AuditFile]
      const valB = b[sortCol.value as keyof AuditFile]
      if (valA < valB) return sortDesc.value ? 1 : -1
      if (valA > valB) return sortDesc.value ? -1 : 1
      return 0
    })
  }

  return data
})

function setSort(col: keyof AuditFile) {
  if (sortCol.value === col) {
    sortDesc.value = !sortDesc.value
  } else {
    sortCol.value = col
    sortDesc.value = true // default to desc for metrics
  }
}

function healthColor(score: number) {
  if (score < 50) return 'bg-destructive shadow-[0_0_8px_rgba(220,38,38,0.5)]'
  if (score < 80) return 'bg-amber-500 shadow-[0_0_8px_rgba(245,158,11,0.5)]'
  return 'bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]'
}
</script>

<template>
  <div class="flex flex-col gap-4 h-full">
    <!-- Controls -->
    <div class="flex items-center justify-between">
      <div class="relative w-80">
        <svg xmlns="http://www.w3.org/2000/svg" class="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>
        <input 
          v-model="searchQuery" 
          type="text" 
          placeholder="Filter by file path..." 
          class="w-full bg-card border border-border rounded-md pl-10 pr-4 py-2 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
        />
      </div>
      <div class="text-xs text-muted-foreground font-mono">
        {{ filteredFiles.length }} FILE(S) MATCHING
      </div>
    </div>

    <!-- Table content inside InsightPanel for consistent bordering/style -->
    <InsightPanel title="Audit Data Explorer" description="Drill down into specific file metrics" class="flex-1 overflow-hidden">
      <div class="h-full overflow-y-auto">
        <table class="w-full border-collapse text-sm text-left">
          <thead class="sticky top-0 z-10">
            <tr class="text-[11px] uppercase tracking-wider text-muted-foreground border-b border-border bg-card/90 backdrop-blur-sm">
              <th class="px-6 py-3 font-bold cursor-pointer hover:text-foreground" @click="setSort('health_score')">Health <span v-if="sortCol === 'health_score'">{{ sortDesc ? '↓' : '↑' }}</span></th>
              <th class="px-4 py-3 font-bold cursor-pointer hover:text-foreground" @click="setSort('file_path')">File Path <span v-if="sortCol === 'file_path'">{{ sortDesc ? '↓' : '↑' }}</span></th>
              <th class="px-4 py-3 font-bold cursor-pointer text-right hover:text-foreground" @click="setSort('script_lines')">Loc <span v-if="sortCol === 'script_lines'">{{ sortDesc ? '↓' : '↑' }}</span></th>
              <th class="px-4 py-3 font-bold cursor-pointer text-right hover:text-foreground" @click="setSort('api_total')">APIs <span v-if="sortCol === 'api_total'">{{ sortDesc ? '↓' : '↑' }}</span></th>
              <th class="px-4 py-3 font-bold cursor-pointer text-right hover:text-foreground" @click="setSort('max_nesting_depth')">Depth <span v-if="sortCol === 'max_nesting_depth'">{{ sortDesc ? '↓' : '↑' }}</span></th>
              <th class="px-4 py-3 font-bold cursor-pointer text-right hover:text-foreground" @click="setSort('flag_count')">Complexity <span v-if="sortCol === 'flag_count'">{{ sortDesc ? '↓' : '↑' }}</span></th>
              <th class="px-4 py-3 font-bold cursor-pointer text-right hover:text-foreground" @click="setSort('accessibility_defects')">A11y <span v-if="sortCol === 'accessibility_defects'">{{ sortDesc ? '↓' : '↑' }}</span></th>
              <th class="px-6 py-3 font-bold cursor-pointer text-right hover:text-foreground" @click="setSort('confidence')">Conf <span v-if="sortCol === 'confidence'">{{ sortDesc ? '↓' : '↑' }}</span></th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="file in filteredFiles"
              :key="file.id"
              class="border-b border-border bg-card transition-all duration-200 hover:bg-accent/40 group cursor-pointer"
              @click="router.push(`/files/${file.id}`)"
            >
              <td class="px-6 py-3">
                <div class="flex items-center gap-2">
                  <div :class="['w-2 h-2 rounded-full', healthColor(file.health_score)]"></div>
                  <span class="font-mono text-xs">{{ file.health_score }}</span>
                </div>
              </td>
              <td class="px-4 py-3 text-foreground">
                <span class="block truncate max-w-[400px] font-mono text-[13px] bg-background px-1.5 py-0.5 rounded-sm border border-border" :title="file.file_path">{{ file.file_path }}</span>
              </td>
              <td class="px-4 py-3 text-right font-mono text-[13px]">{{ file.script_lines + file.template_lines }}</td>
              <td class="px-4 py-3 text-right font-mono text-[13px] text-muted-foreground">{{ file.api_total }}</td>
              <td class="px-4 py-3 text-right font-mono text-[13px] text-muted-foreground" :class="{'text-amber-500': file.max_nesting_depth > 5}">{{ file.max_nesting_depth }}</td>
              <td class="px-4 py-3 text-right font-mono text-[13px] text-muted-foreground" :class="{'text-destructive': file.flag_count > 4}">{{ file.flag_count }}</td>
              <td class="px-4 py-3 text-right font-mono text-[13px] text-muted-foreground" :class="{'text-destructive': file.accessibility_defects > 0}">{{ file.accessibility_defects }}</td>
              <td class="px-6 py-3 text-right font-mono text-[13px] text-muted-foreground">{{ Math.round(file.confidence * 100) }}%</td>
            </tr>
            <tr v-if="filteredFiles.length === 0">
              <td colspan="8" class="px-8 py-10 text-center text-sm font-medium text-muted-foreground border-b border-border">No files found matching your criteria.</td>
            </tr>
          </tbody>
        </table>
      </div>
    </InsightPanel>
  </div>
</template>
