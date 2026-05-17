<template>
  <div class="flex flex-col h-full overflow-hidden bg-white dark:bg-gray-950">
    <!-- Loading -->
    <div v-if="loading" class="flex flex-col items-center justify-center gap-4 py-16 px-10 text-center flex-1 text-gray-500 dark:text-gray-400 text-[13px]">
      <div class="w-8 h-8 border-[3px] border-gray-200 dark:border-gray-800 border-t-blue-500 rounded-full animate-spin"></div>
      <p>Loading file details...</p>
    </div>

    <!-- Error -->
    <div v-else-if="error" class="flex flex-col items-center justify-center gap-4 py-16 px-10 text-center flex-1 text-gray-500 dark:text-gray-400 text-[13px]">
      <svg class="text-red-500" width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <circle cx="12" cy="12" r="10"/>
        <line x1="12" y1="8" x2="12" y2="12"/>
        <line x1="12" y1="16" x2="12.01" y2="16"/>
      </svg>
      <p class="leading-relaxed max-w-[350px]">{{ error }}</p>
      <button class="px-4 py-2 bg-blue-500/15 text-blue-600 dark:text-blue-400 border border-blue-500/30 rounded-lg text-[12px] font-semibold cursor-pointer transition-all duration-200 mt-2 hover:bg-blue-500/25 hover:border-blue-500/50" @click="fetchFileData">Retry</button>
    </div>

    <!-- Content -->
    <div v-else class="flex flex-col min-h-0 flex-1 overflow-hidden">
      <!-- File Header -->
      <div class="flex items-center justify-between gap-6 py-5 px-6 bg-gray-50 dark:bg-gray-900/50 border-b border-gray-200 dark:border-gray-800 shrink-0">
        <div class="flex items-center gap-3 flex-1 min-w-0">
          <div class="flex items-center gap-1.5 px-2.5 py-1.5 bg-blue-500/10 border border-blue-500/20 rounded-md text-[11px] font-bold text-blue-500 shrink-0">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/>
              <polyline points="13 2 13 9 20 9"/>
            </svg>
            Vue
          </div>
          <div class="min-w-0">
            <div class="text-[14px] font-bold text-gray-900 dark:text-gray-100 font-mono overflow-hidden text-ellipsis whitespace-nowrap">{{ fileName }}</div>
            <div class="text-[11px] text-gray-500 dark:text-gray-400 font-mono overflow-hidden text-ellipsis whitespace-nowrap mt-0.5">{{ filePath }}</div>
          </div>
        </div>
        <div class="flex gap-2 shrink-0">
          <div class="flex flex-col items-center justify-center gap-0.5 px-3 py-2 rounded-lg min-w-[48px]" :class="aiIssues.length > 0 ? 'bg-purple-100 dark:bg-purple-500/10' : 'bg-emerald-100/50 dark:bg-emerald-500/10'">
            <div class="font-mono text-[16px] font-bold leading-none" :class="aiIssues.length > 0 ? 'text-purple-500' : 'text-emerald-500'">{{ aiIssues.length }}</div>
            <div class="text-[8px] font-bold tracking-[0.08em] uppercase" :class="aiIssues.length > 0 ? 'text-purple-600/70 dark:text-purple-400/70' : 'text-emerald-600/60 dark:text-emerald-400/60'">AI</div>
          </div>
          <div class="flex flex-col items-center justify-center gap-0.5 px-3 py-2 rounded-lg min-w-[48px]" :class="eslintFlags.length > 0 ? 'bg-emerald-100 dark:bg-emerald-500/10' : 'bg-emerald-100/50 dark:bg-emerald-500/10'">
            <div class="font-mono text-[16px] font-bold leading-none text-emerald-500">{{ eslintFlags.length }}</div>
            <div class="text-[8px] font-bold tracking-[0.08em] uppercase" :class="eslintFlags.length > 0 ? 'text-emerald-600/70 dark:text-emerald-400/70' : 'text-emerald-600/60 dark:text-emerald-400/60'">ESLint</div>
          </div>
          <div class="flex flex-col items-center justify-center gap-0.5 px-3 py-2 rounded-lg min-w-[48px]" :class="accessibilityDefects.length > 0 ? 'bg-amber-100 dark:bg-amber-500/10' : 'bg-emerald-100/50 dark:bg-emerald-500/10'">
            <div class="font-mono text-[16px] font-bold leading-none" :class="accessibilityDefects.length > 0 ? 'text-amber-500' : 'text-emerald-500'">{{ accessibilityDefects.length }}</div>
            <div class="text-[8px] font-bold tracking-[0.08em] uppercase" :class="accessibilityDefects.length > 0 ? 'text-amber-600/70 dark:text-amber-400/70' : 'text-emerald-600/60 dark:text-emerald-400/60'">A11y</div>
          </div>
          <div class="flex flex-col items-center justify-center gap-0.5 px-3 py-2 rounded-lg min-w-[48px] bg-blue-100 dark:bg-blue-500/10">
            <div class="font-mono text-[16px] font-bold leading-none text-blue-500">{{ apiCalls.length }}</div>
            <div class="text-[8px] font-bold tracking-[0.08em] uppercase text-blue-600/70 dark:text-blue-400/70">API</div>
          </div>
        </div>
      </div>

      <!-- Metrics -->
      <div class="flex bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-800 shrink-0">
        <div class="flex flex-col gap-1 px-5 py-3 border-r border-gray-200 dark:border-gray-800 flex-1 last:border-r-0">
          <span class="text-[10px] font-bold text-gray-500 dark:text-gray-400 tracking-[0.08em] uppercase">Methods</span>
          <span class="font-mono text-[18px] font-bold text-gray-900 dark:text-gray-50 leading-[1.2]">{{ metrics.methods || 0 }}</span>
        </div>
        <div class="flex flex-col gap-1 px-5 py-3 border-r border-gray-200 dark:border-gray-800 flex-1 last:border-r-0">
          <span class="text-[10px] font-bold text-gray-500 dark:text-gray-400 tracking-[0.08em] uppercase">Lines</span>
          <span class="font-mono text-[18px] font-bold text-gray-900 dark:text-gray-50 leading-[1.2]">{{ metrics.script_lines || 0 }}</span>
        </div>
        <div class="flex flex-col gap-1 px-5 py-3 border-r border-gray-200 dark:border-gray-800 flex-1 last:border-r-0">
          <span class="text-[10px] font-bold text-gray-500 dark:text-gray-400 tracking-[0.08em] uppercase">Complexity</span>
          <span class="font-mono text-[18px] font-bold text-gray-900 dark:text-gray-50 leading-[1.2]">{{ metrics.cyclomatic_complexity || 0 }}</span>
        </div>
        <div class="flex flex-col gap-1 px-5 py-3 border-r border-gray-200 dark:border-gray-800 flex-1 last:border-r-0">
          <span class="text-[10px] font-bold text-gray-500 dark:text-gray-400 tracking-[0.08em] uppercase">API Calls</span>
          <span class="font-mono text-[18px] font-bold text-gray-900 dark:text-gray-50 leading-[1.2]">{{ metrics.api_total || 0 }}</span>
        </div>
      </div>

      <!-- Tabs -->
      <div class="flex flex-col min-h-0 flex-1 overflow-hidden">
        <div class="flex bg-gray-50 dark:bg-gray-900/50 border-b border-gray-200 dark:border-gray-800 shrink-0 px-2 overflow-x-auto">
          <button
            v-for="tab in tabs"
            :key="tab.id"
            class="flex items-center gap-2 px-3.5 py-3 text-[13px] font-medium bg-transparent border-none border-b-2 cursor-pointer transition-all duration-200 whitespace-nowrap -mb-[1px]"
            :class="activeTab === tab.id ? 'border-indigo-500 bg-indigo-50 dark:bg-indigo-500/20 text-indigo-700 dark:text-indigo-300' : 'border-transparent text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200'"
            @click="activeTab = tab.id"
          >
            <span class="w-1.5 h-1.5 rounded-full shrink-0" 
                  :class="{
                    'bg-purple-400': tab.dotClass === 'dot-purple',
                    'bg-emerald-500': tab.dotClass === 'dot-emerald',
                    'bg-amber-500': tab.dotClass === 'dot-amber',
                    'bg-blue-400': tab.dotClass === 'dot-blue'
                  }" 
                  v-if="getTabCount(tab.id) > 0"></span>
            {{ tab.label }}
            <span class="font-mono text-[9px] px-1.5 py-[1px] rounded bg-gray-200 dark:bg-gray-800 ml-0.5 shrink-0"
                  :class="activeTab === tab.id ? 'bg-blue-500/20 text-blue-600 dark:text-blue-400' : 'text-gray-500 dark:text-gray-400'">
              {{ getTabCount(tab.id) }}
            </span>
          </button>
        </div>

        <!-- Tab Content -->
        <div class="flex-1 overflow-y-auto p-4 flex flex-col">
          <!-- AI Issues Tab -->
          <div v-if="activeTab === 'ai'" class="flex-1 flex flex-col">
            <div v-if="aiIssues.length === 0" class="flex flex-col items-center justify-center gap-3 py-16 px-10 text-gray-500 dark:text-gray-400 text-[13px] flex-1 text-center">
              <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1" class="opacity-30">
                <circle cx="12" cy="12" r="10"/>
                <path d="M12 6v6m0 4v.01"/>
              </svg>
              <span>No AI issues found</span>
            </div>
            <div v-else class="flex flex-col gap-3">
              <div v-for="(issue, i) in aiIssues" :key="i" class="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-4 transition-all duration-300 ease-out hover:border-gray-300 dark:hover:border-gray-700 hover:-translate-y-0.5 hover:shadow-md dark:hover:bg-gray-800/80">
                <div class="flex items-start justify-between gap-3 mb-2.5">
                  <div class="text-[13px] font-bold text-gray-900 dark:text-gray-50 leading-[1.4]">{{ issue.issue_title || 'Untitled Issue' }}</div>
                  <span class="inline-flex items-center px-2 py-0.5 rounded-md text-[9px] font-bold tracking-[0.04em] uppercase shrink-0 border"
                        :class="{
                          'bg-red-100 text-red-500 border-red-500/30 dark:bg-red-500/10 dark:text-red-400': getSeverityClass(issue.severity) === 'badge-high',
                          'bg-amber-100 text-amber-500 border-amber-500/30 dark:bg-amber-500/10 dark:text-amber-400': getSeverityClass(issue.severity) === 'badge-med',
                          'bg-emerald-100 text-emerald-500 border-emerald-500/30 dark:bg-emerald-500/10 dark:text-emerald-400': getSeverityClass(issue.severity) === 'badge-low'
                        }">{{ issue.severity || 'Low' }}</span>
                </div>
                <p class="text-[13px] text-gray-600 dark:text-gray-300 leading-[1.6] m-0 mb-2.5">{{ issue.description }}</p>
                <div class="mb-2.5">
                  <span class="inline-flex items-center gap-1 font-mono text-[10px] text-gray-500 dark:text-gray-400 bg-gray-100 dark:bg-gray-800 px-2 py-0.5 rounded-md">Line {{ issue.line_number || 'N/A' }}</span>
                </div>
                <CodeSnippet v-if="issue.code_snippet" :code="issue.code_snippet" :targetLine="issue.line_number" />
              </div>
            </div>
          </div>

          <!-- ESLint Tab -->
          <div v-if="activeTab === 'eslint'" class="flex-1 flex flex-col">
            <div v-if="eslintFlags.length === 0" class="flex flex-col items-center justify-center gap-3 py-16 px-10 text-gray-500 dark:text-gray-400 text-[13px] flex-1 text-center">
              <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1" class="opacity-30">
                <circle cx="12" cy="12" r="10"/>
                <path d="M12 6v6m0 4v.01"/>
              </svg>
              <span>No ESLint issues</span>
            </div>
            <div v-else class="flex flex-col gap-3">
              <div v-for="(flag, i) in eslintFlags" :key="i" class="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-4 transition-all duration-300 ease-out hover:border-gray-300 dark:hover:border-gray-700 hover:-translate-y-0.5 hover:shadow-md dark:hover:bg-gray-800/80">
                <div class="flex items-start justify-between gap-3 mb-2.5">
                  <div class="text-[12px] font-bold text-gray-900 dark:text-gray-50 leading-[1.4] font-mono">{{ flag.rule || 'Unknown Rule' }}</div>
                  <span class="inline-flex items-center px-2 py-0.5 rounded-md text-[9px] font-bold tracking-[0.04em] uppercase shrink-0 border"
                        :class="{
                          'bg-red-100 text-red-500 border-red-500/30 dark:bg-red-500/10 dark:text-red-400': getSeverityClass(flag.severity) === 'badge-high',
                          'bg-amber-100 text-amber-500 border-amber-500/30 dark:bg-amber-500/10 dark:text-amber-400': getSeverityClass(flag.severity) === 'badge-med',
                          'bg-emerald-100 text-emerald-500 border-emerald-500/30 dark:bg-emerald-500/10 dark:text-emerald-400': getSeverityClass(flag.severity) === 'badge-low'
                        }">{{ flag.severity || 'Low' }}</span>
                </div>
                <p class="text-[13px] text-gray-600 dark:text-gray-300 leading-[1.6] m-0 mb-2.5">{{ flag.message }}</p>
                <div class="mb-2.5">
                  <span class="inline-flex items-center gap-1 font-mono text-[10px] text-gray-500 dark:text-gray-400 bg-gray-100 dark:bg-gray-800 px-2 py-0.5 rounded-md">Line {{ flag.line_number || 'N/A' }}</span>
                </div>
                <CodeSnippet v-if="flag.code_snippet" :code="flag.code_snippet" :targetLine="flag.line_number" />
              </div>
            </div>
          </div>

          <!-- Accessibility Tab -->
          <div v-if="activeTab === 'accessibility'" class="flex-1 flex flex-col">
            <div v-if="accessibilityDefects.length === 0" class="flex flex-col items-center justify-center gap-3 py-16 px-10 text-gray-500 dark:text-gray-400 text-[13px] flex-1 text-center">
              <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1" class="opacity-30">
                <circle cx="12" cy="12" r="10"/>
                <path d="M12 6v6m0 4v.01"/>
              </svg>
              <span>No accessibility defects</span>
            </div>
            <div v-else class="flex flex-col gap-3">
              <div v-for="(defect, i) in accessibilityDefects" :key="i" class="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-4 transition-all duration-300 ease-out hover:border-gray-300 dark:hover:border-gray-700 hover:-translate-y-0.5 hover:shadow-md dark:hover:bg-gray-800/80">
                <div class="flex items-start justify-between gap-3 mb-2.5">
                  <div class="text-[12px] font-bold text-gray-900 dark:text-gray-50 leading-[1.4] font-mono">{{ defect.rule || 'Unknown Rule' }}</div>
                  <span class="inline-flex items-center px-2 py-0.5 rounded-md text-[9px] font-bold tracking-[0.04em] uppercase shrink-0 border bg-amber-100 text-amber-500 border-amber-500/30 dark:bg-amber-500/10 dark:text-amber-400">A11y</span>
                </div>
                <p class="text-[13px] text-gray-600 dark:text-gray-300 leading-[1.6] m-0 mb-2.5">{{ defect.message }}</p>
                <div v-if="defect.wcag_criterion" class="flex items-center gap-2 py-2 px-2.5 bg-amber-500/10 border border-amber-500/15 rounded-lg mb-2.5">
                  <span class="text-[9px] font-bold text-amber-500 font-mono shrink-0">WCAG {{ defect.wcag_level }}</span>
                  <span class="text-[12px] text-gray-600 dark:text-gray-300">{{ defect.wcag_criterion }}</span>
                </div>
                <div class="mb-2.5">
                  <span class="inline-flex items-center gap-1 font-mono text-[10px] text-gray-500 dark:text-gray-400 bg-gray-100 dark:bg-gray-800 px-2 py-0.5 rounded-md">Line {{ defect.line_number || 'N/A' }}</span>
                </div>
                <CodeSnippet v-if="defect.code_snippet" :code="defect.code_snippet" :targetLine="defect.line_number" />
              </div>
            </div>
          </div>

          <!-- API Calls Tab -->
          <div v-if="activeTab === 'api'" class="flex-1 flex flex-col">
            <div v-if="apiCalls.length === 0" class="flex flex-col items-center justify-center gap-3 py-16 px-10 text-gray-500 dark:text-gray-400 text-[13px] flex-1 text-center">
              <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1" class="opacity-30">
                <circle cx="12" cy="12" r="10"/>
                <path d="M12 6v6m0 4v.01"/>
              </svg>
              <span>No API calls found</span>
            </div>
            <div v-else class="flex flex-col gap-3">
              <div v-for="(call, i) in apiCalls" :key="i" class="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-4 transition-all duration-300 ease-out hover:border-gray-300 dark:hover:border-gray-700 hover:-translate-y-0.5 hover:shadow-md dark:hover:bg-gray-800/80">
                <div class="flex items-start justify-between gap-3 mb-2.5">
                  <div class="text-[12px] font-bold text-gray-900 dark:text-gray-50 leading-[1.4] font-mono">{{ call.method }} {{ call.endpoint }}</div>
                  <span v-if="call.in_loop" class="inline-flex items-center px-2 py-0.5 rounded-md text-[9px] font-bold tracking-[0.04em] uppercase shrink-0 border bg-red-100 text-red-500 border-red-500/30 dark:bg-red-500/10 dark:text-red-400">IN LOOP</span>
                </div>
                <div class="mb-2.5">
                  <span class="inline-flex items-center gap-1 font-mono text-[10px] text-gray-500 dark:text-gray-400 bg-gray-100 dark:bg-gray-800 px-2 py-0.5 rounded-md">Line {{ call.line_number || 'N/A' }}</span>
                </div>
                <CodeSnippet v-if="call.code_snippet" :code="call.code_snippet" :targetLine="call.line_number" />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, computed } from 'vue'
import { filesAPI } from '../api.js'
import CodeSnippet from './CodeSnippet.vue'

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
  { id: 'eslint',        label: 'ESLint',       dotClass: 'dot-emerald' },
  { id: 'accessibility', label: 'Accessibility', dotClass: 'dot-amber' },
  { id: 'api',           label: 'API Calls',    dotClass: 'dot-blue' },
]

const getTabCount = (id) => {
  return { ai: aiIssues, eslint: eslintFlags, accessibility: accessibilityDefects, api: apiCalls }[id]?.value?.length || 0
}

const getSeverityClass = (s) => {
  const l = (s || '').toLowerCase()
  if (l === 'high' || l === 'error') return 'badge-high'
  if (l === 'medium' || l === 'warning') return 'badge-med'
  return 'badge-low'
}

const fetchFileData = async () => {
  if (!props.filePath) return
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
</script>
