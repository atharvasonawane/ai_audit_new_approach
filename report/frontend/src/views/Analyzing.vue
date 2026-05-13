<template>
  <div class="flex flex-col items-center justify-center h-full px-6">
    <!-- Header -->
    <div class="text-center mb-12">
      <h1 class="text-3xl font-bold text-text-primary mb-2">
        Analyzing Project
      </h1>
      <p class="text-text-secondary text-base font-mono">
        {{ projectPath || '/path/to/project' }}
      </p>
      <p class="text-text-tertiary text-sm mt-2">
        Elapsed time: {{ elapsedTime }}s
      </p>
    </div>

    <!-- Pipeline Progress Visual -->
    <div class="pipeline-container">
      <div class="pipeline-grid">
        <!-- Phase 1: Scout -->
        <div class="phase-card" :class="getPhaseClass(0)">
          <div class="phase-title">SCOUT</div>
          <div class="phase-icon">
            <CheckCircle2 
              v-if="currentPhase > 0"
              :size="32" 
              :stroke-width="2" 
              class="text-status-success"
            />
            <Loader2 
              v-else-if="currentPhase === 0"
              :size="32" 
              :stroke-width="2" 
              class="animate-spin text-status-warning"
            />
            <Circle 
              v-else
              :size="32" 
              :stroke-width="2" 
              class="text-text-tertiary"
            />
          </div>
          <div class="phase-status">{{ getPhaseStatus(0) }}</div>
        </div>

        <!-- Phase 2: ESLint -->
        <div class="phase-card" :class="getPhaseClass(1)">
          <div class="phase-title">ESLINT</div>
          <div class="phase-icon">
            <CheckCircle2 
              v-if="currentPhase > 1"
              :size="32" 
              :stroke-width="2" 
              class="text-status-success"
            />
            <Loader2 
              v-else-if="currentPhase === 1"
              :size="32" 
              :stroke-width="2" 
              class="animate-spin text-status-warning"
            />
            <Circle 
              v-else
              :size="32" 
              :stroke-width="2" 
              class="text-text-tertiary"
            />
          </div>
          <div class="phase-status">{{ getPhaseStatus(1) }}</div>
        </div>

        <!-- Phase 3: AI Analysis -->
        <div class="phase-card" :class="getPhaseClass(2)">
          <div class="phase-title">AI ANALYSIS</div>
          <div class="phase-icon">
            <CheckCircle2 
              v-if="currentPhase > 2"
              :size="32" 
              :stroke-width="2" 
              class="text-status-success"
            />
            <Loader2 
              v-else-if="currentPhase === 2"
              :size="32" 
              :stroke-width="2" 
              class="animate-spin text-status-warning"
            />
            <Circle 
              v-else
              :size="32" 
              :stroke-width="2" 
              class="text-text-tertiary"
            />
          </div>
          <div class="phase-status">{{ getPhaseStatus(2) }}</div>
        </div>

        <!-- Phase 4: Synthesis -->
        <div class="phase-card" :class="getPhaseClass(3)">
          <div class="phase-title">SYNTHESIS</div>
          <div class="phase-icon">
            <CheckCircle2 
              v-if="currentPhase > 3"
              :size="32" 
              :stroke-width="2" 
              class="text-status-success"
            />
            <Loader2 
              v-else-if="currentPhase === 3"
              :size="32" 
              :stroke-width="2" 
              class="animate-spin text-status-warning"
            />
            <Circle 
              v-else
              :size="32" 
              :stroke-width="2" 
              class="text-text-tertiary"
            />
          </div>
          <div class="phase-status">{{ getPhaseStatus(3) }}</div>
        </div>
      </div>
    </div>

    <!-- Progress Details Panel -->
    <div class="progress-details-panel">
      <div class="progress-header">
        <div class="progress-label">
          Phase: {{ currentPhaseName }} ({{ currentPhase + 1 }} of 4)
        </div>
        <div class="progress-percentage">
          {{ progressPercentage }}% complete
        </div>
      </div>

      <!-- Progress Bar -->
      <div class="progress-bar-container">
        <div 
          class="progress-bar-fill"
          :style="{ width: progressPercentage + '%' }"
        ></div>
      </div>

      <!-- Current File Info -->
      <div class="current-file-info">
        <FileCode2 :size="16" :stroke-width="2" class="text-accent-primary" />
        <span class="text-text-secondary text-sm font-mono">
          {{ currentFile }}
        </span>
      </div>

      <!-- Recent Findings -->
      <div class="recent-findings">
        <div class="findings-title">Recent Findings:</div>
        <div class="findings-list">
          <div
            v-for="(finding, index) in recentFindings"
            :key="index"
            class="finding-item"
          >
            <div 
              class="finding-severity"
              :class="getSeverityClass(finding.severity)"
            >
              {{ finding.severity }}
            </div>
            <div class="finding-text">
              <span class="finding-file">{{ finding.file }}:</span>
              <span class="finding-message">{{ finding.message }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Action Buttons -->
    <div class="action-buttons">
      <button class="cancel-button" @click="cancelAnalysis">
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
const getPhaseClass = (phaseIndex) => {
  if (currentPhase.value > phaseIndex) {
    return 'phase-completed'
  } else if (currentPhase.value === phaseIndex) {
    return 'phase-in-progress'
  } else {
    return 'phase-pending'
  }
}

const getPhaseStatus = (phaseIndex) => {
  if (currentPhase.value > phaseIndex) {
    return 'DONE'
  } else if (currentPhase.value === phaseIndex) {
    return 'IN PROGRESS'
  } else {
    return 'PENDING'
  }
}

const getSeverityClass = (severity) => {
  switch (severity) {
    case 'HIGH': return 'severity-high'
    case 'MEDIUM': return 'severity-medium'
    case 'LOW': return 'severity-low'
    default: return 'severity-low'
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

<style scoped>
/* Pipeline Container */
.pipeline-container {
  width: 100%;
  max-width: 1000px;
  margin-bottom: 48px;
}

.pipeline-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 24px;
}

@media (max-width: 768px) {
  .pipeline-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

/* Phase Card */
.phase-card {
  background-color: var(--color-bg-secondary);
  border: 2px solid var(--color-border);
  border-radius: var(--rounded-base);
  padding: 24px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  transition: all 400ms ease-out;
}

.phase-card.phase-completed {
  background-color: rgba(16, 185, 129, 0.1);
  border-color: var(--color-status-success);
  box-shadow: 0 0 12px rgba(16, 185, 129, 0.2);
}

.phase-card.phase-in-progress {
  background-color: rgba(245, 158, 11, 0.1);
  border-color: var(--color-status-warning);
  animation: pulse 2s ease-in-out infinite;
}

.phase-card.phase-pending {
  background-color: var(--color-bg-secondary);
  border-color: var(--color-border);
}

@keyframes pulse {
  0%, 100% {
    box-shadow: 0 0 0 rgba(245, 158, 11, 0);
  }
  50% {
    box-shadow: 0 0 20px rgba(245, 158, 11, 0.3);
  }
}

.phase-title {
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--color-text-primary);
  letter-spacing: var(--tracking-wide);
  text-transform: uppercase;
  font-family: var(--font-mono);
}

.phase-icon {
  margin: 8px 0;
}

.phase-status {
  font-size: var(--text-xs);
  color: var(--color-text-secondary);
  font-weight: 500;
}

/* Progress Details Panel */
.progress-details-panel {
  width: 100%;
  max-width: 800px;
  background-color: var(--color-bg-secondary);
  border: 1px solid var(--color-border);
  border-radius: var(--rounded-lg);
  padding: 24px;
  margin-bottom: 32px;
}

.progress-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.progress-label {
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
  font-weight: 500;
}

.progress-percentage {
  font-size: var(--text-sm);
  color: var(--color-text-primary);
  font-weight: 600;
  font-family: var(--font-mono);
}

/* Progress Bar */
.progress-bar-container {
  width: 100%;
  height: 8px;
  background-color: var(--color-bg-tertiary);
  border: 1px solid var(--color-border);
  border-radius: var(--rounded-full);
  overflow: hidden;
  margin-bottom: 16px;
}

.progress-bar-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--color-accent-primary), var(--color-accent-secondary));
  transition: width 500ms ease-out;
  border-radius: var(--rounded-full);
}

