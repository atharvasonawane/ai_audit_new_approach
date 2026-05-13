<template>
  <div class="home-page fade-in">
    <!-- Hero Header -->
    <div class="home-hero">
      <div class="hero-label">
        <span class="hero-dot"></span>
        <span>Ready to analyze</span>
      </div>
      <h1 class="hero-title">Code Audit<br><span class="hero-accent">Librarian</span></h1>
      <p class="hero-sub">Vue.js codebase analysis — ESLint, accessibility, AI insights</p>
    </div>

    <!-- Content Grid -->
    <div class="home-grid">
      <!-- Recent Audits -->
      <div class="panel">
        <div class="panel-header">
          <span class="panel-title">Recent Audits</span>
          <span class="panel-count">{{ recentAudits.length }}</span>
        </div>

        <div v-if="loading" class="panel-loading">
          <div class="skeleton" style="height:80px;margin-bottom:10px;"></div>
          <div class="skeleton" style="height:80px;"></div>
        </div>

        <div v-else-if="recentAudits.length === 0" class="panel-empty">
          <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1" opacity="0.3">
            <path d="M3 7V5a2 2 0 012-2h2M3 17v2a2 2 0 002 2h2M17 3h2a2 2 0 012 2v2M17 21h2a2 2 0 002-2v-2"/>
            <rect x="7" y="7" width="10" height="10" rx="1"/>
          </svg>
          <p>No audits yet. Start your first analysis.</p>
        </div>

        <div v-else class="audit-list">
          <div
            v-for="(audit, i) in recentAudits"
            :key="i"
            class="audit-card"
            @click="navigateToDashboard"
          >
            <div class="audit-top">
              <span class="audit-name">{{ audit.project_name || 'Code Audit' }}</span>
              <span class="audit-status-badge" :class="audit.status">
                <span class="status-dot"></span>
                {{ getStatusText(audit.status) }}
              </span>
            </div>
            <div class="audit-meta">
              <span class="audit-time">{{ formatDate(audit.started_at) }}</span>
            </div>
            <div class="audit-stats">
              <div class="audit-stat">
                <svg width="12" height="12" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M4 2h5l4 4v8a1 1 0 01-1 1H4a1 1 0 01-1-1V3a1 1 0 011-1z"/>
                  <path d="M9 2v4h4"/>
                </svg>
                <span>{{ audit.total_files || 0 }} files</span>
              </div>
              <div class="audit-stat">
                <svg width="12" height="12" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2">
                  <circle cx="8" cy="8" r="6"/>
                  <path d="M8 5v3l2 1.5"/>
                </svg>
                <span>{{ audit.total_issues || 0 }} issues</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Quick Start -->
      <div class="panel panel-wide">
        <div class="panel-header">
          <span class="panel-title">Quick Start</span>
        </div>

        <div class="quickstart-content">
          <label class="field-label">Project Directory Path</label>
          <div class="input-wrapper">
            <svg class="input-icon" width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5">
              <path d="M1 4a1 1 0 011-1h4l2 2h6a1 1 0 011 1v7a1 1 0 01-1 1H2a1 1 0 01-1-1V4z"/>
            </svg>
            <input
              v-model="projectPath"
              type="text"
              placeholder="/path/to/your/vue-project"
              class="path-input"
              @keydown.enter="startAnalysis"
            />
          </div>

          <div v-if="pathError" class="error-bar">
            <svg width="13" height="13" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="8" cy="8" r="6"/><path d="M8 5v3M8 11h.01"/>
            </svg>
            {{ pathError }}
          </div>

          <div class="btn-row">
            <button class="btn-secondary" @click="showBrowseHint">
              <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5">
                <path d="M1 4a1 1 0 011-1h4l2 2h6a1 1 0 011 1v7a1 1 0 01-1 1H2a1 1 0 01-1-1V4z"/>
              </svg>
              Browse
            </button>
            <button
              class="btn-primary"
              :class="{ 'btn-disabled': !projectPath }"
              :disabled="!projectPath"
              @click="startAnalysis"
            >
              <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="8" cy="8" r="6"/><path d="M6 5l5 3-5 3V5z"/>
              </svg>
              Analyze Now
            </button>
          </div>

          <div class="drop-zone">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" opacity="0.3">
              <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M17 8l-5-5-5 5M12 3v12"/>
            </svg>
            <span>Drag a folder here <span class="drop-soon">— coming soon</span></span>
          </div>

          <!-- Tip cards -->
          <div class="tips-row">
            <div class="tip-card">
              <div class="tip-icon tip-blue">AI</div>
              <div>
                <p class="tip-label">AI Analysis</p>
                <p class="tip-desc">Deep code intelligence</p>
              </div>
            </div>
            <div class="tip-card">
              <div class="tip-icon tip-green">ES</div>
              <div>
                <p class="tip-label">ESLint Scan</p>
                <p class="tip-desc">Standards enforcement</p>
              </div>
            </div>
            <div class="tip-card">
              <div class="tip-icon tip-amber">A11</div>
              <div>
                <p class="tip-label">Accessibility</p>
                <p class="tip-desc">WCAG compliance</p>
              </div>
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

