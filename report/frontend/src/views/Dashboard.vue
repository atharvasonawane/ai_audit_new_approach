<template>
  <div class="dashboard">
    <!-- Loading -->
    <div v-if="loading" class="full-center">
      <div class="loader-wrap">
        <div class="spinner"></div>
        <p class="loader-text">Loading dashboard...</p>
      </div>
    </div>

    <!-- Error -->
    <div v-else-if="error" class="full-center">
      <div class="error-card">
        <div class="error-icon">!</div>
        <h3>Failed to load</h3>
        <p>{{ error }}</p>
        <button class="btn-primary" @click="fetchDashboardData">
          <svg width="13" height="13" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M1 4s1-3 7-3a7 7 0 010 14c-3 0-5.5-1.5-6.5-4"/>
            <path d="M1 1v3h3"/>
          </svg>
          Retry
        </button>
      </div>
    </div>

    <!-- Dashboard Content -->
    <div v-else class="dashboard-content fade-in">
      <!-- Top Bar -->
      <div class="dash-header">
        <div class="dash-header-left">
          <div class="project-badge">
            <svg width="13" height="13" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5">
              <path d="M1 4a1 1 0 011-1h4l2 2h6a1 1 0 011 1v7a1 1 0 01-1 1H2a1 1 0 01-1-1V4z"/>
            </svg>
            {{ summary.project_name || 'Unknown Project' }}
          </div>
          <h1 class="dash-title">Audit Dashboard</h1>
          <p class="dash-sub">Last scan completed — all findings below</p>
        </div>
        <button class="btn-primary" @click="fetchDashboardData">
          <svg width="13" height="13" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M1 4s1-3 7-3a7 7 0 010 14c-3 0-5.5-1.5-6.5-4"/>
            <path d="M1 1v3h3"/>
          </svg>
          Re-Audit
        </button>
      </div>

      <!-- Executive Summary -->
      <div class="exec-panel" v-if="executiveSummary.synthesis_text">
        <div class="exec-label">
          <svg width="12" height="12" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="8" cy="8" r="6"/><path d="M8 5v4l2 2"/>
          </svg>
          Executive Summary
        </div>
        <p class="exec-text">{{ executiveSummary.synthesis_text }}</p>
      </div>

      <!-- Metrics -->
      <div class="metrics-grid">
        <div class="metric-card">
          <div class="metric-label">Total Files</div>
          <div class="metric-value">{{ summary.total_files || 0 }}</div>
          <div class="metric-bar" style="background:rgba(56,139,253,0.2)">
            <div class="metric-fill" style="background:#388BFD;width:65%"></div>
          </div>
        </div>
        <div class="metric-card">
          <div class="metric-label">Total Issues</div>
          <div class="metric-value accent-red">{{ summary.ai_issues_total || 0 }}</div>
          <div class="metric-bar" style="background:rgba(248,81,73,0.15)">
            <div class="metric-fill" style="background:#F85149;width:48%"></div>
          </div>
        </div>
        <div class="metric-card">
          <div class="metric-label">ESLint Flags</div>
          <div class="metric-value accent-green">{{ summary.total_eslint_flags || 0 }}</div>
          <div class="metric-bar" style="background:rgba(63,185,80,0.15)">
            <div class="metric-fill" style="background:#3FB950;width:55%"></div>
          </div>
        </div>
        <div class="metric-card">
          <div class="metric-label">A11y Defects</div>
          <div class="metric-value accent-amber">{{ summary.total_accessibility_defects || 0 }}</div>
          <div class="metric-bar" style="background:rgba(210,153,34,0.15)">
            <div class="metric-fill" style="background:#D29922;width:80%"></div>
          </div>
        </div>
        <div class="metric-card">
          <div class="metric-label">Avg Complexity</div>
          <div class="metric-value">{{ summary.average_complexity || 0 }}</div>
          <div class="metric-bar" style="background:rgba(137,87,229,0.15)">
            <div class="metric-fill" style="background:#8957E5;width:30%"></div>
          </div>
        </div>
        <div class="metric-card">
          <div class="metric-label">High Severity</div>
          <div class="metric-value accent-orange">{{ summary.ai_issues_by_severity?.High || 0 }}</div>
          <div class="metric-bar" style="background:rgba(240,136,62,0.15)">
            <div class="metric-fill" style="background:#F0883E;width:25%"></div>
          </div>
        </div>
      </div>

      <!-- Dependency Health -->
      <div class="exec-panel" v-if="dependencySummary.total_nodes">
        <div class="exec-label" style="color: var(--color-accent-primary);">
          <svg width="12" height="12" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M4 8h8m-4-4v8"/>
          </svg>
          Dependency Health
        </div>
        <div class="dep-metrics-grid">
          <div class="dep-metric">
            <span class="dep-label">Total Files</span>
            <span class="dep-value">{{ dependencySummary.total_nodes }}</span>
          </div>
          <div class="dep-metric">
            <span class="dep-label">Total Edges</span>
            <span class="dep-value">{{ dependencySummary.total_edges }}</span>
          </div>
          <div class="dep-metric">
            <span class="dep-label">Max Depth</span>
            <span class="dep-value">{{ dependencySummary.max_depth }}</span>
          </div>
          <div class="dep-metric">
            <span class="dep-label">Orphans <span v-if="dependencySummary.orphan_count > 0" title="Warning">⚠️</span></span>
            <span class="dep-value" :class="{'accent-amber': dependencySummary.orphan_count > 0}">{{ dependencySummary.orphan_count }}</span>
          </div>
          <div class="dep-metric">
            <span class="dep-label">Circular Deps <span v-if="dependencySummary.cycle_count > 0" title="Danger">🔴</span></span>
            <span class="dep-value" :class="{'accent-red': dependencySummary.cycle_count > 0}">{{ dependencySummary.cycle_count }}</span>
          </div>
        </div>
        <div class="dep-critical" v-if="dependencySummary.most_critical_file">
          <span class="dep-label">Most Critical File:</span>
          <span class="offender-name">{{ getFileName(dependencySummary.most_critical_file) }}</span>
          <span class="dep-sub"> (In-degree: {{ dependencySummary.most_critical_file_in_degree }})</span>
        </div>
      </div>

      <!-- Charts -->
      <div class="charts-grid">
        <div class="chart-card">
          <div class="chart-header">
            <span class="chart-title">Issues by Severity</span>
            <div class="chart-legend">
              <div class="leg-item"><span class="leg-dot" style="background:#F0883E"></span>High</div>
              <div class="leg-item"><span class="leg-dot" style="background:#D29922"></span>Medium</div>
              <div class="leg-item"><span class="leg-dot" style="background:#3FB950"></span>Low</div>
            </div>
          </div>
          <div class="chart-wrap">
            <Doughnut :data="severityChartData" :options="severityChartOptions" />
          </div>
        </div>

        <div class="chart-card">
          <div class="chart-header">
            <span class="chart-title">Issues by Category</span>
          </div>
          <div class="chart-wrap">
            <Bar :data="categoryChartData" :options="categoryChartOptions" />
          </div>
        </div>
      </div>

      <!-- Worst Offenders -->
      <div class="offenders-card">
        <div class="offenders-header">
          <span class="chart-title">Worst Offenders</span>
          <span class="offenders-sub">Files with the most issues</span>
        </div>

        <div v-if="worstOffenders.length === 0" class="offenders-empty">
          <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1" opacity="0.25">
            <circle cx="11" cy="11" r="8"/><path d="M21 21l-4.35-4.35"/>
          </svg>
          <p>No files analyzed yet</p>
        </div>

        <div v-else class="offenders-list">
          <div
            v-for="(file, i) in worstOffenders"
            :key="i"
            class="offender-row"
            @click="navigateToFile(file.file_path)"
          >
            <div class="offender-rank">#{{ i + 1 }}</div>
            <div class="offender-info">
              <div class="offender-name">{{ getFileName(file.file_path) }}</div>
              <div class="offender-path">{{ file.file_path }}</div>
            </div>
            <div class="offender-scores">
              <div class="score-item">
                <span class="score-label">Issues</span>
                <span class="score-val">{{ file.composite_score || 0 }}</span>
              </div>
              <div class="score-item">
                <span class="score-label">ESLint</span>
                <span class="score-val">{{ file.eslint_flag_count || 0 }}</span>
              </div>
              <div class="score-item">
                <span class="score-label">AI</span>
                <span class="score-val ai-col">{{ file.ai_issue_count || 0 }}</span>
              </div>
            </div>
            <svg class="offender-arrow" width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M6 12l4-4-4-4"/>
            </svg>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { filesAPI } from '../api.js'
