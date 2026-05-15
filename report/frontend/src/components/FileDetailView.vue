<template>
  <div class="file-detail">
    <!-- Loading -->
    <div v-if="loading" class="detail-loading">
      <div class="spinner"></div>
      <p>Loading file details...</p>
    </div>

    <!-- Error -->
    <div v-else-if="error" class="detail-error">
      <div class="err-ico">!</div>
      <p class="err-msg">{{ error }}</p>
      <button class="btn-sm" @click="fetchFileData">Retry</button>
    </div>

    <!-- Content -->
    <div v-else class="detail-body fade-in">
      <!-- File Header -->
      <div class="file-header">
        <div class="file-header-left">
          <div class="file-type-chip">
            <svg width="11" height="11" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5">
              <path d="M4 2h5l4 4v8a1 1 0 01-1 1H4a1 1 0 01-1-1V3a1 1 0 011-1z"/>
              <path d="M9 2v4h4"/>
            </svg>
            Vue
          </div>
          <div>
            <div class="file-title">{{ fileName }}</div>
            <div class="file-path">{{ filePath }}</div>
          </div>
        </div>
        <div class="file-header-scores">
          <div class="header-score" :class="aiIssues.length > 0 ? 'score-purple' : 'score-green'">
            <div class="hs-val">{{ aiIssues.length }}</div>
            <div class="hs-label">AI</div>
          </div>
          <div class="header-score" :class="eslintFlags.length > 0 ? 'score-teal' : 'score-green'">
            <div class="hs-val">{{ eslintFlags.length }}</div>
            <div class="hs-label">ESLint</div>
          </div>
          <div class="header-score" :class="accessibilityDefects.length > 0 ? 'score-amber' : 'score-green'">
            <div class="hs-val">{{ accessibilityDefects.length }}</div>
            <div class="hs-label">A11y</div>
          </div>
          <div class="header-score score-blue">
            <div class="hs-val">{{ apiCalls.length }}</div>
            <div class="hs-label">API</div>
          </div>
        </div>
      </div>

      <!-- Metrics Row -->
      <div class="metrics-row">
        <div class="metric-pill">
          <span class="mp-label">Methods</span>
          <span class="mp-val">{{ metrics.methods || 0 }}</span>
        </div>
        <div class="metric-pill">
          <span class="mp-label">Script Lines</span>
          <span class="mp-val">{{ metrics.script_lines || 0 }}</span>
        </div>
        <div class="metric-pill">
          <span class="mp-label">Complexity</span>
          <span class="mp-val">{{ metrics.cyclomatic_complexity || 0 }}</span>
        </div>
        <div class="metric-pill">
          <span class="mp-label">API Calls</span>
          <span class="mp-val">{{ metrics.api_total || 0 }}</span>
        </div>
      </div>

      <!-- Tabs -->
      <div class="tab-bar">
        <button
          v-for="tab in tabs"
          :key="tab.id"
          class="tab-btn"
          :class="{ active: activeTab === tab.id }"
          @click="activeTab = tab.id"
        >
          <span class="tab-dot" :class="tab.dotClass" v-if="getTabCount(tab.id) > 0"></span>
          {{ tab.label }}
          <span class="tab-count">{{ getTabCount(tab.id) }}</span>
        </button>
      </div>

      <!-- Tab Content -->
      <div class="tab-content">
        <!-- AI Issues -->
        <div v-if="activeTab === 'ai'">
          <div v-if="aiIssues.length === 0" class="tab-empty">
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" opacity="0.3">
              <path d="M22 11.08V12a10 10 0 11-5.93-9.14"/>
              <polyline points="22 4 12 14.01 9 11.01"/>
            </svg>
            <span>No AI issues detected</span>
          </div>
          <div v-else class="issue-list">
            <div v-for="(issue, i) in aiIssues" :key="i" class="issue-card">
              <div class="issue-card-top">
                <div class="issue-title">{{ issue.issue_title || 'Untitled Issue' }}</div>
                <span class="sev-badge" :class="getSeverityClass(issue.severity)">{{ issue.severity || 'Low' }}</span>
              </div>
              <p class="issue-desc">{{ issue.description }}</p>
              <div class="issue-meta">
                <span class="line-ref">Line {{ issue.line_number || 'N/A' }}</span>
              </div>
              <CodeSnippet v-if="issue.code_snippet" :code="issue.code_snippet" :targetLine="issue.line_number" />
            </div>
          </div>
        </div>

        <!-- ESLint -->
        <div v-if="activeTab === 'eslint'">
          <div v-if="eslintFlags.length === 0" class="tab-empty">
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" opacity="0.3">
              <path d="M22 11.08V12a10 10 0 11-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/>
            </svg>
            <span>No ESLint flags found</span>
          </div>
          <div v-else class="issue-list">
            <div v-for="(flag, i) in eslintFlags" :key="i" class="issue-card">
              <div class="issue-card-top">
                <div class="issue-title mono-title">{{ flag.rule || 'Unknown Rule' }}</div>
                <span class="sev-badge" :class="getSeverityClass(flag.severity)">{{ flag.severity || 'Low' }}</span>
              </div>
              <p class="issue-desc">{{ flag.message }}</p>
              <div class="issue-meta"><span class="line-ref">Line {{ flag.line_number || 'N/A' }}</span></div>
              <CodeSnippet v-if="flag.code_snippet" :code="flag.code_snippet" :targetLine="flag.line_number" />
            </div>
          </div>
        </div>

        <!-- Accessibility -->
        <div v-if="activeTab === 'accessibility'">
          <div v-if="accessibilityDefects.length === 0" class="tab-empty">
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" opacity="0.3">
              <circle cx="12" cy="12" r="10"/><path d="M12 8v4M12 16h.01"/>
            </svg>
            <span>No accessibility defects found</span>
          </div>
          <div v-else class="issue-list">
            <div v-for="(defect, i) in accessibilityDefects" :key="i" class="issue-card">
              <div class="issue-card-top">
                <div class="issue-title mono-title">{{ defect.rule || 'Unknown Rule' }}</div>
                <span class="sev-badge badge-amber">A11y</span>
              </div>
              <p class="issue-desc">{{ defect.message }}</p>
              <div v-if="defect.wcag_criterion" class="wcag-chip">
                <span class="wcag-level">WCAG {{ defect.wcag_level }}</span>
                <span class="wcag-text">{{ defect.wcag_criterion }}</span>
              </div>
              <div class="issue-meta"><span class="line-ref">Line {{ defect.line_number || 'N/A' }}</span></div>
              <CodeSnippet v-if="defect.code_snippet" :code="defect.code_snippet" :targetLine="defect.line_number" />
            </div>
          </div>
        </div>

        <!-- API Calls -->
        <div v-if="activeTab === 'api'">
          <div v-if="apiCalls.length === 0" class="tab-empty">
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" opacity="0.3">
              <circle cx="12" cy="12" r="10"/><path d="M12 8v4M12 16h.01"/>
            </svg>
            <span>No API calls found</span>
          </div>
          <div v-else class="issue-list">
            <div v-for="(call, i) in apiCalls" :key="i" class="issue-card">
              <div class="issue-card-top">
                <div class="issue-title mono-title">{{ call.method }} {{ call.endpoint }}</div>
                <span v-if="call.in_loop" class="sev-badge badge-high">IN LOOP</span>
              </div>
              <div class="issue-meta"><span class="line-ref">Line {{ call.line_number || 'N/A' }}</span></div>
              <CodeSnippet v-if="call.code_snippet" :code="call.code_snippet" :targetLine="call.line_number" />
            </div>
          </div>
        </div>
        <!-- Dependencies Tab -->
        <div v-if="activeTab === 'dependencies'" class="dep-tab">

          <!-- Loading -->
          <div v-if="depLoading" class="tab-empty">
            <div class="dep-spinner"></div>
            <span>Loading dependency data…</span>
          </div>

          <!-- Error -->
          <div v-else-if="depError" class="tab-empty">
            <span style="color:var(--color-status-error)">{{ depError }}</span>
          </div>

          <template v-else-if="depData">

            <!-- Cycle Warning -->
            <div v-if="depData.is_in_cycle" class="cycle-warning">
              <div class="cycle-warning-header">
                <svg width="15" height="15" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M8 2a6 6 0 100 12A6 6 0 008 2z"/>
                  <path d="M8 6v3M8 11h.01"/>
                </svg>
                ⚠ CIRCULAR DEPENDENCY DETECTED
              </div>
              <p class="cycle-path" v-if="depData.cycle && depData.cycle.length">
                {{ depData.cycle.join(' → ') }}
              </p>
            </div>

            <!-- Impact Score -->
            <div class="dep-impact-row">
              <span class="dep-kv-label">Impact Score</span>
              <span class="impact-num" :class="getImpactClass(depData.impact_score)">
                {{ depData.impact_score }}
              </span>
              <span class="dep-kv-label" style="margin-left:24px">Category</span>
              <span class="cat-chip">{{ depData.category || '—' }}</span>
            </div>

            <!-- Change Impact Summary -->
            <div class="dep-section" v-if="depData.transitive_impact">
              <div class="dep-section-title">Change Impact</div>
              <div class="impact-grid">
                <div class="impact-cell">
                  <span class="ic-num">{{ (depData.dependents || []).length }}</span>
                  <span class="ic-label">Direct</span>
                </div>
                <div class="impact-cell">
                  <span class="ic-num">{{ (depData.transitive_impact || []).length }}</span>
                  <span class="ic-label">Transitive</span>
                </div>
                <div class="impact-cell ic-total">
                  <span class="ic-num">{{ (depData.dependents || []).length + (depData.transitive_impact || []).length }}</span>
                  <span class="ic-label">Total Affected</span>
                </div>
              </div>
            </div>

            <!-- Imported By (in-edges) -->
            <div class="dep-section">
              <div class="dep-section-title">
                <svg width="12" height="12" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M8 2v12M2 8l6 6 6-6"/>
                </svg>
                {{ (depData.dependents || []).length }} file{{ (depData.dependents || []).length !== 1 ? 's' : '' }} import this file
              </div>
              <div v-if="!depData.dependents || depData.dependents.length === 0" class="dep-empty">
                Nothing imports this file.
              </div>
              <div v-else class="dep-list">
                <div
                  v-for="f in depData.dependents"
                  :key="f"
                  class="dep-item"
                  @click="navigateDep(f)"
                >
                  <span class="dep-arrow">←</span>
                  <span class="dep-item-name">{{ getBasename(f) }}</span>
                  <span class="dep-item-path">{{ f }}</span>
                </div>
              </div>
            </div>

            <!-- Imports (out-edges) -->
            <div class="dep-section">
              <div class="dep-section-title">
                <svg width="12" height="12" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M8 14V2M2 8l6-6 6 6"/>
                </svg>
                This file imports {{ (depData.dependencies || []).length }} file{{ (depData.dependencies || []).length !== 1 ? 's' : '' }}
              </div>
              <div v-if="!depData.dependencies || depData.dependencies.length === 0" class="dep-empty">
                This file imports nothing local.
              </div>
              <div v-else class="dep-list">
                <div
                  v-for="f in depData.dependencies"
                  :key="f"
                  class="dep-item"
                  @click="navigateDep(f)"
                >
                  <span class="dep-arrow">→</span>
                  <span class="dep-item-name">{{ getBasename(f) }}</span>
                  <span class="dep-item-path">{{ f }}</span>
                </div>
              </div>
            </div>

          </template>

          <!-- Not yet loaded / no data -->
          <div v-else class="tab-empty">
            <span>Click to load dependency data.</span>
          </div>
        </div>

      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, computed } from 'vue'
