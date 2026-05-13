<template>
  <div class="flex flex-col h-full">
    <!-- Page Header -->
    <div class="mb-8">
      <h1 class="text-4xl font-display font-bold text-text-primary mb-2">
        Code Audit Librarian
      </h1>
      <p class="text-text-secondary text-base">
        Vue.js Codebase Analysis Tool
      </p>
    </div>

    <!-- Main Content Grid -->
    <div class="flex-1 grid grid-cols-1 md:grid-cols-5 gap-8">
      <!-- Left Column: Recent Audits (40%) -->
      <div class="md:col-span-2">
        <div class="recent-audits-panel">
          <h2 class="panel-title">Recent Audits</h2>
          
          <!-- Loading State -->
          <div v-if="loading" class="flex items-center justify-center py-12">
            <Loader2 
              :size="32" 
              :stroke-width="2" 
              class="animate-spin text-accent-primary"
            />
          </div>

          <!-- Empty State -->
          <div v-else-if="recentAudits.length === 0" class="empty-state">
            <FolderOpen 
              :size="48" 
              :stroke-width="1.5" 
              class="text-text-tertiary mx-auto mb-3"
            />
            <p class="text-text-secondary text-sm">
              No audits yet. Get started by analyzing a project!
            </p>
          </div>

          <!-- Audit Cards -->
          <div v-else class="space-y-3">
            <div
              v-for="(audit, index) in recentAudits"
              :key="index"
              class="audit-card"
              @click="navigateToDashboard"
            >
              <div class="audit-timestamp">
                {{ formatDate(audit.started_at) }}
              </div>
              <div class="audit-project-name">
                {{ audit.project_name || 'Code Audit' }}
              </div>
              <div class="audit-metadata">
                <div class="metadata-badge">
                  <FileCode2 :size="14" :stroke-width="2" />
                  <span>{{ audit.total_files || 0 }} files</span>
                </div>
                <div class="metadata-badge">
                  <AlertCircle :size="14" :stroke-width="2" />
                  <span>{{ audit.total_issues || 0 }} issues</span>
                </div>
              </div>
              <div class="audit-status">
                <CheckCircle2 
                  v-if="audit.status === 'completed'"
                  :size="16" 
                  :stroke-width="2" 
                  class="text-status-success"
                />
                <Loader2 
                  v-else-if="audit.status === 'in_progress'"
                  :size="16" 
                  :stroke-width="2" 
                  class="animate-spin text-status-warning"
                />
                <XCircle 
                  v-else
                  :size="16" 
                  :stroke-width="2" 
                  class="text-status-error"
                />
                <span>{{ getStatusText(audit.status) }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Right Column: Quick Start (60%) -->
      <div class="md:col-span-3">
        <div class="quick-start-panel">
          <h2 class="panel-title">Quick Start</h2>
          
          <div class="quick-start-content">
            <label class="input-label">
              Project Directory Path
            </label>
            <input
              v-model="projectPath"
              type="text"
              placeholder="/path/to/vue-project"
              class="path-input"
              @keydown.enter="startAnalysis"
            />
            
            <div v-if="pathError" class="error-message">
              <AlertCircle :size="14" :stroke-width="2" />
              <span>{{ pathError }}</span>
            </div>

            <div class="button-group">
              <button
                class="browse-button"
                @click="showBrowseHint"
              >
                <FolderOpen :size="16" :stroke-width="2" />
                <span>Browse...</span>
              </button>
              
              <button
                class="analyze-button"
                :class="{ disabled: !projectPath }"
                :disabled="!projectPath"
                @click="startAnalysis"
              >
                <span>Analyze Now</span>
                <ArrowRight :size="16" :stroke-width="2" />
              </button>
            </div>

            <div class="drop-zone-hint">
              <Upload :size="20" :stroke-width="1.5" class="text-text-tertiary" />
              <p class="text-text-tertiary text-sm">
                or drag a folder here (coming soon)
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { 
  Loader2, 
  FolderOpen, 
  FileCode2, 
  AlertCircle,
  CheckCircle2,
  XCircle,
  ArrowRight,
  Upload
} from 'lucide-vue-next'

const router = useRouter()

// State
const loading = ref(false)
const recentAudits = ref([])
const projectPath = ref('')
const pathError = ref('')

// Mock recent audits (since /api/audit_runs might not be ready)
const mockRecentAudits = [
  {
    project_name: 'MyProject v1.0',
    started_at: '2024-01-15T14:32:00',
    status: 'completed',
    total_files: 42,
    total_issues: 128
  },
  {
    project_name: 'WebApp v2.1',
    started_at: '2024-01-10T09:15:00',
    status: 'completed',
    total_files: 156,
    total_issues: 342
  }
]

// Methods
const fetchRecentAudits = async () => {
  loading.value = true
  
  try {
    // TODO: Replace with actual API call when endpoint is ready
    // const response = await filesAPI.getAuditRuns()
    // recentAudits.value = response.data || []
    
    // For now, use mock data
    await new Promise(resolve => setTimeout(resolve, 500))
    recentAudits.value = mockRecentAudits
  } catch (err) {
    console.error('Error fetching recent audits:', err)
    recentAudits.value = []
  } finally {
    loading.value = false
  }
}

const formatDate = (dateString) => {
  if (!dateString) return 'Unknown date'
  const date = new Date(dateString)
  return date.toLocaleDateString('en-US', { 
    year: 'numeric', 
    month: 'short', 
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

const getStatusText = (status) => {
  switch (status) {
    case 'completed': return 'Completed'
    case 'in_progress': return 'In Progress'
    case 'failed': return 'Failed'
    default: return 'Unknown'
  }
}

const navigateToDashboard = () => {
  router.push('/dashboard')
}

const showBrowseHint = () => {
  alert('File browser integration coming soon! For now, please type the path manually.')
}

const startAnalysis = () => {
  pathError.value = ''
  
  if (!projectPath.value) {
    pathError.value = 'Please enter a project directory path'
    return
  }
  
  // Navigate to analyzing view
  router.push({ 
    path: '/analyzing', 
    query: { path: projectPath.value } 
  })
}

// Lifecycle
onMounted(() => {
  fetchRecentAudits()
})
</script>

<style scoped>
/* Recent Audits Panel */
.recent-audits-panel {
  background-color: var(--color-bg-secondary);
  border: 1px solid var(--color-border);
  border-radius: var(--rounded-lg);
  padding: 24px;
  height: 100%;
}

.panel-title {
  font-size: var(--text-lg);
  font-weight: 600;
  color: var(--color-text-primary);
  margin-bottom: 20px;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 48px 24px;
  text-align: center;
}

/* Audit Card */
.audit-card {
  background-color: var(--color-bg-tertiary);
  border: 1px solid var(--color-border);
  border-radius: var(--rounded-base);
  padding: 16px;
  cursor: pointer;
  transition: all 200ms ease-out;
}

.audit-card:hover {
  background-color: var(--color-bg-hover);
  border-color: var(--color-accent-primary);
  transform: translateY(-2px);
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.audit-timestamp {
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
  font-weight: 500;
  margin-bottom: 8px;
}

.audit-project-name {
  font-size: var(--text-lg);
  font-weight: 600;
  color: var(--color-text-primary);
  margin-bottom: 12px;
}

.audit-metadata {
  display: flex;
  gap: 12px;
  margin-bottom: 12px;
}

.metadata-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  background-color: var(--color-bg-primary);
  border-radius: var(--rounded-full);
  font-size: var(--text-sm);
  font-weight: 500;
  color: var(--color-text-secondary);
}

.audit-status {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
}

/* Quick Start Panel */
.quick-start-panel {
  background-color: var(--color-bg-secondary);
  border: 1px solid var(--color-border);
  border-radius: var(--rounded-lg);
  padding: 24px;
  height: 100%;
}

.quick-start-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.input-label {
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--color-text-primary);
}

.path-input {
  width: 100%;
  padding: 12px 16px;
  background-color: var(--color-bg-primary);
  border: 1px solid var(--color-border);
  border-radius: var(--rounded-base);
  color: var(--color-text-primary);
  font-size: var(--text-sm);
  font-family: var(--font-mono);
  transition: all 200ms ease-out;
}

.path-input:focus {
  outline: none;
  border-color: var(--color-accent-primary);
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.path-input::placeholder {
  color: var(--color-text-tertiary);
}

.error-message {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  background-color: rgba(255, 94, 94, 0.1);
  border: 1px solid var(--color-severity-error);
  border-radius: var(--rounded-base);
  color: var(--color-severity-error);
  font-size: var(--text-xs);
}

.button-group {
  display: flex;
  gap: 12px;
}

.browse-button {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 12px 20px;
  background-color: transparent;
  border: 1px solid var(--color-border);
  border-radius: var(--rounded-base);
  color: var(--color-text-secondary);
  font-size: var(--text-base);
  font-weight: 500;
  cursor: pointer;
  transition: all 200ms ease-out;
}

.browse-button:hover {
  background-color: var(--color-bg-tertiary);
  border-color: var(--color-accent-primary);
  color: var(--color-text-primary);
}

.analyze-button {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 12px 24px;
  background-color: var(--color-accent-primary);
  border: none;
  border-radius: var(--rounded-base);
  color: #FFFFFF;
  font-size: var(--text-base);
  font-weight: 600;
  cursor: pointer;
  transition: all 200ms ease-out;
  flex: 1;
  justify-content: center;
}

.analyze-button:hover:not(.disabled) {
  background-color: var(--color-accent-hover);
}

.analyze-button.disabled {
  background-color: var(--color-bg-hover);
  color: var(--color-text-tertiary);
  cursor: not-allowed;
  opacity: 0.5;
}

.drop-zone-hint {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 32px;
  border: 2px dashed var(--color-border);
  border-radius: var(--rounded-base);
  margin-top: 16px;
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