const router = useRouter()
const loading = ref(false)
const recentAudits = ref([])
const projectPath = ref('')
const pathError = ref('')

const mockRecentAudits = [
  { project_name: 'MyProject v1.0', started_at: '2024-01-15T14:32:00', status: 'completed', total_files: 42, total_issues: 128 },
  { project_name: 'WebApp v2.1', started_at: '2024-01-10T09:15:00', status: 'completed', total_files: 156, total_issues: 342 },
]

const fetchRecentAudits = async () => {
  loading.value = true
  try {
    await new Promise(r => setTimeout(r, 400))
    recentAudits.value = mockRecentAudits
  } catch (err) {
    recentAudits.value = []
  } finally {
    loading.value = false
  }
}

const formatDate = (d) => {
  if (!d) return ''
  return new Date(d).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric', hour: '2-digit', minute: '2-digit' })
}

const getStatusText = (s) => ({ completed: 'Completed', in_progress: 'Running', failed: 'Failed' }[s] || 'Unknown')
const navigateToDashboard = () => router.push('/dashboard')
const showBrowseHint = () => alert('File browser integration coming soon! Please type the path manually.')
const startAnalysis = () => {
  pathError.value = ''
  if (!projectPath.value) { pathError.value = 'Please enter a project directory path'; return }
  router.push({ path: '/analyzing', query: { path: projectPath.value } })
}

onMounted(fetchRecentAudits)
</script>

<style scoped>
.home-page {
  padding: 28px 32px;
  max-width: 1100px;
  margin: 0 auto;
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 28px;
}

.home-hero {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.hero-label {
  display: flex;
  align-items: center;
  gap: 7px;
  font-size: 12px;
  color: var(--color-text-tertiary);
  font-weight: 500;
  letter-spacing: 0.04em;
}

.hero-dot {
  width: 6px; height: 6px;
  border-radius: 50%;
  background: var(--color-status-success);
  box-shadow: 0 0 6px var(--color-status-success);
}

.hero-title {
  font-size: 42px;
  font-weight: 800;
  letter-spacing: -0.04em;
  line-height: 1.1;
  color: var(--color-text-primary);
}

.hero-accent {
  background: linear-gradient(135deg, #388BFD, #8957E5);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.hero-sub {
  font-size: 14px;
  color: var(--color-text-secondary);
  font-weight: 400;
}

/* Grid */
.home-grid {
  display: grid;
  grid-template-columns: 340px 1fr;
  gap: 16px;
  flex: 1;
  min-height: 0;
}

/* Panel */
.panel {
  background: var(--color-bg-secondary);
  border: 1px solid var(--color-border);
  border-radius: var(--rounded-lg);
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 18px;
  border-bottom: 1px solid var(--color-border);
}

.panel-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-primary);
  letter-spacing: -0.01em;
}

.panel-count {
  font-family: var(--font-mono);
  font-size: 11px;
  padding: 2px 7px;
  background: var(--color-bg-tertiary);
  border: 1px solid var(--color-border-emphasis);
  border-radius: var(--rounded-full);
  color: var(--color-text-secondary);
}

.panel-loading {
  padding: 14px;
}

.panel-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 48px 24px;
  color: var(--color-text-tertiary);
  font-size: 13px;
  text-align: center;
  flex: 1;
}

/* Audit Cards */
.audit-list {
  padding: 8px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.audit-card {
  padding: 12px 14px;
  background: var(--color-bg-tertiary);
  border: 1px solid var(--color-border);
  border-radius: var(--rounded-base);
  cursor: pointer;
  transition: all 150ms ease;
}

.audit-card:hover {
  background: var(--color-bg-hover);
  border-color: rgba(56, 139, 253, 0.35);
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(0,0,0,0.3);
}

.audit-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
}