import { useRouter } from 'vue-router'
import { filesAPI } from '../api.js'
import CodeSnippet from './CodeSnippet.vue'

const router = useRouter()

const props = defineProps({ filePath: { type: String, required: true } })

const loading = ref(false)
const error = ref(null)
const metrics = ref({})
const aiIssues = ref([])
const eslintFlags = ref([])
const accessibilityDefects = ref([])
const apiCalls = ref([])
const activeTab = ref('ai')

const fileName = computed(() => props.filePath ? props.filePath.split('/').pop() : '')

const tabs = [
  { id: 'ai',            label: 'AI Issues',    dotClass: 'dot-purple' },
  { id: 'eslint',        label: 'ESLint',       dotClass: 'dot-teal' },
  { id: 'accessibility', label: 'Accessibility', dotClass: 'dot-amber' },
  { id: 'api',           label: 'API Calls',    dotClass: 'dot-blue' },
  { id: 'dependencies',  label: 'Dependencies', dotClass: 'dot-green' },
]

// Dependency tab state (lazy-loaded)
const depData    = ref(null)
const depLoading = ref(false)
const depError   = ref(null)
const depFetched = ref(false)

const getTabCount = (id) => {
  if (id === 'dependencies') {
    if (!depData.value) return 0
    return (depData.value.in_degree || 0) + (depData.value.out_degree || 0)
  }
  return { ai: aiIssues, eslint: eslintFlags, accessibility: accessibilityDefects, api: apiCalls }[id]?.value?.length || 0
}

