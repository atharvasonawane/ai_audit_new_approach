<template>
  <div class="h-full flex flex-col bg-bg-primary">
    <!-- Loading State -->
    <div v-if="loading" class="flex items-center justify-center h-full">
      <div class="text-center">
        <Loader2 
          :size="48" 
          :stroke-width="2" 
          class="animate-spin text-accent-primary mx-auto mb-4"
        />
        <p class="text-text-secondary text-base">Loading file details...</p>
      </div>
    </div>

    <!-- Error State -->
    <div v-else-if="error" class="flex items-center justify-center h-full p-6">
      <div class="bg-bg-secondary border border-severity-error rounded-lg p-8 text-center max-w-md">
        <AlertCircle 
          :size="48" 
          :stroke-width="2" 
          class="text-severity-error mx-auto mb-4"
        />
        <p class="text-text-primary font-semibold mb-2">Failed to load file details</p>
        <p class="text-text-secondary text-sm mb-4">{{ error }}</p>
        <button
          @click="fetchFileData"
          class="retry-button"
        >
          <RefreshCw :size="16" :stroke-width="2" />
          <span>Retry</span>
        </button>
      </div>
    </div>

    <!-- File Detail Content -->
    <div v-else class="flex flex-col h-full overflow-hidden">
      <!-- Header -->
      <div class="border-b border-border px-6 py-4">
        <div class="flex items-center justify-between">
          <div>
            <h2 class="text-text-primary font-semibold text-lg font-mono">
              {{ fileName }}
            </h2>
            <p class="text-text-tertiary text-xs font-mono mt-1">
              {{ filePath }}
            </p>
          </div>
        </div>
      </div>

      <!-- Metrics Grid -->
      <div class="px-6 py-6 border-b border-border">
        <div class="metrics-grid">
          <div class="metric-item">
            <span class="metric-label">METHODS</span>
            <span class="metric-value">{{ metrics.methods || 0 }}</span>
          </div>
          <div class="metric-item">
            <span class="metric-label">SCRIPT LINES</span>
            <span class="metric-value">{{ metrics.script_lines || 0 }}</span>
          </div>
          <div class="metric-item">
            <span class="metric-label">COMPLEXITY</span>
            <span class="metric-value">{{ metrics.cyclomatic_complexity || 0 }}</span>
          </div>
          <div class="metric-item">
            <span class="metric-label">API CALLS</span>
            <span class="metric-value">{{ metrics.api_total || 0 }}</span>
          </div>
          <div class="metric-item">
            <span class="metric-label">AI ISSUES</span>
            <span class="metric-value">{{ aiIssues.length }}</span>
          </div>
          <div class="metric-item">
            <span class="metric-label">ESLINT FLAGS</span>
            <span class="metric-value">{{ eslintFlags.length }}</span>
          </div>
        </div>
      </div>

      <!-- Tab Bar -->
      <div class="sticky top-0 z-10 bg-bg-primary border-b border-border">
        <div class="flex px-6">
          <button
            v-for="tab in tabs"
            :key="tab.id"
            @click="activeTab = tab.id"
            class="tab-button"
            :class="{ active: activeTab === tab.id }"
          >
            {{ tab.label }} ({{ getTabCount(tab.id) }})
          </button>
        </div>
      </div>

      <!-- Tab Content -->
      <div class="flex-1 overflow-y-auto px-6 py-6">
        <!-- AI Issues Tab -->
        <div v-if="activeTab === 'ai'" class="space-y-4">
          <div v-if="aiIssues.length === 0" class="empty-state">
            <CheckCircle2 :size="48" :stroke-width="1.5" class="text-status-success mx-auto mb-3" />
            <p class="text-text-secondary">No AI issues found</p>
          </div>
          <div v-else v-for="(issue, index) in aiIssues" :key="index" class="issue-card">
            <div class="flex items-start justify-between mb-3">
              <h3 class="text-text-primary font-semibold text-base flex-1">
                {{ issue.issue_title || 'Untitled Issue' }}
              </h3>
              <span 
                class="severity-badge"
                :class="getSeverityClass(issue.severity)"
              >
                {{ issue.severity || 'Low' }}
              </span>
            </div>
            <p class="text-text-secondary text-sm mb-3 leading-relaxed">
              {{ issue.description }}
            </p>
            <div class="flex items-center gap-4 text-xs text-text-tertiary mb-3">
              <span class="flex items-center gap-1">
                <Hash :size="12" />
                Line {{ issue.line_number || 'N/A' }}
              </span>
            </div>
            <CodeSnippet 
              v-if="issue.code_snippet" 
              :code="issue.code_snippet"
              :targetLine="issue.line_number"
            />
          </div>
        </div>

        <!-- ESLint Tab -->
        <div v-if="activeTab === 'eslint'" class="space-y-4">
          <div v-if="eslintFlags.length === 0" class="empty-state">
            <CheckCircle2 :size="48" :stroke-width="1.5" class="text-status-success mx-auto mb-3" />
            <p class="text-text-secondary">No ESLint flags found</p>
          </div>
          <div v-else v-for="(flag, index) in eslintFlags" :key="index" class="issue-card">
            <div class="flex items-start justify-between mb-3">
              <h3 class="text-text-primary font-semibold text-base flex-1 font-mono text-sm">
                {{ flag.rule || 'Unknown Rule' }}
              </h3>
              <span 
                class="severity-badge"
                :class="getSeverityClass(flag.severity)"
              >
                {{ flag.severity || 'Low' }}
              </span>
            </div>
            <p class="text-text-secondary text-sm mb-3 leading-relaxed">
              {{ flag.message }}
            </p>
            <div class="flex items-center gap-4 text-xs text-text-tertiary mb-3">
              <span class="flex items-center gap-1">
                <Hash :size="12" />
                Line {{ flag.line_number || 'N/A' }}
              </span>
            </div>
            <CodeSnippet 
              v-if="flag.code_snippet" 
              :code="flag.code_snippet"
              :targetLine="flag.line_number"
            />
          </div>
        </div>

        <!-- Accessibility Tab -->
        <div v-if="activeTab === 'accessibility'" class="space-y-4">
          <div v-if="accessibilityDefects.length === 0" class="empty-state">
            <CheckCircle2 :size="48" :stroke-width="1.5" class="text-status-success mx-auto mb-3" />
            <p class="text-text-secondary">No accessibility defects found</p>
          </div>
          <div v-else v-for="(defect, index) in accessibilityDefects" :key="index" class="issue-card">
            <div class="flex items-start justify-between mb-3">
              <h3 class="text-text-primary font-semibold text-base flex-1 font-mono text-sm">
                {{ defect.rule || 'Unknown Rule' }}
              </h3>
              <span class="severity-badge badge-medium">
                A11y
              </span>
            </div>
            <p class="text-text-secondary text-sm mb-3 leading-relaxed">
              {{ defect.message }}
            </p>
            <div v-if="defect.wcag_criterion" class="bg-bg-tertiary rounded px-3 py-2 mb-3">
              <p class="text-xs text-text-secondary">
                <span class="font-semibold text-text-primary">WCAG {{ defect.wcag_level }}:</span> 
                {{ defect.wcag_criterion }}
              </p>
              <p class="text-xs text-text-tertiary mt-1">
                {{ defect.wcag_explanation }}
              </p>
            </div>
            <div class="flex items-center gap-4 text-xs text-text-tertiary mb-3">
              <span class="flex items-center gap-1">
                <Hash :size="12" />
                Line {{ defect.line_number || 'N/A' }}
              </span>
            </div>
            <CodeSnippet 
              v-if="defect.code_snippet" 
              :code="defect.code_snippet"
              :targetLine="defect.line_number"
            />
          </div>
        </div>

        <!-- API Calls Tab -->
        <div v-if="activeTab === 'api'" class="space-y-4">
          <div v-if="apiCalls.length === 0" class="empty-state">
            <Info :size="48" :stroke-width="1.5" class="text-text-tertiary mx-auto mb-3" />
            <p class="text-text-secondary">No API calls found</p>
          </div>
          <div v-else v-for="(call, index) in apiCalls" :key="index" class="issue-card">
            <div class="flex items-start justify-between mb-3">
              <h3 class="text-text-primary font-semibold text-base flex-1 font-mono text-sm">
                {{ call.method }} {{ call.endpoint }}
              </h3>
              <span 
                v-if="call.in_loop"
                class="severity-badge badge-high"
              >
                IN LOOP
              </span>
            </div>
            <div class="flex items-center gap-4 text-xs text-text-tertiary mb-3">
              <span class="flex items-center gap-1">
                <Hash :size="12" />
                Line {{ call.line_number || 'N/A' }}
              </span>
            </div>
            <CodeSnippet 
              v-if="call.code_snippet" 
              :code="call.code_snippet"
              :targetLine="call.line_number"
            />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, computed } from 'vue'
