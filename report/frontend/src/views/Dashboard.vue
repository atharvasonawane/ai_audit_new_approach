<template>
  <div class="h-full overflow-y-auto">
    <!-- Loading State -->
    <div v-if="loading" class="h-full flex items-center justify-center p-10">
      <div class="text-center">
        <div class="w-10 h-10 border-4 border-slate-200/10 border-t-blue-500 rounded-full animate-spin mx-auto mb-4"></div>
        <p class="text-sm text-gray-500 dark:text-gray-400">Loading dashboard...</p>
      </div>
    </div>

    <!-- Error State -->
    <div v-else-if="error" class="h-full flex items-center justify-center p-10">
      <div class="bg-red-50 dark:bg-red-900/10 border border-red-200 dark:border-red-900/30 rounded-xl p-8 text-center max-w-[400px] flex flex-col items-center gap-4 text-red-500">
        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <circle cx="12" cy="12" r="10"/>
          <line x1="12" y1="8" x2="12" y2="12"/>
          <line x1="12" y1="16" x2="12.01" y2="16"/>
        </svg>
        <h3 class="text-base font-semibold text-gray-900 dark:text-gray-100">Failed to load dashboard</h3>
        <p class="text-sm text-gray-600 dark:text-gray-300">{{ error }}</p>
        <button class="inline-flex items-center gap-2 px-4 py-2.5 bg-gradient-to-br from-blue-500 to-blue-600 text-white rounded-lg text-[13px] font-semibold transition-all duration-200 shadow-[0_4px_12px_rgba(59,130,246,0.2)] hover:from-blue-600 hover:to-blue-700 hover:shadow-[0_6px_20px_rgba(59,130,246,0.3)] hover:-translate-y-[1px]" @click="fetchDashboardData">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M1 4s1-3 7-3a7 7 0 010 14c-3 0-5.5-1.5-6.5-4"/>
            <path d="M1 1v3h3"/>
          </svg>
          Retry
        </button>
      </div>
    </div>

    <!-- Dashboard Content -->
    <div v-else class="p-8 max-w-[1400px] mx-auto flex flex-col gap-8">
      <!-- Header -->
      <div class="flex items-start justify-between gap-6">
        <div class="flex-1">
          <div class="inline-flex items-center gap-2 px-3 py-1.5 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-900/30 rounded-md text-xs font-semibold text-blue-500 mb-3">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>
            </svg>
            {{ summary.project_name || 'Unknown Project' }}
          </div>
          <h1 class="text-[32px] font-extrabold text-gray-900 dark:text-gray-50 tracking-[-0.02em] mb-2">Audit Dashboard</h1>
          <p class="text-sm text-gray-500 dark:text-gray-400">Comprehensive analysis of your codebase quality and health</p>
        </div>
        <button class="inline-flex items-center gap-2 px-4 py-2.5 bg-gradient-to-br from-blue-500 to-blue-600 text-white rounded-lg text-[13px] font-semibold transition-all duration-200 shadow-[0_4px_12px_rgba(59,130,246,0.2)] hover:from-blue-600 hover:to-blue-700 hover:shadow-[0_6px_20px_rgba(59,130,246,0.3)] hover:-translate-y-[1px]" @click="fetchDashboardData">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M1 4s1-3 7-3a7 7 0 010 14c-3 0-5.5-1.5-6.5-4"/>
            <path d="M1 1v3h3"/>
          </svg>
          Re-Audit
        </button>
      </div>

      <!-- Executive Summary -->
      <div v-if="executiveSummary.synthesis_text" class="bg-blue-50/50 dark:bg-blue-900/10 border border-blue-100 dark:border-blue-800/30 rounded-xl px-6 py-5">
        <div class="flex items-center gap-2 text-[11px] font-bold text-blue-500 tracking-[0.08em] uppercase mb-3">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10"/>
            <polyline points="12 6 12 12 16 14"/>
          </svg>
          Executive Summary
        </div>
        <p class="text-sm text-gray-700 dark:text-gray-300 leading-relaxed max-h-[120px] overflow-y-auto">{{ executiveSummary.synthesis_text }}</p>
      </div>

      <!-- Metrics Grid -->
      <div class="grid grid-cols-[repeat(auto-fit,minmax(200px,1fr))] gap-4">
        <div class="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 shadow-sm rounded-xl p-6 transition-all duration-300 border-t-2 border-t-indigo-500 cursor-default hover:border-gray-300 dark:hover:border-gray-700 hover:shadow-md hover:-translate-y-0.5">
          <div class="flex items-center justify-between mb-4">
            <span class="text-[11px] font-bold text-gray-500 dark:text-gray-400 tracking-[0.08em] uppercase">Total Files</span>
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" class="opacity-50">
              <path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/>
              <polyline points="13 2 13 9 20 9"/>
            </svg>
          </div>
          <div class="text-[32px] font-extrabold text-gray-900 dark:text-gray-50 tracking-tighter leading-none mb-3 font-mono">{{ summary.total_files || 0 }}</div>
          <div class="flex items-center gap-2">
            <div class="flex-1 h-1 bg-slate-200 dark:bg-slate-800 rounded-sm overflow-hidden">
              <div class="h-full rounded-sm transition-all duration-700" style="width:65%; background:linear-gradient(90deg, #3b82f6, #60a5fa);"></div>
            </div>
          </div>
        </div>

        <div class="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 shadow-sm rounded-xl p-6 transition-all duration-300 border-t-2 border-t-indigo-500 cursor-default hover:border-gray-300 dark:hover:border-gray-700 hover:shadow-md hover:-translate-y-0.5">
          <div class="flex items-center justify-between mb-4">
            <span class="text-[11px] font-bold text-gray-500 dark:text-gray-400 tracking-[0.08em] uppercase">Total Issues</span>
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" class="opacity-50">
              <circle cx="12" cy="12" r="10"/>
              <line x1="12" y1="8" x2="12" y2="12"/>
              <line x1="12" y1="16" x2="12.01" y2="16"/>
            </svg>
          </div>
          <div class="text-[32px] font-extrabold text-red-500 tracking-tighter leading-none mb-3 font-mono">{{ summary.ai_issues_total || 0 }}</div>
          <div class="flex items-center gap-2">
            <div class="flex-1 h-1 bg-slate-200 dark:bg-slate-800 rounded-sm overflow-hidden">
              <div class="h-full rounded-sm transition-all duration-700" style="width:48%; background:linear-gradient(90deg, #ef4444, #f87171);"></div>
            </div>
          </div>
        </div>

        <div class="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 shadow-sm rounded-xl p-6 transition-all duration-300 border-t-2 border-t-indigo-500 cursor-default hover:border-gray-300 dark:hover:border-gray-700 hover:shadow-md hover:-translate-y-0.5">
          <div class="flex items-center justify-between mb-4">
            <span class="text-[11px] font-bold text-gray-500 dark:text-gray-400 tracking-[0.08em] uppercase">ESLint Flags</span>
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" class="opacity-50">
              <polyline points="22 12 18 12 15 20 9 4 6 12 2 12"/>
            </svg>
          </div>
          <div class="text-[32px] font-extrabold text-emerald-500 tracking-tighter leading-none mb-3 font-mono">{{ summary.total_eslint_flags || 0 }}</div>
          <div class="flex items-center gap-2">
            <div class="flex-1 h-1 bg-slate-200 dark:bg-slate-800 rounded-sm overflow-hidden">
              <div class="h-full rounded-sm transition-all duration-700" style="width:55%; background:linear-gradient(90deg, #10b981, #34d399);"></div>
            </div>
          </div>
        </div>

        <div class="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 shadow-sm rounded-xl p-6 transition-all duration-300 border-t-2 border-t-indigo-500 cursor-default hover:border-gray-300 dark:hover:border-gray-700 hover:shadow-md hover:-translate-y-0.5">
          <div class="flex items-center justify-between mb-4">
            <span class="text-[11px] font-bold text-gray-500 dark:text-gray-400 tracking-[0.08em] uppercase">A11y Defects</span>
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" class="opacity-50">
              <circle cx="12" cy="12" r="10"/>
              <path d="M8 14s1.5 2 4 2 4-2 4-2M9 9h.01M15 9h.01"/>
            </svg>
          </div>
          <div class="text-[32px] font-extrabold text-amber-500 tracking-tighter leading-none mb-3 font-mono">{{ summary.total_accessibility_defects || 0 }}</div>
          <div class="flex items-center gap-2">
            <div class="flex-1 h-1 bg-slate-200 dark:bg-slate-800 rounded-sm overflow-hidden">
              <div class="h-full rounded-sm transition-all duration-700" style="width:80%; background:linear-gradient(90deg, #f59e0b, #fbbf24);"></div>
            </div>
          </div>
        </div>

        <div class="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 shadow-sm rounded-xl p-6 transition-all duration-300 border-t-2 border-t-indigo-500 cursor-default hover:border-gray-300 dark:hover:border-gray-700 hover:shadow-md hover:-translate-y-0.5">
          <div class="flex items-center justify-between mb-4">
            <span class="text-[11px] font-bold text-gray-500 dark:text-gray-400 tracking-[0.08em] uppercase">Avg Complexity</span>
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" class="opacity-50">
              <polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/>
              <polyline points="17 6 23 6 23 12"/>
            </svg>
          </div>
          <div class="text-[32px] font-extrabold text-gray-900 dark:text-gray-50 tracking-tighter leading-none mb-3 font-mono">{{ summary.average_complexity || 0 }}</div>
          <div class="flex items-center gap-2">
            <div class="flex-1 h-1 bg-slate-200 dark:bg-slate-800 rounded-sm overflow-hidden">
              <div class="h-full rounded-sm transition-all duration-700" style="width:30%; background:linear-gradient(90deg, #a78bfa, #c4b5fd);"></div>
            </div>
          </div>
        </div>

        <div class="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 shadow-sm rounded-xl p-6 transition-all duration-300 border-t-2 border-t-indigo-500 cursor-default hover:border-gray-300 dark:hover:border-gray-700 hover:shadow-md hover:-translate-y-0.5">
          <div class="flex items-center justify-between mb-4">
            <span class="text-[11px] font-bold text-gray-500 dark:text-gray-400 tracking-[0.08em] uppercase">High Severity</span>
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" class="opacity-50">
              <path d="M12 2L2 20h20L12 2z"/>
              <line x1="12" y1="9" x2="12" y2="13"/>
              <line x1="12" y1="17" x2="12.01" y2="17"/>
            </svg>
          </div>
          <div class="text-[32px] font-extrabold text-red-500 tracking-tighter leading-none mb-3 font-mono">{{ summary.ai_issues_by_severity?.High || 0 }}</div>
          <div class="flex items-center gap-2">
            <div class="flex-1 h-1 bg-slate-200 dark:bg-slate-800 rounded-sm overflow-hidden">
              <div class="h-full rounded-sm transition-all duration-700" style="width:25%; background:linear-gradient(90deg, #ff6b6b, #ff8787);"></div>
            </div>
          </div>
        </div>
      </div>

      <!-- Detailed Breakdowns -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mt-4">
        <!-- Severity Breakdown -->
        <div class="p-6 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl shadow-sm transition-all duration-300 hover:border-gray-300 dark:hover:border-gray-700">
          <h3 class="text-sm font-bold text-gray-900 dark:text-gray-50 mb-6 tracking-tight">Issues by Severity</h3>
          <div class="space-y-5">
            <div>
              <div class="flex justify-between text-xs mb-2">
                <span class="font-bold text-rose-500 tracking-wide uppercase text-[10px]">High</span>
                <span class="text-gray-500 font-mono">{{ summary.ai_issues_by_severity?.High || 0 }}</span>
              </div>
              <div class="h-1 w-full bg-gray-100 dark:bg-gray-800 rounded-full overflow-hidden">
                <div class="h-full bg-rose-500 rounded-full transition-all duration-1000" :style="{ width: getPercentage(summary.ai_issues_by_severity?.High) + '%' }"></div>
              </div>
            </div>
            <div>
              <div class="flex justify-between text-xs mb-2">
                <span class="font-bold text-amber-500 tracking-wide uppercase text-[10px]">Medium</span>
                <span class="text-gray-500 font-mono">{{ summary.ai_issues_by_severity?.Medium || 0 }}</span>
              </div>
              <div class="h-1 w-full bg-gray-100 dark:bg-gray-800 rounded-full overflow-hidden">
                <div class="h-full bg-amber-500 rounded-full transition-all duration-1000" :style="{ width: getPercentage(summary.ai_issues_by_severity?.Medium) + '%' }"></div>
              </div>
            </div>
            <div>
              <div class="flex justify-between text-xs mb-2">
                <span class="font-bold text-emerald-500 tracking-wide uppercase text-[10px]">Low</span>
                <span class="text-gray-500 font-mono">{{ summary.ai_issues_by_severity?.Low || 0 }}</span>
              </div>
              <div class="h-1 w-full bg-gray-100 dark:bg-gray-800 rounded-full overflow-hidden">
                <div class="h-full bg-emerald-500 rounded-full transition-all duration-1000" :style="{ width: getPercentage(summary.ai_issues_by_severity?.Low) + '%' }"></div>
              </div>
            </div>
          </div>
        </div>

        <!-- Category Breakdown -->
        <div class="p-6 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl shadow-sm transition-all duration-300 hover:border-gray-300 dark:hover:border-gray-700">
          <h3 class="text-sm font-bold text-gray-900 dark:text-gray-50 mb-6 tracking-tight">Issues by Category</h3>
          <div class="space-y-5">
            <div>
              <div class="flex justify-between text-xs mb-2">
                <span class="font-bold text-indigo-500 tracking-wide uppercase text-[10px]">AI Issues</span>
                <span class="text-gray-500 font-mono">{{ summary.ai_issues_total || 0 }}</span>
              </div>
              <div class="h-1 w-full bg-gray-100 dark:bg-gray-800 rounded-full overflow-hidden">
                <div class="h-full bg-indigo-500 rounded-full transition-all duration-1000" :style="{ width: getCategoryPercentage(summary.ai_issues_total) + '%' }"></div>
              </div>
            </div>
            <div>
              <div class="flex justify-between text-xs mb-2">
                <span class="font-bold text-teal-500 tracking-wide uppercase text-[10px]">ESLint Flags</span>
                <span class="text-gray-500 font-mono">{{ summary.total_eslint_flags || 0 }}</span>
              </div>
              <div class="h-1 w-full bg-gray-100 dark:bg-gray-800 rounded-full overflow-hidden">
                <div class="h-full bg-teal-500 rounded-full transition-all duration-1000" :style="{ width: getCategoryPercentage(summary.total_eslint_flags) + '%' }"></div>
              </div>
            </div>
            <div>
              <div class="flex justify-between text-xs mb-2">
                <span class="font-bold text-orange-500 tracking-wide uppercase text-[10px]">Accessibility</span>
                <span class="text-gray-500 font-mono">{{ summary.total_accessibility_defects || 0 }}</span>
              </div>
              <div class="h-1 w-full bg-gray-100 dark:bg-gray-800 rounded-full overflow-hidden">
                <div class="h-full bg-orange-500 rounded-full transition-all duration-1000" :style="{ width: getCategoryPercentage(summary.total_accessibility_defects) + '%' }"></div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Worst Offenders -->
      <div class="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 shadow-sm rounded-xl transition-all duration-300 overflow-hidden hover:border-gray-300 dark:hover:border-gray-700">
        <div class="px-6 py-5 border-b border-gray-100 dark:border-gray-800/50">
          <div>
            <h3 class="text-[14px] font-bold text-gray-900 dark:text-gray-50 m-0 mb-1">Worst Offenders</h3>
            <p class="text-[12px] text-gray-400 dark:text-gray-500 m-0">Files with the most code quality issues</p>
          </div>
        </div>

        <div v-if="worstOffenders.length === 0" class="flex flex-col items-center justify-center gap-3 py-16 px-8 text-gray-500 text-sm text-center">
          <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1" class="opacity-25">
            <circle cx="11" cy="11" r="8"/>
            <path d="M21 21l-4.35-4.35"/>
          </svg>
          <p>No data available yet</p>
        </div>

        <div v-else class="flex flex-col max-h-[400px] overflow-y-auto">
          <div
            v-for="(file, i) in worstOffenders"
            :key="i"
            class="group flex items-center gap-4 px-6 py-4 border-b border-gray-100 dark:border-gray-800/50 cursor-pointer transition-colors duration-200 hover:bg-blue-50/50 dark:hover:bg-blue-900/10 last:border-b-0"
            @click="navigateToFile(file.file_path)"
          >
            <div class="font-mono text-xs text-gray-400 dark:text-gray-500 w-8 shrink-0 font-semibold">#{{ i + 1 }}</div>
            <div class="flex-1 min-w-0">
              <div class="text-[13px] font-bold text-gray-800 dark:text-gray-200 font-mono mb-0.5 overflow-hidden text-ellipsis whitespace-nowrap group-hover:text-blue-500">{{ getFileName(file.file_path) }}</div>
              <div class="text-[11px] text-gray-400 dark:text-gray-500 font-mono whitespace-nowrap overflow-hidden text-ellipsis">{{ file.file_path }}</div>
            </div>
            <div class="flex gap-5 shrink-0">
              <div class="flex flex-col items-center gap-0.5 text-center">
                <span class="text-[9px] text-gray-400 font-bold tracking-[0.05em] uppercase">Issues</span>
                <span class="font-mono text-base font-bold text-gray-900 dark:text-gray-100">{{ file.composite_score || 0 }}</span>
              </div>
              <div class="flex flex-col items-center gap-0.5 text-center">
                <span class="text-[9px] text-gray-400 font-bold tracking-[0.05em] uppercase">ESLint</span>
                <span class="font-mono text-base font-bold text-gray-900 dark:text-gray-100">{{ file.eslint_flag_count || 0 }}</span>
              </div>
              <div class="flex flex-col items-center gap-0.5 text-center">
                <span class="text-[9px] text-gray-400 font-bold tracking-[0.05em] uppercase">AI</span>
                <span class="font-mono text-base font-bold text-purple-500 dark:text-purple-400">{{ file.ai_issue_count || 0 }}</span>
              </div>
            </div>
            <svg class="text-gray-300 dark:text-gray-600 shrink-0 transition-colors duration-200 group-hover:text-blue-500" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="9 18 15 12 9 6"/>
            </svg>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { filesAPI } from '../api.js'