import {
  Chart as ChartJS, Title, Tooltip, Legend,
  ArcElement, BarElement, CategoryScale, LinearScale
} from 'chart.js'
import { Doughnut, Bar } from 'vue-chartjs'

ChartJS.register(Title, Tooltip, Legend, ArcElement, BarElement, CategoryScale, LinearScale)

const router = useRouter()
const loading = ref(false)
const error = ref(null)
const summary = ref({})
const executiveSummary = ref({})
const worstOffenders = ref([])
const dependencySummary = ref({})

const severityChartData = computed(() => {
  const s = summary.value.ai_issues_by_severity || {}
  return {
    labels: ['High', 'Medium', 'Low'],
    datasets: [{ data: [s.High||0, s.Medium||0, s.Low||0], backgroundColor: ['#F0883E','#D29922','#3FB950'], borderWidth: 0, hoverOffset: 4 }]
  }
})

const severityChartOptions = {
  responsive: true, maintainAspectRatio: true,
  cutout: '65%',
  plugins: {
    legend: { display: false },
    tooltip: { backgroundColor: '#0D1117', titleColor: '#E6EDF3', bodyColor: '#7D8590', borderColor: '#21262D', borderWidth: 1, padding: 10 }
  }
}

const categoryChartData = computed(() => ({
  labels: ['AI Issues', 'ESLint', 'Accessibility'],
  datasets: [{
    label: 'Count',
    data: [summary.value.ai_issues_total||0, summary.value.total_eslint_flags||0, summary.value.total_accessibility_defects||0],
    backgroundColor: ['rgba(188,140,255,0.8)', 'rgba(86,211,100,0.8)', 'rgba(227,179,65,0.8)'],
    borderWidth: 0, borderRadius: 4
  }]
}))