import { 
  Loader2, 
  AlertCircle, 
  RefreshCw, 
  CheckCircle2,
  Hash,
  Info
} from 'lucide-vue-next'
import { filesAPI } from '../api.js'
import CodeSnippet from './CodeSnippet.vue'

const props = defineProps({
  filePath: {
    type: String,
    required: true
  }
})

// State
const loading = ref(false)
const error = ref(null)
const metrics = ref({})
const aiIssues = ref([])
const eslintFlags = ref([])
const accessibilityDefects = ref([])
const apiCalls = ref([])
const activeTab = ref('ai')

// Computed
const fileName = computed(() => {
  if (!props.filePath) return ''
  const parts = props.filePath.split('/')
  return parts[parts.length - 1]
})

const tabs = [
  { id: 'ai', label: 'AI Issues' },
  { id: 'eslint', label: 'ESLint' },
  { id: 'accessibility', label: 'Accessibility' },
  { id: 'api', label: 'API Calls' }
]

// Methods
const getTabCount = (tabId) => {
  switch (tabId) {
    case 'ai': return aiIssues.value.length
    case 'eslint': return eslintFlags.value.length
    case 'accessibility': return accessibilityDefects.value.length
    case 'api': return apiCalls.value.length
    default: return 0
  }
}

const getSeverityClass = (severity) => {
  const sev = (severity || 'Low').toLowerCase()
  if (sev === 'high' || sev === 'error') return 'badge-high'
  if (sev === 'medium' || sev === 'warning') return 'badge-medium'
  return 'badge-low'
}

