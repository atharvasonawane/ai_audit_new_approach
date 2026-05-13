<template>
  <div class="flex flex-col h-full overflow-auto">
    <!-- Loading State -->
    <div v-if="loading" class="flex items-center justify-center h-full">
      <div class="text-center">
        <Loader2 
          :size="48" 
          :stroke-width="2" 
          class="animate-spin text-accent-primary mx-auto mb-4"
        />
        <p class="text-text-secondary text-base">Loading dashboard...</p>
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
        <p class="text-text-primary font-semibold mb-2">Failed to load dashboard</p>
        <p class="text-text-secondary text-sm mb-4">{{ error }}</p>
        <button
          @click="fetchDashboardData"
          class="retry-button"
        >
          <RefreshCw :size="16" :stroke-width="2" />
          <span>Retry</span>
        </button>
      </div>
    </div>

    <!-- Dashboard Content -->
    <div v-else class="px-6 py-6 space-y-8">
      <!-- Header -->
      <div class="flex items-center justify-between">
        <div>
          <h1 class="text-3xl font-bold text-text-primary">
            {{ summary.project_name || 'Code Audit Dashboard' }}
          </h1>
          <p class="text-text-secondary text-sm mt-1">
            Last scan completed
          </p>
        </div>
        <button class="re-audit-button">
          <RefreshCw :size="16" :stroke-width="2" />
          <span>Re-Audit</span>
        </button>
      </div>

      <!-- Executive Synthesis Panel -->
      <div class="executive-synthesis-panel">
        <h2 class="panel-title">Executive Synthesis</h2>
        <p class="synthesis-text">
          {{ executiveSummary.synthesis_text || 'No executive summary available. Run the full audit pipeline first.' }}
        </p>
      </div>

      <!-- Metrics Grid -->
      <div class="metrics-grid">
        <div class="metric-card">
          <div class="metric-label">TOTAL FILES</div>
          <div class="metric-value">{{ summary.total_files || 0 }}</div>
        </div>
        <div class="metric-card">
          <div class="metric-label">TOTAL ISSUES</div>
          <div class="metric-value">{{ summary.ai_issues_total || 0 }}</div>
        </div>
        <div class="metric-card">
          <div class="metric-label">ESLINT FLAGS</div>
          <div class="metric-value">{{ summary.total_eslint_flags || 0 }}</div>
        </div>
        <div class="metric-card">
          <div class="metric-label">A11Y DEFECTS</div>
          <div class="metric-value">{{ summary.total_accessibility_defects || 0 }}</div>
        </div>
        <div class="metric-card">
          <div class="metric-label">AVG COMPLEXITY</div>
          <div class="metric-value">{{ summary.average_complexity || 0 }}</div>
        </div>
        <div class="metric-card">
          <div class="metric-label">HIGH SEVERITY</div>
          <div class="metric-value severity-high">{{ summary.ai_issues_by_severity?.High || 0 }}</div>
        </div>
      </div>

      <!-- Charts Section -->
      <div class="charts-grid">
        <!-- Severity Pie Chart -->
        <div class="chart-card">
          <h3 class="chart-title">Issues by Severity</h3>
          <div class="chart-container">
            <Doughnut :data="severityChartData" :options="severityChartOptions" />
          </div>
        </div>

        <!-- Category Bar Chart -->
        <div class="chart-card">
          <h3 class="chart-title">Issues by Category</h3>
          <div class="chart-container">
            <Bar :data="categoryChartData" :options="categoryChartOptions" />
          </div>
        </div>
      </div>

      <!-- Worst Offenders Panel -->
      <div class="worst-offenders-panel">
        <h2 class="panel-title">Worst Offenders</h2>
        <div v-if="worstOffenders.length === 0" class="empty-state">
          <FileSearch :size="48" :stroke-width="1.5" class="text-text-tertiary mx-auto mb-3" />
          <p class="text-text-secondary">No files analyzed yet</p>
        </div>
        <div v-else class="offenders-list">
          <div
            v-for="(file, index) in worstOffenders"
            :key="index"
            class="offender-row"
            @click="navigateToFile(file.file_path)"
          >
            <div class="offender-rank">{{ index + 1 }}</div>
            <div class="offender-info">
              <div class="offender-filename">{{ getFileName(file.file_path) }}</div>
              <div class="offender-path">{{ file.file_path }}</div>
            </div>
            <div class="offender-metrics">
              <div class="metric-badge">
                <span class="metric-badge-label">Issues</span>
                <span class="metric-badge-value">{{ file.composite_score || 0 }}</span>
              </div>
              <div class="metric-badge">
                <span class="metric-badge-label">ESLint</span>
                <span class="metric-badge-value">{{ file.eslint_flag_count || 0 }}</span>
              </div>
              <div class="metric-badge">
                <span class="metric-badge-label">AI</span>
                <span class="metric-badge-value">{{ file.ai_issue_count || 0 }}</span>
              </div>
            </div>
            <ChevronRight :size="20" :stroke-width="2" class="offender-arrow" />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { 
  Loader2, 
  AlertCircle, 
  RefreshCw,
  FileSearch,
  ChevronRight
} from 'lucide-vue-next'
import { filesAPI } from '../api.js'
import {
  Chart as ChartJS,
  Title,
  Tooltip,
  Legend,
  ArcElement,
  BarElement,
  CategoryScale,
  LinearScale
} from 'chart.js'
import { Doughnut, Bar } from 'vue-chartjs'

