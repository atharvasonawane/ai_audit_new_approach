<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getMockFileDetail } from '../features/files/mock/fileDetails.mock'
import MetricWidget from '../features/files/components/MetricWidget.vue'
import FindingsList from '../features/files/components/FindingsList.vue'

const route = useRoute()
const router = useRouter()

const fileId = computed(() => route.params.id as string)
const fileDetails = computed(() => getMockFileDetail(fileId.value))

function goBack() {
  router.push('/files')
}

const healthStatus = computed(() => {
  if (!fileDetails.value) return 'neutral'
  const score = fileDetails.value.health_score
  if (score < 50) return 'critical'
  if (score < 80) return 'warning'
  return 'good'
})

const depthStatus = computed(() => {
  if (!fileDetails.value) return 'neutral'
  return fileDetails.value.max_nesting_depth > 5 ? 'warning' : 'good'
})

const complexityStatus = computed(() => {
  if (!fileDetails.value) return 'neutral'
  return fileDetails.value.flag_count > 4 ? 'critical' : (fileDetails.value.flag_count > 0 ? 'warning' : 'good')
})

const a11yStatus = computed(() => {
  if (!fileDetails.value) return 'neutral'
  return fileDetails.value.accessibility_defects > 0 ? 'critical' : 'good'
})
</script>

<template>
  <div v-if="!fileDetails" class="h-full flex items-center justify-center">
    <div class="text-muted-foreground font-mono">File not found.</div>
  </div>

  <div v-else class="h-full flex flex-col gap-6 overflow-hidden">
    <!-- Header -->
    <header class="shrink-0 space-y-4">
      <button @click="goBack" class="text-xs font-mono text-muted-foreground hover:text-foreground inline-flex items-center gap-2 transition-colors">
        <svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m15 18-6-6 6-6"/></svg>
        BACK TO FILE EXPLORER
      </button>
      
      <div class="flex items-start justify-between">
        <div>
          <h1 class="text-xl font-mono tracking-tight text-foreground truncate max-w-2xl bg-card border border-border px-3 py-1.5 rounded-md shadow-sm">
            {{ fileDetails.file_path }}
          </h1>
          <div class="mt-3 flex items-center gap-2">
            <span v-for="tag in fileDetails.tags" :key="tag" class="text-[10px] uppercase tracking-wider font-semibold px-2 py-0.5 bg-accent text-muted-foreground rounded-full border border-border">
              {{ tag }}
            </span>
            <span class="text-[10px] text-muted-foreground ml-2 font-mono">Analyzed: {{ new Date(fileDetails.last_analyzed).toLocaleString() }}</span>
          </div>
        </div>
        
        <div class="flex flex-col items-end gap-1">
          <div class="text-xs uppercase tracking-widest text-muted-foreground font-bold">Health Score</div>
          <div class="text-4xl font-black font-mono tracking-tighter" :class="healthStatus === 'critical' ? 'text-destructive drop-shadow-[0_0_12px_rgba(220,38,38,0.4)]' : healthStatus === 'warning' ? 'text-amber-500' : 'text-emerald-500'">
            {{ fileDetails.health_score }}<span class="text-xl text-muted-foreground">/100</span>
          </div>
        </div>
      </div>
    </header>

    <!-- Metrics Grid -->
    <div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4 shrink-0">
      <MetricWidget 
        label="Lines of Code" 
        :value="fileDetails.script_lines + fileDetails.template_lines"
        sublabel="Total" 
      />
      <MetricWidget 
        label="Methods" 
        :value="fileDetails.methods" 
        sublabel="Count"
      />
      <MetricWidget 
        label="API Integrations" 
        :value="fileDetails.api_total" 
        sublabel="Calls"
        :status="fileDetails.api_total > 5 ? 'warning' : 'neutral'"
      />
      <MetricWidget 
        label="Dom Payload" 
        :value="fileDetails.payload_size_kb" 
        sublabel="KB"
        :status="fileDetails.payload_size_kb > 20 ? 'warning' : 'neutral'"
      />
      <MetricWidget 
        label="Max Nesting" 
        :value="fileDetails.max_nesting_depth" 
        sublabel="Levels"
        :status="depthStatus"
      />
      <MetricWidget 
        label="A11y Defects" 
        :value="fileDetails.accessibility_defects" 
        sublabel="Issues"
        :status="a11yStatus"
      />
    </div>

    <!-- Main Content Area -->
    <main class="flex-1 min-h-0 grid grid-cols-1 lg:grid-cols-3 gap-6">
      
      <!-- Issue Breakdown Summary (Left Col) -->
      <div class="flex flex-col gap-6 overflow-y-auto pr-2">
        <div class="bg-card border border-border rounded-xl p-5 shadow-sm relative overflow-hidden">
          <div class="absolute right-0 top-0 w-1 h-full" :class="complexityStatus === 'critical' ? 'bg-destructive' : 'bg-transparent'"></div>
          <h3 class="text-sm font-semibold uppercase tracking-wider text-muted-foreground mb-4">Complexity Flags</h3>
          <div class="flex items-baseline gap-2">
            <span class="text-4xl font-black tracking-tight" :class="complexityStatus === 'critical' ? 'text-destructive' : (complexityStatus === 'warning' ? 'text-amber-500' : 'text-foreground')">{{ fileDetails.flag_count }}</span>
            <span class="text-xs text-muted-foreground uppercase tracking-widest font-mono">Active</span>
          </div>
          <p class="text-xs text-muted-foreground mt-3 leading-relaxed">
            Measures structural risk including God components, deeply nested callbacks, and bloated parameter lists.
          </p>
        </div>

        <div class="bg-card border border-border rounded-xl p-5 shadow-sm">
          <h3 class="text-sm font-semibold uppercase tracking-wider text-muted-foreground mb-4">Confidence Score</h3>
          <div class="flex items-center justify-between mb-2">
            <span class="text-2xl font-mono">{{ Math.round(fileDetails.confidence * 100) }}%</span>
          </div>
          <div class="h-2 w-full bg-background rounded-full overflow-hidden border border-border">
            <div class="h-full bg-primary" :style="{ width: `${fileDetails.confidence * 100}%` }"></div>
          </div>
          <p class="text-[11px] text-muted-foreground mt-3 font-mono">
            Pipeline extraction precision rating based on AST parsing success.
          </p>
        </div>
      </div>

      <!-- Line Level Findings (Right Cols) -->
      <div class="lg:col-span-2 h-full">
        <FindingsList :findings="fileDetails.findings" />
      </div>
      
    </main>
  </div>
</template>