const fetchFileData = async () => {
  if (!props.filePath) return
  
  loading.value = true
  error.value = null
  
  try {
    // Fetch all data in parallel
    const [metricsRes, aiRes, eslintRes, a11yRes, apiRes] = await Promise.all([
      filesAPI.getFileMetrics(props.filePath),
      filesAPI.getFileAIIssues(props.filePath),
      filesAPI.getFileESLint(props.filePath),
      filesAPI.getFileAccessibility(props.filePath),
      filesAPI.getFileAPICalls(props.filePath)
    ])
    
    metrics.value = metricsRes.data || {}
    aiIssues.value = aiRes.data || []
    eslintFlags.value = eslintRes.data || []
    accessibilityDefects.value = a11yRes.data || []
    apiCalls.value = apiRes.data || []
    
    console.log('File data loaded:', {
      metrics: metrics.value,
      aiIssues: aiIssues.value.length,
      eslintFlags: eslintFlags.value.length,
      accessibilityDefects: accessibilityDefects.value.length,
      apiCalls: apiCalls.value.length
    })
  } catch (err) {
    console.error('Error fetching file data:', err)
    error.value = err.response?.data?.error || err.message || 'Failed to load file details'
  } finally {
    loading.value = false
  }
}

// Watch for file path changes
watch(() => props.filePath, (newPath) => {
  if (newPath) {
    fetchFileData()
  }
}, { immediate: true })
</script>

<style scoped>
.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 16px;
}

.metric-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.metric-label {
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
  font-weight: 600;
  letter-spacing: var(--tracking-wide);
  text-transform: uppercase;
}

.metric-value {
  font-size: var(--text-3xl);
  font-weight: 700;
  color: var(--color-text-primary);
  font-family: var(--font-mono);
  line-height: var(--leading-tight);
}

.tab-button {
  padding: 12px 16px;
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: all 200ms ease-out;
  border-bottom: 3px solid transparent;
  position: relative;
}

.tab-button:hover {
  color: var(--color-text-primary);
  background-color: rgba(255, 255, 255, 0.05);
}

.tab-button.active {
  color: var(--color-text-primary);
  border-bottom-color: var(--color-accent-primary);
}

.issue-card {
  background-color: var(--color-bg-secondary);
  border: 1px solid var(--color-border);
  border-radius: var(--rounded-lg);
  padding: 20px;
  transition: all 200ms ease-out;
}

.issue-card:hover {
  border-color: var(--color-accent-primary);
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.severity-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 4px 12px;
  border-radius: var(--rounded-full);
  font-size: var(--text-xs);
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: var(--tracking-wide);
  flex-shrink: 0;
}

.badge-high {
  background-color: var(--color-severity-high);
  color: #FFFFFF;
}

.badge-medium {
  background-color: var(--color-severity-medium);
  color: #FFFFFF;
}

.badge-low {
  background-color: var(--color-severity-low);
  color: #FFFFFF;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 64px 24px;
  text-align: center;
}

.retry-button {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  background-color: var(--color-accent-primary);
  color: #FFFFFF;
  border-radius: var(--rounded-base);
  font-size: var(--text-sm);
  font-weight: 600;
  cursor: pointer;
  transition: all 200ms ease-out;
}

.retry-button:hover {
  background-color: var(--color-accent-hover);
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