const categoryChartOptions = {
  responsive: true, maintainAspectRatio: true,
  scales: {
    y: { beginAtZero: true, ticks: { color: '#7D8590', font: { size: 11 } }, grid: { color: '#21262D' } },
    x: { ticks: { color: '#7D8590', font: { size: 11 } }, grid: { display: false } }
  },
  plugins: {
    legend: { display: false },
    tooltip: { backgroundColor: '#0D1117', titleColor: '#E6EDF3', bodyColor: '#7D8590', borderColor: '#21262D', borderWidth: 1, padding: 10 }
  }
}

const fetchDashboardData = async () => {
  loading.value = true; error.value = null
  try {
    const [summaryRes, executiveRes, offendersRes, depSummaryRes] = await Promise.all([
      filesAPI.getSummary(), filesAPI.getExecutiveSummary(), filesAPI.getWorstOffenders(10),
      filesAPI.getDependencySummary().catch(() => ({ data: {} }))
    ])
    summary.value = summaryRes.data || {}
    executiveSummary.value = executiveRes.data || {}
    worstOffenders.value = offendersRes.data || []
    dependencySummary.value = depSummaryRes.data || {}
  } catch (err) {
    if (err.code === 'ERR_NETWORK' || err.message?.includes('Network Error')) {
      error.value = 'Cannot connect to API server. Ensure Flask is running on http://localhost:5000'
    } else {
      error.value = err.message || 'An unexpected error occurred'
    }
  } finally { loading.value = false }
}

