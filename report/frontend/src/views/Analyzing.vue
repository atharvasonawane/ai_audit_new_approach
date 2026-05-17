<template>
  <div class="flex flex-col items-center justify-center min-h-screen h-full px-6 bg-gray-50 dark:bg-gray-950">
    <!-- Header -->
    <div class="text-center mb-12">
      <h1 class="text-3xl font-bold text-gray-900 dark:text-gray-50 mb-2">
        Analyzing Project
      </h1>
      <p class="text-gray-500 dark:text-gray-400 text-base font-mono">
        {{ projectPath || '/path/to/project' }}
      </p>
      <p class="text-gray-400 dark:text-gray-500 text-sm mt-2">
        Elapsed time: {{ elapsedTime }}s
      </p>
    </div>

    <!-- Pipeline Progress Visual -->
    <div class="w-full max-w-[1000px] mb-12">
      <div class="grid grid-cols-2 md:grid-cols-4 gap-6">
        <!-- Phase 1: Scout -->
        <div class="bg-white dark:bg-gray-900 border rounded-xl p-6 flex flex-col items-center gap-3 transition-all duration-300 shadow-sm dark:shadow-none"
             :class="{
               'bg-emerald-50 dark:bg-emerald-500/10 border-emerald-500 dark:border-emerald-500/50 shadow-[0_0_12px_rgba(16,185,129,0.2)]': currentPhase > 0,
               'bg-amber-50 dark:bg-amber-500/10 border-amber-500 dark:border-amber-500/50 shadow-[0_0_12px_rgba(245,158,11,0.2)]': currentPhase === 0,
               'bg-gray-50 dark:bg-gray-900 border-gray-200 dark:border-gray-800': currentPhase < 0
             }">
          <div class="text-[14px] font-semibold text-gray-900 dark:text-gray-100 tracking-[0.05em] uppercase font-mono">SCOUT</div>
          <div class="my-2">
            <CheckCircle2 
              v-if="currentPhase > 0"
              :size="32" 
              :stroke-width="2" 
              class="text-emerald-500"
            />
            <Loader2 
              v-else-if="currentPhase === 0"
              :size="32" 
              :stroke-width="2" 
              class="animate-spin text-amber-500"
            />
            <Circle 
              v-else
              :size="32" 
              :stroke-width="2" 
              class="text-gray-300 dark:text-gray-600"
            />
          </div>
          <div class="text-[12px] font-medium text-gray-500 dark:text-gray-400">{{ getPhaseStatus(0) }}</div>
        </div>

        <!-- Phase 2: ESLint -->
        <div class="bg-white dark:bg-gray-900 border rounded-xl p-6 flex flex-col items-center gap-3 transition-all duration-300 shadow-sm dark:shadow-none"
             :class="{
               'bg-emerald-50 dark:bg-emerald-500/10 border-emerald-500 dark:border-emerald-500/50 shadow-[0_0_12px_rgba(16,185,129,0.2)]': currentPhase > 1,
               'bg-amber-50 dark:bg-amber-500/10 border-amber-500 dark:border-amber-500/50 shadow-[0_0_12px_rgba(245,158,11,0.2)]': currentPhase === 1,
               'bg-gray-50 dark:bg-gray-900 border-gray-200 dark:border-gray-800': currentPhase < 1
             }">
          <div class="text-[14px] font-semibold text-gray-900 dark:text-gray-100 tracking-[0.05em] uppercase font-mono">ESLINT</div>
          <div class="my-2">
            <CheckCircle2 
              v-if="currentPhase > 1"
              :size="32" 
              :stroke-width="2" 
              class="text-emerald-500"
            />
            <Loader2 
              v-else-if="currentPhase === 1"
              :size="32" 
              :stroke-width="2" 
              class="animate-spin text-amber-500"
            />
            <Circle 
              v-else
              :size="32" 
              :stroke-width="2" 
              class="text-gray-300 dark:text-gray-600"
            />
          </div>
          <div class="text-[12px] font-medium text-gray-500 dark:text-gray-400">{{ getPhaseStatus(1) }}</div>
        </div>

        <!-- Phase 3: AI Analysis -->
        <div class="bg-white dark:bg-gray-900 border rounded-xl p-6 flex flex-col items-center gap-3 transition-all duration-300 shadow-sm dark:shadow-none"
             :class="{
               'bg-emerald-50 dark:bg-emerald-500/10 border-emerald-500 dark:border-emerald-500/50 shadow-[0_0_12px_rgba(16,185,129,0.2)]': currentPhase > 2,
               'bg-amber-50 dark:bg-amber-500/10 border-amber-500 dark:border-amber-500/50 shadow-[0_0_12px_rgba(245,158,11,0.2)]': currentPhase === 2,
               'bg-gray-50 dark:bg-gray-900 border-gray-200 dark:border-gray-800': currentPhase < 2
             }">
          <div class="text-[14px] font-semibold text-gray-900 dark:text-gray-100 tracking-[0.05em] uppercase font-mono">AI ANALYSIS</div>
          <div class="my-2">
            <CheckCircle2 
              v-if="currentPhase > 2"
              :size="32" 
              :stroke-width="2" 
              class="text-emerald-500"
            />
            <Loader2 
              v-else-if="currentPhase === 2"
              :size="32" 
              :stroke-width="2" 
              class="animate-spin text-amber-500"
            />
            <Circle 
              v-else
              :size="32" 
              :stroke-width="2" 
              class="text-gray-300 dark:text-gray-600"
            />
          </div>
          <div class="text-[12px] font-medium text-gray-500 dark:text-gray-400">{{ getPhaseStatus(2) }}</div>
        </div>

        <!-- Phase 4: Synthesis -->
        <div class="bg-white dark:bg-gray-900 border rounded-xl p-6 flex flex-col items-center gap-3 transition-all duration-300 shadow-sm dark:shadow-none"
             :class="{
               'bg-emerald-50 dark:bg-emerald-500/10 border-emerald-500 dark:border-emerald-500/50 shadow-[0_0_12px_rgba(16,185,129,0.2)]': currentPhase > 3,
               'bg-amber-50 dark:bg-amber-500/10 border-amber-500 dark:border-amber-500/50 shadow-[0_0_12px_rgba(245,158,11,0.2)]': currentPhase === 3,
               'bg-gray-50 dark:bg-gray-900 border-gray-200 dark:border-gray-800': currentPhase < 3
             }">
          <div class="text-[14px] font-semibold text-gray-900 dark:text-gray-100 tracking-[0.05em] uppercase font-mono">SYNTHESIS</div>
          <div class="my-2">
            <CheckCircle2 
              v-if="currentPhase > 3"
              :size="32" 
              :stroke-width="2" 
              class="text-emerald-500"
            />
            <Loader2 
              v-else-if="currentPhase === 3"
              :size="32" 
              :stroke-width="2" 
              class="animate-spin text-amber-500"
            />
            <Circle 
              v-else
              :size="32" 
              :stroke-width="2" 
              class="text-gray-300 dark:text-gray-600"
            />
          </div>
          <div class="text-[12px] font-medium text-gray-500 dark:text-gray-400">{{ getPhaseStatus(3) }}</div>
        </div>
      </div>
    </div>

    <!-- Progress Details Panel -->
    <div class="w-full max-w-[800px] bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 shadow-sm dark:shadow-none rounded-xl p-6 mb-8">
      <div class="flex justify-between items-center mb-3">
        <div class="text-[14px] text-gray-500 dark:text-gray-400 font-medium">
          Phase: {{ currentPhaseName }} ({{ currentPhase + 1 }} of 4)
        </div>
        <div class="text-[14px] text-gray-900 dark:text-gray-100 font-semibold font-mono">
          {{ progressPercentage }}% complete
        </div>
      </div>

      <!-- Progress Bar -->
      <div class="w-full h-2 bg-gray-100 dark:bg-gray-800 rounded-full overflow-hidden mb-4">
        <div 
          class="h-full bg-gradient-to-r from-blue-500 to-indigo-500 transition-all duration-500 ease-out rounded-full"
          :style="{ width: progressPercentage + '%' }"
        ></div>
      </div>

      <!-- Current File Info -->
      <div class="flex items-center gap-2 p-3 bg-gray-50 dark:bg-gray-800/50 rounded-lg mb-5">
        <FileCode2 :size="16" :stroke-width="2" class="text-blue-500" />
        <span class="text-gray-600 dark:text-gray-400 text-sm font-mono">
          {{ currentFile }}
        </span>
      </div>

      <!-- Recent Findings -->
      <div class="mt-5">
        <div class="text-[14px] font-semibold text-gray-900 dark:text-gray-100 mb-3">Recent Findings:</div>
        <div class="flex flex-col gap-2">
          <div
            v-for="(finding, index) in recentFindings"
            :key="index"
            class="flex items-center gap-3 py-2 px-3 bg-gray-50 dark:bg-gray-800/50 rounded-lg border-l-[3px] border-gray-200 dark:border-gray-700"
          >
            <div 
              class="inline-flex items-center justify-center min-w-[60px] py-1 px-2 rounded-full text-[11px] font-semibold uppercase shrink-0 text-white"
              :class="{
                'bg-red-500': finding.severity === 'HIGH',
                'bg-amber-500': finding.severity === 'MEDIUM',
                'bg-emerald-500': finding.severity === 'LOW' || (finding.severity !== 'HIGH' && finding.severity !== 'MEDIUM')
              }"
            >
              {{ finding.severity }}
            </div>
            <div class="flex-1 text-[14px] text-gray-500 dark:text-gray-400">
              <span class="font-mono font-medium text-blue-500 dark:text-blue-400 mr-2">{{ finding.file }}:</span>
              <span class="text-gray-900 dark:text-gray-100">{{ finding.message }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Action Buttons -->
    <div class="flex gap-3">
      <button class="inline-flex items-center gap-2 py-2.5 px-5 bg-transparent border border-red-500 text-red-500 rounded-lg text-[14px] font-medium cursor-pointer transition-all duration-200 hover:bg-red-500/10 hover:border-red-600" @click="cancelAnalysis">
        <XCircle :size="16" :stroke-width="2" />
        <span>Cancel Analysis</span>
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { 
  CheckCircle2, 
  Loader2, 
  Circle,
  FileCode2,
  XCircle
} from 'lucide-vue-next'

const router = useRouter()
const route = useRoute()

// State
const currentPhase = ref(0)
const progressPercentage = ref(0)
const elapsedTime = ref(0)
const projectPath = ref(route.query.path || '')
const currentFile = ref('Initializing...')

const recentFindings = ref([
  { file: 'UserModal.vue', severity: 'HIGH', message: 'Prop validation missing' },
  { file: 'UserForm.vue', severity: 'MEDIUM', message: 'Unhandled promise' },
  { file: 'API.js', severity: 'LOW', message: 'Deprecated API endpoint' },
])

let progressInterval = null
let elapsedInterval = null

// Computed
const currentPhaseName = computed(() => {
  const phases = ['Scout', 'ESLint', 'AI Analysis', 'Synthesis']
  return phases[currentPhase.value] || 'Complete'
})

// Methods
const getPhaseStatus = (phaseIndex) => {
  if (currentPhase.value > phaseIndex) {
    return 'DONE'
  } else if (currentPhase.value === phaseIndex) {
    return 'IN PROGRESS'
  } else {
    return 'PENDING'
  }
}

const simulateProgress = () => {
  // Simulate 4 phases over ~8 seconds (2 seconds per phase)
  const phaseFiles = [
    ['App.vue', 'main.js', 'router/index.js'],
    ['components/Button.vue', 'components/Modal.vue'],
    ['views/Dashboard.vue', 'views/Home.vue'],
    ['Generating executive summary...']
  ]

  let fileIndex = 0
  
  progressInterval = setInterval(() => {
    // Update progress
    progressPercentage.value += 2
    
    // Update current file
    if (currentPhase.value < 4) {
      const files = phaseFiles[currentPhase.value]
      currentFile.value = files[fileIndex % files.length]
      fileIndex++
    }
    
    // Move to next phase every 25% (2 seconds)
    if (progressPercentage.value >= (currentPhase.value + 1) * 25 && currentPhase.value < 3) {
      currentPhase.value++
      fileIndex = 0
    }
    
    // Complete at 100%
    if (progressPercentage.value >= 100) {
      clearInterval(progressInterval)
      currentPhase.value = 4
      currentFile.value = 'Analysis complete!'
      
      // Navigate to dashboard after 1 second
      setTimeout(() => {
        router.push('/dashboard')
      }, 1000)
    }
  }, 100) // Update every 100ms for smooth animation
}

const startElapsedTimer = () => {
  elapsedInterval = setInterval(() => {
    elapsedTime.value++
  }, 1000)
}

const cancelAnalysis = () => {
  if (confirm('Are you sure you want to cancel the analysis?')) {
    clearInterval(progressInterval)
    clearInterval(elapsedInterval)
    router.push('/')
  }
}

// Lifecycle
onMounted(() => {
  simulateProgress()
  startElapsedTimer()
})

onUnmounted(() => {
  if (progressInterval) clearInterval(progressInterval)
  if (elapsedInterval) clearInterval(elapsedInterval)
})
</script>