const fetchDepData = async () => {
  if (!props.filePath || depFetched.value) return
  depLoading.value = true
  depError.value   = null
  try {
    const res = await filesAPI.getFileDependencies(props.filePath)
    depData.value = res.data || {}
  } catch (err) {
    depError.value = err.response?.data?.error || err.message || 'Failed to load dependency data'
  } finally {
    depLoading.value = false
    depFetched.value = true
  }
}

// Reset dep state when the selected file changes
watch(() => props.filePath, () => {
  depData.value    = null
  depFetched.value = false
  depError.value   = null
})

// Lazily fetch dep data when the tab becomes active
watch(activeTab, (tab) => {
  if (tab === 'dependencies') fetchDepData()
})

const getSeverityClass = (s) => {
  const l = (s || '').toLowerCase()
  if (l === 'high' || l === 'error') return 'badge-high'
  if (l === 'medium' || l === 'warning') return 'badge-med'
  return 'badge-low'
}

const fetchFileData = async () => {
  if (!props.filePath) return
  depData.value = null; depFetched.value = false
  loading.value = true; error.value = null
  try {
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
  } catch (err) {
    error.value = err.response?.data?.error || err.message || 'Failed to load file details'
  } finally { loading.value = false }
}

watch(() => props.filePath, (p) => { if (p) fetchFileData() }, { immediate: true })