const getFileName = (p) => p ? p.split('/').pop() : ''
const navigateToFile = (p) => router.push({ path: '/audit', query: { file: p } })

onMounted(fetchDashboardData)
</script>

<style scoped>
.dashboard {
  height: 100%;
  overflow-y: auto;
  background: var(--color-bg-primary);
}

.full-center {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.loader-wrap {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 14px;
}

.spinner {
  width: 36px;
  height: 36px;
  border: 2px solid var(--color-border-emphasis);
  border-top-color: var(--color-accent-primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

.loader-text { font-size: 13px; color: var(--color-text-secondary); }

.error-card {
  background: var(--color-bg-secondary);
  border: 1px solid rgba(248,81,73,0.3);
  border-radius: var(--rounded-lg);
  padding: 32px;
  text-align: center;
  max-width: 360px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
}

.error-icon {
  width: 44px; height: 44px;
  border-radius: 50%;
  background: rgba(248,81,73,0.1);
  border: 1px solid rgba(248,81,73,0.3);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-status-error);
  font-weight: 700;
  font-size: 20px;
}

.error-card h3 { font-size: 16px; color: var(--color-text-primary); }
.error-card p { font-size: 13px; color: var(--color-text-secondary); }

.dashboard-content {
  padding: 28px 32px;
  display: flex;
  flex-direction: column;
  gap: 20px;
  max-width: 1200px;
}

/* Header */
.dash-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
}

.dash-header-left { display: flex; flex-direction: column; gap: 4px; }

.project-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 3px 10px;
  background: var(--color-bg-tertiary);
  border: 1px solid var(--color-border-emphasis);
  border-radius: var(--rounded-full);
  font-size: 11px;
  color: var(--color-text-secondary);
  font-family: var(--font-mono);
  width: fit-content;
}

.dash-title {
  font-size: 30px;
  font-weight: 800;
  letter-spacing: -0.035em;
  color: var(--color-text-primary);
}

.dash-sub { font-size: 13px; color: var(--color-text-secondary); }

/* Executive Summary */
.exec-panel {
  background: var(--color-bg-secondary);
  border: 1px solid var(--color-border);
  border-left: 3px solid var(--color-accent-secondary);
  border-radius: var(--rounded-lg);
  padding: 16px 20px;
}

.exec-label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  font-weight: 600;
  color: var(--color-accent-secondary);
  letter-spacing: 0.06em;
  text-transform: uppercase;
  margin-bottom: 8px;
}

.exec-text {
  font-size: 13.5px;
  color: var(--color-text-secondary);
  line-height: 1.7;
  max-height: 120px;
  overflow-y: auto;
}

/* Metrics */
.metrics-grid {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 12px;
}

.dep-metrics-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 12px;
  margin-top: 12px;
  margin-bottom: 12px;
}
.dep-metric {
  background: var(--color-bg-primary);
  border: 1px solid var(--color-border);
  border-radius: var(--rounded-base);
  padding: 10px 14px;
  display: flex;
  flex-direction: column;
}
.dep-label {
  font-size: 10px;
  font-weight: 600;
  color: var(--color-text-tertiary);
  text-transform: uppercase;
  margin-bottom: 4px;
}
.dep-value {
  font-family: var(--font-mono);
  font-size: 20px;
  font-weight: 700;
  color: var(--color-text-primary);
}
.dep-critical {
  font-size: 13px;
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px dashed var(--color-border);
  display: flex;
  align-items: center;
  gap: 8px;
}
.dep-sub { color: var(--color-text-tertiary); font-family: var(--font-mono); }

@media (max-width: 1100px) { .metrics-grid { grid-template-columns: repeat(3, 1fr); } }
@media (max-width: 700px)  { .metrics-grid { grid-template-columns: repeat(2, 1fr); } }