.audit-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text-primary);
  letter-spacing: -0.01em;
}

.audit-status-badge {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 11px;
  font-weight: 500;
  padding: 2px 8px;
  border-radius: var(--rounded-full);
}
.audit-status-badge.completed { color: var(--color-status-success); background: rgba(63,185,80,0.1); }
.audit-status-badge.in_progress { color: var(--color-status-warning); background: rgba(210,153,34,0.1); }
.audit-status-badge.failed { color: var(--color-status-error); background: rgba(248,81,73,0.1); }

.status-dot {
  width: 5px; height: 5px;
  border-radius: 50%;
  background: currentColor;
}

.audit-meta {
  margin-bottom: 10px;
}

.audit-time {
  font-size: 11px;
  color: var(--color-text-tertiary);
  font-family: var(--font-mono);
}

.audit-stats {
  display: flex;
  gap: 14px;
}

.audit-stat {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 12px;
  color: var(--color-text-secondary);
}

/* Quick Start */
.quickstart-content {
  padding: 18px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.field-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--color-text-secondary);
  letter-spacing: 0.02em;
  text-transform: uppercase;
}

.input-wrapper {
  position: relative;
}

.input-icon {
  position: absolute;
  left: 12px;
  top: 50%;
  transform: translateY(-50%);
  color: var(--color-text-tertiary);
  pointer-events: none;
}

.path-input {
  width: 100%;
  padding: 10px 14px 10px 34px;
  background: var(--color-bg-primary);
  border: 1px solid var(--color-border-emphasis);
  border-radius: var(--rounded-base);
  color: var(--color-text-primary);
  font-size: 13px;
  font-family: var(--font-mono);
  transition: all 150ms;
  outline: none;
}

.path-input:focus {
  border-color: var(--color-accent-primary);
  box-shadow: 0 0 0 3px rgba(56,139,253,0.15);
}

.path-input::placeholder { color: var(--color-text-tertiary); }

.error-bar {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  background: rgba(248,81,73,0.08);
  border: 1px solid rgba(248,81,73,0.3);
  border-radius: var(--rounded-base);
  color: var(--color-status-error);
  font-size: 12px;
}

.btn-row {
  display: flex;
  gap: 10px;
}

.btn-primary, .btn-secondary {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 9px 16px;
  border-radius: var(--rounded-base);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 150ms;
  border: 1px solid transparent;
}

.btn-primary {
  background: var(--color-accent-primary);
  color: white;
  flex: 1;
  justify-content: center;
}
.btn-primary:hover:not(.btn-disabled) {
  background: var(--color-accent-hover);
  box-shadow: 0 0 20px rgba(56,139,253,0.3);
}
.btn-primary.btn-disabled {
  background: var(--color-bg-elevated);
  color: var(--color-text-tertiary);
  cursor: not-allowed;
  opacity: 0.6;
}

.btn-secondary {
  background: var(--color-bg-tertiary);
  border-color: var(--color-border-emphasis);
  color: var(--color-text-secondary);
}
.btn-secondary:hover {
  background: var(--color-bg-hover);
  color: var(--color-text-primary);
  border-color: rgba(56,139,253,0.3);
}

.drop-zone {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 24px;
  border: 1px dashed var(--color-border-emphasis);
  border-radius: var(--rounded-lg);
  color: var(--color-text-tertiary);
  font-size: 12px;
}

.drop-soon { color: var(--color-text-tertiary); opacity: 0.5; }

.tips-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
  margin-top: 4px;
}

.tip-card {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  background: var(--color-bg-tertiary);
  border: 1px solid var(--color-border);
  border-radius: var(--rounded-base);
}

.tip-icon {
  width: 30px;
  height: 30px;
  border-radius: var(--rounded-sm);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 9px;
  font-weight: 700;
  font-family: var(--font-mono);
  flex-shrink: 0;
}

.tip-blue  { background: rgba(56,139,253,0.15); color: #58A6FF; }
.tip-green { background: rgba(63,185,80,0.15);  color: #3FB950; }
.tip-amber { background: rgba(210,153,34,0.15); color: #D29922; }

.tip-label {
  font-size: 11px;
  font-weight: 600;
  color: var(--color-text-primary);
  margin-bottom: 1px;
}

.tip-desc {
  font-size: 10px;
  color: var(--color-text-tertiary);
}
</style>