// ── Dependency tab helpers ────────────────────────────────────────
const getBasename = (p) => (p || '').split('/').pop()

const getImpactClass = (score) => {
  if (score >= 50) return 'impact-critical'
  if (score >= 20) return 'impact-high'
  if (score >= 5)  return 'impact-med'
  return 'impact-low'
}

const navigateDep = (filePath) => {
  router.push({ path: '/audit', query: { file: filePath } })
}
</script>

<style scoped>
.file-detail {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: var(--color-bg-primary);
  overflow: hidden;
}

.detail-loading, .detail-error {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  gap: 12px;
}

.spinner {
  width: 32px; height: 32px;
  border: 2px solid var(--color-border-emphasis);
  border-top-color: var(--color-accent-primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

.detail-loading p, .detail-error .err-msg {
  font-size: 13px;
  color: var(--color-text-secondary);
  text-align: center;
  max-width: 280px;
}

.err-ico {
  width: 40px; height: 40px;
  border-radius: 50%;
  background: rgba(248,81,73,0.1);
  border: 1px solid rgba(248,81,73,0.3);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-status-error);
  font-weight: 700;
  font-size: 18px;
}

.btn-sm {
  padding: 6px 14px;
  background: var(--color-accent-primary);
  color: white;
  border-radius: var(--rounded-base);
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
}

.detail-body {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

/* File Header */
.file-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 18px;
  border-bottom: 1px solid var(--color-border);
  flex-shrink: 0;
  gap: 12px;
}

.file-header-left {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}

.file-type-chip {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 3px 8px;
  background: rgba(56,139,253,0.1);
  border: 1px solid rgba(56,139,253,0.2);
  border-radius: var(--rounded-sm);
  font-size: 10px;
  font-weight: 700;
  color: var(--color-accent-hover);
  font-family: var(--font-mono);
  flex-shrink: 0;
}

.file-title {
  font-family: var(--font-mono);
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text-primary);
}