// Register Chart.js components
ChartJS.register(
  Title,
  Tooltip,
  Legend,
  ArcElement,
  BarElement,
  CategoryScale,
  LinearScale
)

const router = useRouter()

// State
const loading = ref(false)
const error = ref(null)
const summary = ref({})
const executiveSummary = ref({})
const worstOffenders = ref([])

// Severity Chart Data
const severityChartData = computed(() => {
  const severities = summary.value.ai_issues_by_severity || {}
  return {
    labels: ['High', 'Medium', 'Low'],
    datasets: [{
      data: [
        severities.High || 0,
        severities.Medium || 0,
        severities.Low || 0
      ],
      backgroundColor: [
        '#FF8A00', // High - orange
        '#FFB800', // Medium - amber
        '#4ADE80'  // Low - green
      ],
      borderWidth: 0
    }]
  }
})

const severityChartOptions = {
  responsive: true,
  maintainAspectRatio: true,
  plugins: {
    legend: {
      position: 'bottom',
      labels: {
        color: '#A8A8A8',
        font: {
          size: 12,
          family: 'Inter, system-ui, sans-serif'
        },
        padding: 16
      }
    },
    tooltip: {
      backgroundColor: '#1A1A1A',
      titleColor: '#FFFFFF',
      bodyColor: '#A8A8A8',
      borderColor: '#2D2D2D',
      borderWidth: 1,
      padding: 12,
      displayColors: true
    }
  }
}

// Category Chart Data
const categoryChartData = computed(() => {
  return {
    labels: ['AI Issues', 'ESLint', 'Accessibility'],
    datasets: [{
      label: 'Issues',
      data: [
        summary.value.ai_issues_total || 0,
        summary.value.total_eslint_flags || 0,
        summary.value.total_accessibility_defects || 0
      ],
      backgroundColor: [
        '#A78BFA', // AI - purple
        '#34D399', // ESLint - teal
        '#FBBF24'  // Accessibility - amber
      ],
      borderWidth: 0,
      borderRadius: 4
    }]
  }
})

const categoryChartOptions = {
  responsive: true,
  maintainAspectRatio: true,
  scales: {
    y: {
      beginAtZero: true,
      ticks: {
        color: '#A8A8A8',
        font: {
          size: 11,
          family: 'Inter, system-ui, sans-serif'
        }
      },
      grid: {
        color: '#2D2D2D',
        drawBorder: false
      }
    },
    x: {
      ticks: {
        color: '#A8A8A8',
        font: {
          size: 11,
          family: 'Inter, system-ui, sans-serif'
        }
      },
      grid: {
        display: false
      }
    }
  },
  plugins: {
    legend: {
      display: false
    },
    tooltip: {
      backgroundColor: '#1A1A1A',
      titleColor: '#FFFFFF',
      bodyColor: '#A8A8A8',
      borderColor: '#2D2D2D',
      borderWidth: 1,
      padding: 12
    }
  }
}

// Methods
const fetchDashboardData = async () => {
  loading.value = true
  error.value = null
  
  try {
    // Fetch all data in parallel
    const [summaryRes, executiveRes, offendersRes] = await Promise.all([
      filesAPI.getSummary(),
      filesAPI.getExecutiveSummary(),
      filesAPI.getWorstOffenders(10)
    ])
    
    summary.value = summaryRes.data || {}
    executiveSummary.value = executiveRes.data || {}
    worstOffenders.value = offendersRes.data || []
    
    console.log('Dashboard data loaded:', {
      summary: summary.value,
      executiveSummary: executiveSummary.value,
      worstOffenders: worstOffenders.value.length
    })
  } catch (err) {
    console.error('Error fetching dashboard data:', err)
    
    if (err.code === 'ERR_NETWORK' || err.message.includes('Network Error')) {
      error.value = 'Cannot connect to API server. Please ensure Flask is running on http://localhost:5000'
    } else if (err.response?.status === 404) {
      error.value = 'API endpoint not found. Please check the Flask server configuration.'
    } else if (err.response?.status >= 500) {
      error.value = 'Server error. Please check the Flask server logs.'
    } else {
      error.value = err.message || 'An unexpected error occurred'
    }
  } finally {
    loading.value = false
  }
}