.metric-card {
  background: var(--color-bg-secondary);
  border: 1px solid var(--color-border);
  border-radius: var(--rounded-lg);
  padding: 16px;
  transition: border-color 150ms;
}

.metric-card:hover { border-color: var(--color-border-emphasis); }

.metric-label {
  font-size: 10px;
  font-weight: 600;
  color: var(--color-text-tertiary);
  letter-spacing: 0.08em;
  text-transform: uppercase;
  margin-bottom: 8px;
}

.metric-value {
  font-family: var(--font-mono);
  font-size: 28px;
  font-weight: 700;
  color: var(--color-text-primary);
  letter-spacing: -0.03em;
  margin-bottom: 12px;
  line-height: 1;
}

.metric-value.accent-red    { color: var(--color-status-error); }
.metric-value.accent-green  { color: var(--color-status-success); }
.metric-value.accent-amber  { color: var(--color-status-warning); }
.metric-value.accent-orange { color: var(--color-severity-high); }

.metric-bar {
  height: 3px;
  border-radius: 2px;
  overflow: hidden;
}

.metric-fill {
  height: 100%;
  border-radius: 2px;
  transition: width 0.6s ease;
}

/* Charts */
.charts-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

@media (max-width: 800px) { .charts-grid { grid-template-columns: 1fr; } }

.chart-card {
  background: var(--color-bg-secondary);
  border: 1px solid var(--color-border);
  border-radius: var(--rounded-lg);
  padding: 18px 20px;
}

.chart-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.chart-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-primary);
}

.chart-legend {
  display: flex;
  gap: 12px;
}

.leg-item {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 11px;
  color: var(--color-text-secondary);
}

.leg-dot {
  width: 7px; height: 7px;
  border-radius: 50%;
}

.chart-wrap {
  max-height: 240px;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* Offenders */
.offenders-card {
  background: var(--color-bg-secondary);
  border: 1px solid var(--color-border);
  border-radius: var(--rounded-lg);
  overflow: hidden;
}

.offenders-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 18px;
  border-bottom: 1px solid var(--color-border);
}

.offenders-sub {
  font-size: 12px;
  color: var(--color-text-tertiary);
}

.offenders-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  padding: 48px;
  color: var(--color-text-tertiary);
  font-size: 13px;
}

.offender-row {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 12px 18px;
  border-bottom: 1px solid var(--color-border-subtle);
  cursor: pointer;
  transition: background 150ms;
}

.offender-row:last-child { border-bottom: none; }
.offender-row:hover { background: var(--color-bg-tertiary); }
.offender-row:hover .offender-arrow { color: var(--color-accent-primary); }

.offender-rank {
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--color-text-tertiary);
  width: 28px;
  flex-shrink: 0;
}

.offender-info { flex: 1; min-width: 0; }

.offender-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-accent-hover);
  font-family: var(--font-mono);
  margin-bottom: 2px;
}

.offender-row:hover .offender-name { text-decoration: underline; }

.offender-path {
  font-size: 11px;
  color: var(--color-text-tertiary);
  font-family: var(--font-mono);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.offender-scores {
  display: flex;
  gap: 20px;
  flex-shrink: 0;
}

.score-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
}

.score-label {
  font-size: 10px;
  color: var(--color-text-tertiary);
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.score-val {
  font-family: var(--font-mono);
  font-size: 15px;
  font-weight: 700;
  color: var(--color-text-primary);
}

.score-val.ai-col { color: var(--color-category-ai); }

.offender-arrow {
  color: var(--color-text-tertiary);
  flex-shrink: 0;
  transition: color 150ms;
}

/* Buttons */
.btn-primary {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 9px 16px;
  background: var(--color-accent-primary);
  color: white;
  border-radius: var(--rounded-base);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  border: none;
  transition: all 150ms;
}
.btn-primary:hover {
  background: var(--color-accent-hover);
  box-shadow: 0 0 20px rgba(56,139,253,0.25);
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to   { transform: rotate(360deg); }
}
</style>