const router = useRouter()
const loading = ref(false)
const error = ref(null)
const summary = ref({})
const executiveSummary = ref({})
const worstOffenders = ref([])

const getPercentage = (val) => {
  const total = (summary.value.ai_issues_by_severity?.High || 0) + 
                (summary.value.ai_issues_by_severity?.Medium || 0) + 
                (summary.value.ai_issues_by_severity?.Low || 0)
  if (total === 0) return 0
  return Math.round((val || 0) / total * 100)
}

const getCategoryPercentage = (val) => {
  const total = (summary.value.ai_issues_total || 0) + 
                (summary.value.total_eslint_flags || 0) + 
                (summary.value.total_accessibility_defects || 0)
  if (total === 0) return 0
  return Math.round((val || 0) / total * 100)
}

const fetchDashboardData = async () => {
  loading.value = true; error.value = null
  try {
    const [summaryRes, executiveRes, offendersRes] = await Promise.all([
      filesAPI.getSummary(), filesAPI.getExecutiveSummary(), filesAPI.getWorstOffenders(10)
    ])
    summary.value = summaryRes.data || {}
    executiveSummary.value = executiveRes.data || {}
    worstOffenders.value = offendersRes.data || []
  } catch (err) {
    if (err.code === 'ERR_NETWORK' || err.message?.includes('Network Error')) {
      const port = window.__FLASK_PORT__ || 5000;
      error.value = `Cannot connect to API server. Ensure Flask is running on http://localhost:${port}`
    } else {
      error.value = err.message || 'An unexpected error occurred'
    }
  } finally { loading.value = false }
}

const getFileName = (p) => p ? p.split('/').pop() : ''
const navigateToFile = (p) => router.push({ path: '/audit', query: { file: p } })

onMounted(fetchDashboardData)
</script>