const getFileName = (filePath) => {
  if (!filePath) return ''
  const parts = filePath.split('/')
  return parts[parts.length - 1]
}

const navigateToFile = (filePath) => {
  router.push({ path: '/audit', query: { file: filePath } })
}

// Lifecycle
onMounted(() => {
  fetchDashboardData()
})
</script>

<style scoped>
/* Header */
.re-audit-button {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  background-color: var(--color-accent-primary);
  color: #FFFFFF;
  border-radius: var(--rounded-base);
  font-size: var(--text-sm);
  font-weight: 600;
  cursor: pointer;
  transition: all 200ms ease-out;
}

.re-audit-button:hover {
  background-color: var(--color-accent-hover);
}

/* Executive Synthesis Panel */
.executive-synthesis-panel {
  background-color: var(--color-bg-secondary);
  border: 1px solid var(--color-border);
  border-left: 4px solid var(--color-accent-secondary);
  border-radius: var(--rounded-lg);
  padding: 24px;
}

.panel-title {
  font-size: var(--text-lg);
  font-weight: 600;
  color: var(--color-text-primary);
  margin-bottom: 12px;
}

.synthesis-text {
  font-size: var(--text-base);
  line-height: var(--leading-relaxed);
  color: var(--color-text-secondary);
}

/* Metrics Grid */
.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 16px;
}

.metric-card {
  background-color: var(--color-bg-secondary);
  border: 1px solid var(--color-border);
  border-radius: var(--rounded-lg);
  padding: 20px;
  transition: all 200ms ease-out;
}

.metric-card:hover {
  border-color: var(--color-accent-primary);
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.metric-label {
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
  font-weight: 600;
  letter-spacing: var(--tracking-wide);
  text-transform: uppercase;
  margin-bottom: 8px;
}

.metric-value {
  font-size: var(--text-3xl);
  font-weight: 700;
  color: var(--color-text-primary);
  font-family: var(--font-mono);
  line-height: var(--leading-tight);
}

.metric-value.severity-high {
  color: var(--color-severity-high);
}

/* Charts Grid */
.charts-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 24px;
}

.chart-card {
  background-color: var(--color-bg-secondary);
  border: 1px solid var(--color-border);
  border-radius: var(--rounded-lg);
  padding: 24px;
}

.chart-title {
  font-size: var(--text-base);
  font-weight: 600;
  color: var(--color-text-primary);
  margin-bottom: 20px;
}

.chart-container {
  position: relative;
  height: 280px;
}

/* Worst Offenders Panel */
.worst-offenders-panel {
  background-color: var(--color-bg-secondary);
  border: 1px solid var(--color-border);
  border-radius: var(--rounded-lg);
  padding: 24px;
}

.offenders-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.offender-row {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px;
  background-color: var(--color-bg-primary);
  border: 1px solid var(--color-border);
  border-radius: var(--rounded-base);
  cursor: pointer;
  transition: all 200ms ease-out;
}

.offender-row:hover {
  border-color: var(--color-accent-primary);
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.offender-rank {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  background-color: var(--color-bg-tertiary);
  border-radius: var(--rounded-full);
  font-size: var(--text-sm);
  font-weight: 700;
  color: var(--color-text-primary);
  font-family: var(--font-mono);
  flex-shrink: 0;
}

.offender-info {
  flex: 1;
  min-width: 0;
}

.offender-filename {
  font-size: var(--text-base);
  font-weight: 600;
  color: var(--color-text-primary);
  font-family: var(--font-mono);
  margin-bottom: 4px;
}

.offender-path {
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
  font-family: var(--font-mono);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.offender-metrics {
  display: flex;
  gap: 12px;
  flex-shrink: 0;
}

.metric-badge {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 8px 12px;
  background-color: var(--color-bg-tertiary);
  border-radius: var(--rounded-base);
}

.metric-badge-label {
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: var(--tracking-wide);
}

.metric-badge-value {
  font-size: var(--text-lg);
  font-weight: 700;
  color: var(--color-text-primary);
  font-family: var(--font-mono);
}

.offender-arrow {
  color: var(--color-text-tertiary);
  flex-shrink: 0;
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