.file-path {
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--color-text-tertiary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.file-header-scores {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
}

.header-score {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 6px 10px;
  border-radius: var(--rounded-base);
  min-width: 44px;
}

.hs-val {
  font-family: var(--font-mono);
  font-size: 18px;
  font-weight: 700;
  line-height: 1;
}

.hs-label {
  font-size: 9px;
  font-weight: 600;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  margin-top: 3px;
}

.score-purple { background: rgba(188,140,255,0.1); }
.score-purple .hs-val { color: var(--color-category-ai); }
.score-purple .hs-label { color: rgba(188,140,255,0.6); }

.score-teal { background: rgba(86,211,100,0.1); }
.score-teal .hs-val { color: var(--color-category-eslint); }
.score-teal .hs-label { color: rgba(86,211,100,0.6); }

.score-amber { background: rgba(227,179,65,0.1); }
.score-amber .hs-val { color: var(--color-category-a11y); }
.score-amber .hs-label { color: rgba(227,179,65,0.6); }

.score-blue { background: rgba(88,166,255,0.1); }
.score-blue .hs-val { color: var(--color-category-api); }
.score-blue .hs-label { color: rgba(88,166,255,0.6); }

.score-green { background: rgba(63,185,80,0.08); }
.score-green .hs-val { color: var(--color-status-success); }
.score-green .hs-label { color: rgba(63,185,80,0.5); }

/* Metrics Row */
.metrics-row {
  display: flex;
  gap: 0;
  border-bottom: 1px solid var(--color-border);
  flex-shrink: 0;
}

.metric-pill {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 10px 18px;
  border-right: 1px solid var(--color-border);
}

.metric-pill:last-child { border-right: none; }

.mp-label {
  font-size: 9px;
  font-weight: 600;
  color: var(--color-text-tertiary);
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.mp-val {
  font-family: var(--font-mono);
  font-size: 20px;
  font-weight: 700;
  color: var(--color-text-primary);
  line-height: 1.1;
}

/* Tabs */
.tab-bar {
  display: flex;
  border-bottom: 1px solid var(--color-border);
  flex-shrink: 0;
  padding: 0 6px;
}

.tab-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 10px 14px;
  font-size: 13px;
  font-weight: 500;
  color: var(--color-text-secondary);
  cursor: pointer;
  border-bottom: 2px solid transparent;
  margin-bottom: -1px;
  transition: all 150ms;
}

.tab-btn:hover { color: var(--color-text-primary); }

.tab-btn.active {
  color: var(--color-text-primary);
  border-bottom-color: var(--color-accent-primary);
  font-weight: 600;
}

.tab-dot {
  width: 6px; height: 6px;
  border-radius: 50%;
}

.dot-purple { background: var(--color-category-ai); }
.dot-teal   { background: var(--color-category-eslint); }
.dot-amber  { background: var(--color-category-a11y); }
.dot-blue   { background: var(--color-category-api); }

.tab-count {
  font-family: var(--font-mono);
  font-size: 10px;
  padding: 1px 5px;
  background: var(--color-bg-elevated);
  border-radius: var(--rounded-full);
  color: var(--color-text-tertiary);
}

.tab-btn.active .tab-count {
  background: rgba(56,139,253,0.15);
  color: var(--color-accent-hover);
}

/* Tab Content */
.tab-content {
  flex: 1;
  overflow-y: auto;
  padding: 14px;
}

.tab-empty {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 32px;
  color: var(--color-text-tertiary);
  font-size: 13px;
  justify-content: center;
}

.issue-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.issue-card {
  background: var(--color-bg-secondary);
  border: 1px solid var(--color-border);
  border-radius: var(--rounded-lg);
  padding: 14px 16px;
  transition: border-color 150ms;
}

.issue-card:hover {
  border-color: var(--color-border-emphasis);
}

.issue-card-top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 8px;
}

.issue-title {
  font-size: 13.5px;
  font-weight: 600;
  color: var(--color-text-primary);
  flex: 1;
  line-height: 1.4;
}

.mono-title { font-family: var(--font-mono); font-size: 12px; }

.issue-desc {
  font-size: 13px;
  color: var(--color-text-secondary);
  line-height: 1.65;
  margin-bottom: 10px;
}

.issue-meta { margin-bottom: 8px; }

.line-ref {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--color-text-tertiary);
  background: var(--color-bg-tertiary);
  padding: 2px 7px;
  border-radius: var(--rounded-sm);
}

.wcag-chip {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 7px 10px;
  background: var(--color-bg-tertiary);
  border-radius: var(--rounded-base);
  margin-bottom: 10px;
}

.wcag-level {
  font-size: 10px;
  font-weight: 700;
  color: var(--color-category-a11y);
  font-family: var(--font-mono);
  flex-shrink: 0;
}

.wcag-text {
  font-size: 11.5px;
  color: var(--color-text-secondary);
}

/* Severity badges */
.sev-badge {
  display: inline-flex;
  align-items: center;
  padding: 2px 8px;
  border-radius: var(--rounded-full);
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  flex-shrink: 0;
}