/* Current File Info */
.current-file-info {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px;
  background-color: var(--color-bg-primary);
  border-radius: var(--rounded-base);
  margin-bottom: 20px;
}

/* Recent Findings */
.recent-findings {
  margin-top: 20px;
}

.findings-title {
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--color-text-primary);
  margin-bottom: 12px;
}

.findings-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.finding-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 12px;
  background-color: var(--color-bg-primary);
  border-radius: var(--rounded-base);
  border-left: 3px solid var(--color-border);
}

.finding-severity {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 60px;
  padding: 4px 8px;
  border-radius: var(--rounded-full);
  font-size: var(--text-xs);
  font-weight: 600;
  text-transform: uppercase;
  flex-shrink: 0;
}

.severity-high {
  background-color: var(--color-severity-high);
  color: #FFFFFF;
}

.severity-medium {
  background-color: var(--color-severity-medium);
  color: #FFFFFF;
}

.severity-low {
  background-color: var(--color-severity-low);
  color: #FFFFFF;
}

.finding-text {
  flex: 1;
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
}

.finding-file {
  font-family: var(--font-mono);
  font-weight: 500;
  color: var(--color-accent-primary);
  margin-right: 8px;
}

.finding-message {
  color: var(--color-text-primary);
}

/* Action Buttons */
.action-buttons {
  display: flex;
  gap: 12px;
}

.cancel-button {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 10px 20px;
  background-color: transparent;
  border: 1px solid var(--color-severity-error);
  border-radius: var(--rounded-base);
  color: var(--color-severity-error);
  font-size: var(--text-sm);
  font-weight: 500;
  cursor: pointer;
  transition: all 200ms ease-out;
}

.cancel-button:hover {
  background-color: rgba(255, 94, 94, 0.1);
  border-color: var(--color-severity-high);
}

/* Loading animation */
@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

.animate-spin {
  animation: spin 1s linear infinite;
}
</style>
