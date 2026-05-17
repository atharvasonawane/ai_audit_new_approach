<template>
  <div class="flex flex-col gap-10 p-10 max-w-[1200px] mx-auto w-full">
    <!-- Hero Section -->
    <div class="flex flex-col gap-4">
      <div class="inline-flex items-center gap-2 w-fit py-2 px-3.5 bg-emerald-500/10 border border-emerald-500/20 rounded-full text-[12px] font-semibold text-emerald-500">
        <svg width="8" height="8" viewBox="0 0 8 8" fill="none">
          <circle cx="4" cy="4" r="4" fill="currentColor"/>
        </svg>
        <span>Ready to analyze</span>
      </div>
      <h1 class="text-[48px] font-black tracking-[-0.03em] leading-[1.1] m-0 text-gray-900 dark:text-gray-50">
        Code Audit<br><span class="bg-gradient-to-br from-blue-500 to-purple-400 bg-clip-text text-transparent">Librarian</span>
      </h1>
      <p class="text-[16px] font-normal leading-[1.6] m-0 max-w-[600px] text-gray-600 dark:text-gray-400">Enterprise-grade codebase analysis — AI insights, ESLint validation, accessibility compliance</p>
    </div>

    <!-- Main Content -->
    <div class="grid grid-cols-1 lg:grid-cols-[360px_1fr] gap-5 flex-1 min-h-0">
      <!-- Left Panel: Recent Audits -->
      <div class="flex flex-col overflow-hidden bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 shadow-sm rounded-xl transition-all duration-300 hover:border-gray-300 dark:hover:border-gray-700">
        <div class="flex items-center justify-between py-5 px-6 border-b border-gray-100 dark:border-gray-800/50">
          <h3 class="text-[14px] font-bold m-0 tracking-[-0.01em] text-gray-800 dark:text-gray-100">Recent Audits</h3>
          <span class="font-mono text-[10px] py-0.5 px-2 bg-blue-500/10 border border-blue-500/20 rounded-md text-blue-600 dark:text-blue-400 font-bold">{{ recentAudits.length }}</span>
        </div>

        <div v-if="loading" class="flex flex-col gap-2.5 p-4">
          <div v-for="i in 3" :key="i" class="h-20 bg-gradient-to-r from-slate-400/10 to-slate-400/5 rounded-lg animate-pulse"></div>
        </div>

        <div v-else-if="recentAudits.length === 0" class="flex flex-col items-center justify-center gap-3 py-16 px-6 text-[13px] text-gray-500 dark:text-gray-400 flex-1">
          <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1" class="opacity-25">
            <rect x="3" y="3" width="8" height="8" rx="1"/>
            <rect x="13" y="3" width="8" height="8" rx="1"/>
            <rect x="3" y="13" width="8" height="8" rx="1"/>
            <rect x="13" y="13" width="8" height="8" rx="1"/>
          </svg>
          <p>No audits yet. Start analyzing!</p>
        </div>

        <div v-else class="flex flex-col gap-2 p-3 flex-1 overflow-y-auto">
          <div
            v-for="(audit, i) in recentAudits"
            :key="i"
            class="p-4 bg-white dark:bg-gray-800/50 border border-gray-200 dark:border-gray-800/50 rounded-xl cursor-pointer transition-all duration-300 ease-out hover:-translate-y-0.5 hover:shadow-md hover:bg-gray-50 dark:hover:bg-gray-800/80"
            @click="navigateToDashboard"
          >
            <div class="flex items-center justify-between mb-2 gap-2">
              <span class="text-[14px] font-bold tracking-[-0.01em] text-gray-900 dark:text-gray-100">{{ audit.project_name || 'Code Audit' }}</span>
              <span class="inline-flex items-center gap-1 text-[10px] font-bold py-0.5 px-2 rounded-md tracking-[0.05em] uppercase shrink-0"
                    :class="{
                      'text-emerald-500 bg-emerald-500/10': audit.status === 'completed',
                      'text-amber-500 bg-amber-500/10': audit.status === 'in_progress',
                      'text-red-500 bg-red-500/10': audit.status === 'failed'
                    }">
                <span class="w-1 h-1 rounded-full bg-current"></span>
                {{ getStatusText(audit.status) }}
              </span>
            </div>
            <div class="font-mono text-[11px] mb-2.5 text-gray-500 dark:text-gray-400">{{ formatDate(audit.started_at) }}</div>
            <div class="flex gap-3">
              <div class="flex items-center gap-1 text-[12px] text-gray-600 dark:text-gray-400">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" class="text-gray-400 dark:text-gray-500">
                  <path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/>
                </svg>
                <span>{{ audit.total_files || 0 }} files</span>
              </div>
              <div class="flex items-center gap-1 text-[12px] text-gray-600 dark:text-gray-400">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" class="text-gray-400 dark:text-gray-500">
                  <circle cx="12" cy="12" r="10"/>
                  <path d="M12 6v6l4 2"/>
                </svg>
                <span>{{ audit.total_issues || 0 }} issues</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Right Panel: Quick Start -->
      <div class="flex flex-col overflow-hidden bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 shadow-sm rounded-xl transition-all duration-300 hover:border-gray-300 dark:hover:border-gray-700">
        <div class="flex items-center justify-between py-5 px-6 border-b border-gray-100 dark:border-gray-800/50">
          <h3 class="text-[14px] font-bold m-0 tracking-[-0.01em] text-gray-800 dark:text-gray-100">Quick Start</h3>
        </div>

        <div class="flex flex-col gap-4 p-6">
          <label class="text-[11px] font-bold tracking-[0.05em] uppercase text-gray-600 dark:text-gray-400">Project Directory Path</label>
          <div class="relative">
            <svg class="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 dark:text-gray-500 pointer-events-none" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>
            </svg>
            <input
              v-model="projectPath"
              type="text"
              placeholder="/path/to/your/vue-project"
              class="w-full py-2.5 pr-3.5 pl-9 bg-gray-100 dark:bg-gray-800/50 border border-gray-200 dark:border-gray-700/50 text-gray-900 dark:text-gray-100 rounded-lg text-[13px] font-mono outline-none transition-all duration-200 placeholder-gray-400 dark:placeholder-gray-500 focus:border-blue-400/40 focus:bg-blue-500/10 focus:ring-2 focus:ring-gray-300 dark:focus:ring-gray-600 caret-gray-900 dark:caret-white"
              @keydown.enter="startAnalysis"
            />
          </div>

          <div v-if="pathError" class="flex items-center gap-2 py-2.5 px-3 bg-red-500/10 border border-red-500/20 rounded-lg text-[12px] text-red-600 dark:text-red-400">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10"/>
              <line x1="12" y1="8" x2="12" y2="12"/>
              <line x1="12" y1="16" x2="12.01" y2="16"/>
            </svg>
            {{ pathError }}
          </div>

          <div class="flex gap-3">
            <!-- Hidden folder input -->
            <input
              ref="folderInput"
              type="file"
              webkitdirectory
              directory
              class="hidden"
              @change="handleFolderSelect"
            />
            <button class="inline-flex items-center justify-center gap-2 py-2.5 px-4 bg-gray-100 dark:bg-gray-800/50 border border-gray-200 dark:border-gray-700 text-gray-700 dark:text-gray-300 rounded-lg text-[13px] font-bold cursor-pointer transition-all duration-200 hover:bg-gray-200 dark:hover:bg-gray-700/50 hover:text-gray-900 dark:hover:text-gray-100" @click="folderInput.click()">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>
              </svg>
              Browse
            </button>
            <button
              class="inline-flex items-center justify-center gap-2 py-2.5 px-4 bg-gradient-to-br from-blue-500 to-blue-600 text-white flex-1 rounded-lg text-[13px] font-bold cursor-pointer transition-all duration-200 shadow-[0_4px_12px_rgba(59,130,246,0.2)] hover:-translate-y-[1px] hover:shadow-[0_6px_20px_rgba(59,130,246,0.3)] disabled:bg-slate-500/20 disabled:bg-none disabled:text-slate-500 disabled:cursor-not-allowed disabled:shadow-none disabled:transform-none"
              :disabled="!projectPath"
              @click="startAnalysis"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polygon points="5 3 19 12 5 21 5 3"/>
              </svg>
              Analyze Now
            </button>
          </div>

          <div class="flex flex-col items-center justify-center gap-2 py-8 px-6 border border-dashed border-gray-300 dark:border-gray-700 text-gray-500 dark:text-gray-400 rounded-[10px] text-[13px] text-center">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" class="opacity-30">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
              <polyline points="17 8 12 3 7 8"/>
              <line x1="12" y1="3" x2="12" y2="15"/>
            </svg>
            <span>Drag a folder here <span class="text-[12px] text-gray-400 dark:text-gray-500">— coming soon</span></span>
          </div>

          <!-- Feature Cards -->
          <div class="grid grid-cols-1 sm:grid-cols-3 gap-2.5 mt-2">
            <div class="flex items-center gap-2.5 p-3 bg-gray-50 dark:bg-gray-800/50 border border-gray-200 dark:border-gray-800/50 rounded-lg transition-all duration-200 hover:border-gray-300 dark:hover:border-gray-700 hover:bg-gray-100 dark:hover:bg-gray-800">
              <div class="w-9 h-9 rounded-lg flex items-center justify-center text-[11px] font-black tracking-[0.05em] bg-blue-500/15 border border-blue-500/20 text-blue-400 shrink-0">AI</div>
              <div>
                <p class="text-[13px] font-bold text-gray-900 dark:text-gray-100 mb-0.5 m-0">AI Analysis</p>
                <p class="text-[12px] text-gray-500 dark:text-gray-400 m-0">Deep code intelligence</p>
              </div>
            </div>
            <div class="flex items-center gap-2.5 p-3 bg-gray-50 dark:bg-gray-800/50 border border-gray-200 dark:border-gray-800/50 rounded-lg transition-all duration-200 hover:border-gray-300 dark:hover:border-gray-700 hover:bg-gray-100 dark:hover:bg-gray-800">
              <div class="w-9 h-9 rounded-lg flex items-center justify-center text-[11px] font-black tracking-[0.05em] bg-emerald-500/15 border border-emerald-500/20 text-emerald-500 shrink-0">ES</div>
              <div>
                <p class="text-[13px] font-bold text-gray-900 dark:text-gray-100 mb-0.5 m-0">ESLint Scan</p>
                <p class="text-[12px] text-gray-500 dark:text-gray-400 m-0">Standards enforcement</p>
              </div>
            </div>
            <div class="flex items-center gap-2.5 p-3 bg-gray-50 dark:bg-gray-800/50 border border-gray-200 dark:border-gray-800/50 rounded-lg transition-all duration-200 hover:border-gray-300 dark:hover:border-gray-700 hover:bg-gray-100 dark:hover:bg-gray-800">
              <div class="w-9 h-9 rounded-lg flex items-center justify-center text-[11px] font-black tracking-[0.05em] bg-amber-500/15 border border-amber-500/20 text-amber-500 shrink-0">A11</div>
              <div>
                <p class="text-[13px] font-bold text-gray-900 dark:text-gray-100 mb-0.5 m-0">Accessibility</p>
                <p class="text-[12px] text-gray-500 dark:text-gray-400 m-0">WCAG compliance</p>
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
const folderInput = ref(null)

const handleFolderSelect = (e) => {
  const files = e.target.files
  if (files && files.length > 0) {
    // webkitRelativePath gives us 'folderName/file.ext' — grab root folder name
    const rootFolder = files[0].webkitRelativePath.split('/')[0]
    console.log('[Browse] Selected folder:', rootFolder)
    projectPath.value = rootFolder
  }
}

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
const startAnalysis = () => {
  pathError.value = ''
  if (!projectPath.value) { pathError.value = 'Please enter a project directory path'; return }
  router.push({ path: '/analyzing', query: { path: projectPath.value } })
}

onMounted(fetchRecentAudits)
</script>