.badge-high { background: rgba(240,136,62,0.15); color: var(--color-severity-high); border: 1px solid rgba(240,136,62,0.3); }
.badge-med  { background: rgba(210,153,34,0.12); color: var(--color-severity-medium); border: 1px solid rgba(210,153,34,0.3); }
.badge-low  { background: rgba(63,185,80,0.1);  color: var(--color-severity-low); border: 1px solid rgba(63,185,80,0.25); }
.badge-amber { background: rgba(227,179,65,0.12); color: var(--color-category-a11y); border: 1px solid rgba(227,179,65,0.3); }

@keyframes spin {
  from { transform: rotate(0deg); }
  to   { transform: rotate(360deg); }
}

/* ── Dependency Tab ─────────────────────────────────────── */
.dot-green { background: #3FB950; }

.dep-tab {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.dep-spinner {
  width: 24px; height: 24px;
  border: 2px solid var(--color-border-emphasis);
  border-top-color: var(--color-accent-primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

/* Cycle Warning */
.cycle-warning {
  background: rgba(248,81,73,0.08);
  border: 1px solid rgba(248,81,73,0.4);
  border-left: 3px solid #F85149;
  border-radius: var(--rounded-lg);
  padding: 12px 16px;
}
.cycle-warning-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  font-weight: 700;
  color: #F85149;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  margin-bottom: 8px;
}
.cycle-path {
  font-family: var(--font-mono);
  font-size: 11.5px;
  color: var(--color-text-secondary);
  word-break: break-all;
  line-height: 1.7;
  margin: 0;
}

/* Impact row */
.dep-impact-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  background: var(--color-bg-secondary);
  border: 1px solid var(--color-border);
  border-radius: var(--rounded-lg);
}
.dep-kv-label {
  font-size: 10px;
  font-weight: 600;
  color: var(--color-text-tertiary);
  text-transform: uppercase;
  letter-spacing: 0.06em;
}
.impact-num {
  font-family: var(--font-mono);
  font-size: 18px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: var(--rounded-base);
}
.impact-critical { color: #F85149; background: rgba(248,81,73,0.12); }
.impact-high     { color: #F0883E; background: rgba(240,136,62,0.12); }
.impact-med      { color: #D29922; background: rgba(210,153,34,0.12); }
.impact-low      { color: #3FB950; background: rgba(63,185,80,0.10); }
.cat-chip {
  font-size: 11px;
  font-weight: 600;
  font-family: var(--font-mono);
  color: var(--color-text-secondary);
  background: var(--color-bg-tertiary);
  padding: 2px 8px;
  border-radius: var(--rounded-full);
  border: 1px solid var(--color-border);
}

/* Impact Grid */
.impact-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
}
.impact-cell {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 3px;
  padding: 10px;
  background: var(--color-bg-secondary);
  border: 1px solid var(--color-border);
  border-radius: var(--rounded-base);
}
.impact-cell.ic-total {
  border-color: rgba(56,139,253,0.3);
  background: rgba(56,139,253,0.06);
}
.ic-num {
  font-family: var(--font-mono);
  font-size: 22px;
  font-weight: 700;
  color: var(--color-text-primary);
  line-height: 1;
}
.ic-total .ic-num { color: var(--color-accent-hover, #58A6FF); }
.ic-label {
  font-size: 10px;
  font-weight: 600;
  color: var(--color-text-tertiary);
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

/* Dep section */
.dep-section {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.dep-section-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  font-weight: 600;
  color: var(--color-text-tertiary);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  padding-bottom: 6px;
  border-bottom: 1px solid var(--color-border);
}
.dep-empty {
  padding: 12px 0;
  font-size: 12px;
  color: var(--color-text-tertiary);
  font-style: italic;
}
.dep-list {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.dep-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 7px 10px;
  border-radius: var(--rounded-base);
  cursor: pointer;
  transition: background 120ms;
}
.dep-item:hover {
  background: var(--color-bg-secondary);
}
.dep-item:hover .dep-item-name {
  color: var(--color-accent-hover, #58A6FF);
  text-decoration: underline;
}
.dep-arrow {
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--color-text-tertiary);
  flex-shrink: 0;
  width: 14px;
  text-align: center;
}
.dep-item-name {
  font-family: var(--font-mono);
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-primary);
  flex-shrink: 0;
  transition: color 120ms;
}
.dep-item-path {
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--color-text-tertiary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
