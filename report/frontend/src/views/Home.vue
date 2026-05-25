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
      <div class="flex flex-col h-[520px] min-h-0 overflow-hidden bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 shadow-sm rounded-xl transition-all duration-300 hover:border-gray-300 dark:hover:border-gray-700">
        <div class="flex items-center justify-between py-5 px-6 border-b border-gray-100 dark:border-gray-800/50 shrink-0">
          <h3 class="text-[14px] font-bold m-0 tracking-[-0.01em] text-gray-800 dark:text-gray-100">Recent Audits</h3>
          <span class="font-mono text-[10px] py-0.5 px-2 bg-blue-500/10 border border-blue-500/20 rounded-md text-blue-600 dark:text-blue-400 font-bold">{{ recentAudits.length }}</span>
        </div>

        <div v-if="loading" class="flex flex-col gap-2.5 p-4 shrink-0">
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
            class="p-4 bg-white dark:bg-gray-800/50 border border-gray-200 dark:border-gray-800/50 rounded-xl cursor-pointer transition-all duration-300 ease-out hover:-translate-y-0.5 hover:shadow-md hover:bg-gray-50 dark:hover:bg-gray-800/80 group"
            @click="navigateToDashboard(audit.id)"
          >
            <div class="flex items-start justify-between mb-2 gap-2">
              <div class="flex flex-col gap-1 min-w-0 flex-1">
                <span class="text-[14px] font-bold tracking-[-0.01em] text-gray-900 dark:text-gray-100 truncate" :title="audit.project_name || 'Code Audit'">{{ audit.project_name || 'Code Audit' }}</span>
                <div>
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
              </div>
              <button
                v-if="audit.id"
                class="p-1.5 text-gray-400 dark:text-gray-500 hover:text-red-500 dark:hover:text-red-400 rounded-lg hover:bg-red-500/10 dark:hover:bg-red-500/20 transition-all duration-200 shrink-0 md:opacity-0 md:group-hover:opacity-100 focus:opacity-100"
                title="Delete this scan"
                @click.stop="triggerDelete(audit)"
              >
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <polyline points="3 6 5 6 21 6"></polyline>
                  <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                </svg>
              </button>
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
      <div class="flex flex-col h-full overflow-hidden bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 shadow-sm rounded-xl transition-all duration-300 hover:border-gray-300 dark:hover:border-gray-700">
        <div class="flex items-center justify-between py-5 px-6 border-b border-gray-100 dark:border-gray-800/50 shrink-0">
          <h3 class="text-[14px] font-bold m-0 tracking-[-0.01em] text-gray-800 dark:text-gray-100">Quick Start</h3>
        </div>

        <div class="flex flex-col gap-4 p-6">
          <!-- Active Scan Progress Card -->
          <div v-if="showCockpit" class="p-5 bg-blue-50/30 dark:bg-blue-950/10 border border-blue-100 dark:border-blue-900/50 rounded-xl flex flex-col gap-4 animate-in fade-in slide-in-from-top-4 duration-300">
            <!-- Header status details -->
            <div class="flex items-center gap-3">
              <!-- Animated pulsing radar / Completed icon -->
              <div v-if="isAnalyzing" class="relative w-8 h-8 rounded-full flex items-center justify-center bg-blue-500/10 dark:bg-blue-500/20 text-blue-500 shrink-0">
                <span class="absolute inline-flex h-full w-full rounded-full bg-blue-500/30 opacity-75 animate-ping"></span>
                <svg class="animate-spin text-current" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                  <path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67"/>
                </svg>
              </div>
              <div v-else class="w-8 h-8 rounded-full flex items-center justify-center text-emerald-500 bg-emerald-500/10 dark:bg-emerald-500/20 shrink-0">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3">
                  <polyline points="20 6 9 17 4 12" />
                </svg>
              </div>
              <div class="min-w-0 flex-1">
                <p class="text-[13px] font-bold text-gray-900 dark:text-gray-100 m-0">{{ isAnalyzing ? 'Code Analysis in Progress...' : 'Analysis Finished' }}</p>
                <p class="text-[11px] text-gray-500 dark:text-gray-400 m-0 mt-0.5 font-normal truncate" :title="scanProgressText">{{ scanProgressText }}</p>
              </div>
              <span class="font-mono text-[12px] font-black text-blue-600 dark:text-blue-400 shrink-0">{{ scanProgress }}%</span>
            </div>

            <!-- Computed Progress Bar -->
            <div class="w-full bg-gray-200 dark:bg-gray-800 rounded-full h-2 overflow-hidden shrink-0">
              <div 
                class="bg-gradient-to-r from-blue-500 to-indigo-500 h-full rounded-full transition-all duration-300 ease-out shadow-[0_0_8px_rgba(59,130,246,0.5)]"
                :style="{ width: scanProgress + '%' }"
              ></div>
            </div>

            <!-- Pipeline Step Tracker (Stepper) -->
            <div class="flex flex-col gap-3 py-1 shrink-0">
              <div 
                v-for="step in scanSteps" 
                :key="step.id"
                class="flex gap-4 p-3 bg-white dark:bg-gray-800/10 border border-gray-100 dark:border-gray-800/30 rounded-xl transition-all duration-300"
                :class="{
                  'border-blue-500/20 bg-blue-500/5 dark:bg-blue-500/5': step.status === 'active',
                  'opacity-50': step.status === 'pending'
                }"
              >
                <!-- Status Icon Indicator -->
                <div class="shrink-0 mt-0.5">
                  <!-- Pending State -->
                  <div v-if="step.status === 'pending'" class="w-5 h-5 rounded-full border border-gray-300 dark:border-gray-700 flex items-center justify-center bg-gray-50 dark:bg-gray-900">
                    <div class="w-1.5 h-1.5 rounded-full bg-gray-300 dark:bg-gray-700"></div>
                  </div>
                  <!-- Active/In-Progress State -->
                  <div v-else-if="step.status === 'active'" class="w-5 h-5 rounded-full flex items-center justify-center bg-blue-500/10 dark:bg-blue-500/20 text-blue-600 dark:text-blue-400">
                    <svg class="animate-spin" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                      <path d="M21 12a9 9 0 1 1-6.219-8.56"/>
                    </svg>
                  </div>
                  <!-- Completed State -->
                  <div v-else-if="step.status === 'completed'" class="w-5 h-5 rounded-full flex items-center justify-center bg-emerald-500/10 dark:bg-emerald-500/20 text-emerald-600 dark:text-emerald-400">
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3">
                      <polyline points="20 6 9 17 4 12" />
                    </svg>
                  </div>
                  <!-- Failed State -->
                  <div v-else-if="step.status === 'failed'" class="w-5 h-5 rounded-full flex items-center justify-center bg-red-500/10 dark:bg-red-500/20 text-red-600 dark:text-red-400 animate-bounce">
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3">
                      <line x1="18" y1="6" x2="6" y2="18" />
                      <line x1="6" y1="6" x2="18" y2="18" />
                    </svg>
                  </div>
                </div>

                <!-- Text & Context -->
                <div class="flex-1 min-w-0">
                  <div class="flex items-center justify-between gap-2">
                    <span class="text-[13px] font-bold text-gray-900 dark:text-gray-100">{{ step.name }}</span>
                    <span v-if="step.time" class="font-mono text-[10px] font-bold py-0.5 px-2 bg-gray-100 dark:bg-gray-800 border border-gray-200 dark:border-gray-700/50 rounded-md text-gray-500 dark:text-gray-400 shrink-0">
                      {{ step.time }}
                    </span>
                  </div>
                  <p class="text-[11px] text-gray-500 dark:text-gray-400 m-0 mt-0.5 font-normal leading-normal">{{ step.desc }}</p>
                </div>
              </div>
            </div>

            <!-- Collapsible Scrolling Monospace Terminal UI -->
            <div class="flex flex-col gap-2 min-h-0 border-t border-gray-100 dark:border-gray-800/80 pt-3">
              <div class="flex items-center justify-between">
                <span class="text-[10px] font-bold uppercase tracking-[0.05em] text-gray-400 dark:text-gray-500">Developer Logs Console</span>
                <button 
                  class="text-[10px] font-bold text-blue-500 hover:text-blue-600 dark:text-blue-400 dark:hover:text-blue-300 cursor-pointer bg-none border-none p-0 outline-none flex items-center gap-1"
                  @click="showLogs = !showLogs"
                >
                  <span>{{ showLogs ? 'Hide Logs' : 'Show Logs' }}</span>
                  <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="transition-transform duration-200" :class="{ 'rotate-180': showLogs }">
                    <polyline points="6 9 12 15 18 9" />
                  </svg>
                </button>
              </div>
              
              <div 
                v-show="showLogs"
                ref="terminalContainer"
                class="bg-gray-950 dark:bg-black border border-gray-900 dark:border-gray-950 rounded-lg p-3 h-[130px] overflow-y-auto font-mono text-[10px] leading-[1.6] text-gray-300 dark:text-gray-400 shadow-inner flex flex-col gap-1 auto-scroll select-text scrollbar-thin scrollbar-thumb-gray-800 scrollbar-track-transparent"
              >
                <div v-if="scanLogs.length === 0" class="text-gray-500 italic">Initializing console log stream...</div>
                <div 
                  v-for="(log, idx) in scanLogs" 
                  :key="idx"
                  class="whitespace-pre-wrap break-all"
                  :class="{
                    'text-emerald-400 dark:text-emerald-500 font-bold': log.includes('complete') || log.includes('Complete'),
                    'text-amber-400 dark:text-amber-500 font-bold': log.includes('WARNING') || log.includes('dirty') || log.includes('unresolved'),
                    'text-red-400 dark:text-red-500 font-bold': log.includes('failed') || log.includes('Error') || log.includes('Error:') || log.includes('ABORTED') || log.includes('❌'),
                    'text-blue-400 dark:text-blue-500': log.includes('Starting') || log.includes('Running') || log.includes('Phase')
                  }"
                >
                  {{ log }}
                </div>
              </div>
            </div>
            
            <button
              v-if="isAnalyzing"
              class="inline-flex items-center justify-center gap-2 py-2.5 px-4 bg-red-500/10 hover:bg-red-500/20 dark:bg-red-500/5 dark:hover:bg-red-500/10 border border-red-500/20 dark:border-red-500/30 text-red-600 dark:text-red-400 w-full rounded-lg text-[12px] font-bold cursor-pointer transition-all duration-200 shrink-0 mt-1"
              @click="cancelScan"
            >
              <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor">
                <rect x="4" y="4" width="16" height="16" rx="2" />
              </svg>
              Stop & Purge Scan
            </button>

            <button
              v-else
              class="inline-flex items-center justify-center gap-2 py-2.5 px-4 bg-gray-100 hover:bg-gray-200 dark:bg-gray-800 dark:hover:bg-gray-700/80 border border-gray-200 dark:border-gray-700 text-gray-700 dark:text-gray-300 w-full rounded-lg text-[12px] font-bold cursor-pointer transition-all duration-200 shrink-0 mt-1"
              @click="showCockpit = false"
            >
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                <line x1="18" y1="6" x2="6" y2="18"/>
                <line x1="6" y1="6" x2="18" y2="18"/>
              </svg>
              Return to Quick Start
            </button>
          </div>

          <!-- Quick Start Form Controls -->
          <template v-if="!showCockpit">
            <label class="text-[11px] font-bold tracking-[0.05em] uppercase text-gray-600 dark:text-gray-400">Project Directory Path</label>
            <div class="relative">
              <svg class="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 dark:text-gray-500 pointer-events-none" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>
              </svg>
              <input
                v-model="projectPath"
                type="text"
                placeholder="/path/to/your/vue-project"
                class="w-full py-2.5 pr-3.5 pl-9 bg-gray-100 dark:bg-gray-800/50 border border-gray-200 dark:border-gray-700/50 text-gray-900 dark:text-gray-100 rounded-lg text-[13px] font-mono outline-none transition-all duration-200 placeholder-gray-400 dark:placeholder-gray-500 focus:border-blue-400/40 focus:bg-blue-500/10 focus:ring-2 focus:ring-gray-300 dark:focus:ring-gray-600 caret-gray-900 dark:caret-white disabled:opacity-50 disabled:cursor-not-allowed"
                :disabled="isAnalyzing"
                @keydown.enter="analyzeNow"
              />
            </div>

            <div v-if="projectPath && !projectPath.includes('/') && !projectPath.includes('\\')" class="text-[11px] text-blue-600 dark:text-blue-400 bg-blue-500/5 dark:bg-blue-500/10 border border-blue-500/10 dark:border-blue-500/20 py-2 px-3 rounded-lg leading-normal flex items-start gap-1.5 mt-0.5">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" class="shrink-0 mt-0.5 opacity-75">
                <circle cx="12" cy="12" r="10"/>
                <line x1="12" y1="16" x2="12" y2="12"/>
                <line x1="12" y1="8" x2="12.01" y2="8"/>
              </svg>
              <span>Browser security hides absolute paths. Our smart backend resolver will resolve relative folder "{{ projectPath }}" to its absolute directory automatically, or you can paste the absolute path.</span>
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
              <button class="inline-flex items-center justify-center gap-2 py-2.5 px-4 bg-gray-100 dark:bg-gray-800/50 border border-gray-200 dark:border-gray-700 text-gray-700 dark:text-gray-300 rounded-lg text-[13px] font-bold cursor-pointer transition-all duration-200 hover:bg-gray-200 dark:hover:bg-gray-700/50 hover:text-gray-900 dark:hover:text-gray-100" @click="handleBrowse">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                  <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>
                </svg>
                Browse
              </button>
              <button
                class="inline-flex items-center justify-center gap-2 py-2.5 px-4 bg-gradient-to-br from-blue-500 to-blue-600 text-white flex-1 rounded-lg text-[13px] font-bold cursor-pointer transition-all duration-200 shadow-[0_4px_12px_rgba(59,130,246,0.2)] hover:-translate-y-[1px] hover:shadow-[0_6px_20px_rgba(59,130,246,0.3)] disabled:bg-slate-500/20 disabled:bg-none disabled:text-slate-500 disabled:cursor-not-allowed disabled:shadow-none disabled:transform-none"
                :disabled="!projectPath || isAnalyzing"
                @click="analyzeNow"
              >
                <svg v-if="isAnalyzing" class="animate-spin -ml-1 mr-2 h-4 w-4 text-current" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                <svg v-else width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <polygon points="5 3 19 12 5 21 5 3"/>
                </svg>
                {{ isAnalyzing ? 'Analyzing... Please wait' : 'Analyze Now' }}
              </button>
            </div>
          </template>

          <div v-if="scanSuccess" class="flex items-center gap-2 py-2.5 px-3 bg-emerald-500/10 border border-emerald-500/20 rounded-lg text-[12px] text-emerald-600 dark:text-emerald-400">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
              <polyline points="22 4 12 14.01 9 11.01"/>
            </svg>
            {{ scanSuccess }}
          </div>
          <div v-if="scanError" class="flex items-center gap-2 py-2.5 px-3 bg-red-500/10 border border-red-500/20 rounded-lg text-[12px] text-red-600 dark:text-red-400">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10"/>
              <line x1="12" y1="8" x2="12" y2="12"/>
              <line x1="12" y1="16" x2="12.01" y2="16"/>
            </svg>
            {{ scanError }}
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
          <div class="flex flex-wrap gap-2.5 mt-2">
            <div class="flex-1 min-w-[180px] flex items-center gap-2.5 p-3 bg-gray-50 dark:bg-gray-800/50 border border-gray-200 dark:border-gray-800/50 rounded-lg transition-all duration-200 hover:border-gray-300 dark:hover:border-gray-700 hover:bg-gray-100 dark:hover:bg-gray-800">
              <div class="w-9 h-9 rounded-lg flex items-center justify-center text-[11px] font-black tracking-[0.05em] bg-blue-500/15 border border-blue-500/20 text-blue-400 shrink-0">AI</div>
              <div class="min-w-0">
                <p class="text-[13px] font-bold text-gray-900 dark:text-gray-100 mb-0.5 m-0 leading-tight">AI Analysis</p>
                <p class="text-[12px] text-gray-500 dark:text-gray-400 m-0 leading-tight">Deep code intelligence</p>
              </div>
            </div>
            <div class="flex-1 min-w-[180px] flex items-center gap-2.5 p-3 bg-gray-50 dark:bg-gray-800/50 border border-gray-200 dark:border-gray-800/50 rounded-lg transition-all duration-200 hover:border-gray-300 dark:hover:border-gray-700 hover:bg-gray-100 dark:hover:bg-gray-800">
              <div class="w-9 h-9 rounded-lg flex items-center justify-center text-[11px] font-black tracking-[0.05em] bg-emerald-500/15 border border-emerald-500/20 text-emerald-500 shrink-0">ES</div>
              <div class="min-w-0">
                <p class="text-[13px] font-bold text-gray-900 dark:text-gray-100 mb-0.5 m-0 leading-tight">ESLint Scan</p>
                <p class="text-[12px] text-gray-500 dark:text-gray-400 m-0 leading-tight">Standards enforcement</p>
              </div>
            </div>
            <div class="flex-1 min-w-[180px] flex items-center gap-2.5 p-3 bg-gray-50 dark:bg-gray-800/50 border border-gray-200 dark:border-gray-800/50 rounded-lg transition-all duration-200 hover:border-gray-300 dark:hover:border-gray-700 hover:bg-gray-100 dark:hover:bg-gray-800">
              <div class="w-9 h-9 rounded-lg flex items-center justify-center text-[11px] font-black tracking-[0.05em] bg-amber-500/15 border border-amber-500/20 text-amber-500 shrink-0">A11</div>
              <div class="min-w-0">
                <p class="text-[13px] font-bold text-gray-900 dark:text-gray-100 mb-0.5 m-0 leading-tight">Accessibility</p>
                <p class="text-[12px] text-gray-500 dark:text-gray-400 m-0 leading-tight">WCAG compliance</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Custom Confirmation Modal -->
    <div
      v-if="showDeleteModal"
      class="fixed inset-0 z-50 flex items-center justify-center p-4 animate-in fade-in duration-200"
    >
      <!-- Backdrop blur overlay -->
      <div 
        class="absolute inset-0 bg-gray-950/40 dark:bg-black/60 backdrop-blur-sm"
        @click="cancelDelete"
      ></div>
      
      <!-- Modal card content with scaling entry animation -->
      <div 
        class="relative bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 shadow-2xl rounded-2xl w-full max-w-[400px] p-6 overflow-hidden transform scale-100 transition-all duration-300 animate-in zoom-in-95 duration-200"
      >
        <div class="flex flex-col gap-4">
          <!-- Warning Icon & Title -->
          <div class="flex items-center gap-3">
            <div class="w-10 h-10 rounded-full flex items-center justify-center bg-red-500/10 dark:bg-red-500/20 text-red-500 shrink-0">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path>
                <line x1="12" y1="9" x2="12" y2="13"></line>
                <line x1="12" y1="17" x2="12.01" y2="17"></line>
              </svg>
            </div>
            <h3 class="text-[16px] font-bold text-gray-950 dark:text-gray-50 m-0">Confirm Deletion</h3>
          </div>
          
          <!-- Warning Description -->
          <p class="text-[13px] leading-[1.5] text-gray-600 dark:text-gray-400 m-0">
            Are you sure you want to delete the audit scan for <span class="font-bold text-gray-900 dark:text-gray-100">"{{ auditToDelete?.project_name || 'Code Audit' }}"</span>?<br><br>
            This action is permanent and will completely delete the scan results, AI metrics, and lint counts from both the dashboard and database.
          </p>
          
          <!-- Action Buttons -->
          <div class="flex gap-3 mt-2">
            <button 
              class="flex-1 py-2 px-4 bg-gray-100 dark:bg-gray-800/80 border border-gray-200 dark:border-gray-700 text-gray-700 dark:text-gray-300 rounded-lg text-[13px] font-bold cursor-pointer transition-all duration-200 hover:bg-gray-200 dark:hover:bg-gray-700 hover:text-gray-900 dark:hover:text-gray-100"
              @click="cancelDelete"
            >
              Cancel
            </button>
            <button 
              class="flex-1 py-2 px-4 bg-red-600 dark:bg-red-500 hover:bg-red-700 dark:hover:bg-red-600 text-white rounded-lg text-[13px] font-bold cursor-pointer transition-all duration-200 shadow-lg shadow-red-500/10 hover:shadow-red-500/20"
              @click="confirmDelete"
            >
              Delete Scan
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { filesAPI } from '../api.js'
import { getVsCodeApi } from '../utils/vscode.js'

const router = useRouter()
const loading = ref(false)
const recentAudits = ref([])
const projectPath = ref('')
const hasReceivedPath = ref(false)

const pathError = ref('')
const folderInput = ref(null)

const isAnalyzing = ref(false)
const showCockpit = ref(false)
const scanSuccess = ref('')
const scanError = ref('')

// Live Scan logs & computed progress refs
const scanLogs = ref([])
const scanProgress = ref(0)
const scanProgressText = ref('Initializing scan...')
const terminalContainer = ref(null)
const showLogs = ref(false) // Collapsed by default for a clean end-user UI
const activeFile = ref('')
const hasInjectedErrorSummary = ref(false)

// Visual Pipeline Stepper steps definition
const scanSteps = ref([
  { id: 'scout', name: 'Deterministic Scout Scan', desc: 'Audits file structures, ESLint flags, and cyclomatic complexity.', status: 'pending', time: '' },
  { id: 'graph', name: 'Component Dependency Graph', desc: 'Extracts component relationships, cycle detections, and maps imports.', status: 'pending', time: '' },
  { id: 'ai', name: 'AI Code Intelligence', desc: 'Synthesizes LLM-driven deep audits and generates summaries.', status: 'pending', time: '' }
])

// Delete Audit states
const showDeleteModal = ref(false)
const auditToDelete = ref(null)

const triggerDelete = (audit) => {
  auditToDelete.value = audit
  showDeleteModal.value = true
}

const cancelDelete = () => {
  showDeleteModal.value = false
  auditToDelete.value = null
}

const confirmDelete = async () => {
  if (!auditToDelete.value || !auditToDelete.value.id) return
  
  const id = auditToDelete.value.id
  showDeleteModal.value = false
  auditToDelete.value = null
  
  try {
    loading.value = true
    await filesAPI.deleteRecentAudit(id)
    await fetchRecentAudits()
  } catch (err) {
    console.error('Error deleting audit:', err)
    alert(err.response?.data?.error || 'Failed to delete the audit.')
  } finally {
    loading.value = false
  }
}

const handleFolderSelect = (e) => {
  const files = e.target.files
  if (files && files.length > 0) {
    // webkitRelativePath gives us 'folderName/file.ext' — grab root folder name
    const rootFolder = files[0].webkitRelativePath.split('/')[0]
    console.log('[Browse] Selected folder:', rootFolder)
    projectPath.value = rootFolder
  }
}

const handleBrowse = () => {
  const vscode = getVsCodeApi()
  if (vscode) {
    vscode.postMessage({ command: 'openFolderDialog' })
  } else {
    folderInput.value.click()
  }
}

const fetchRecentAudits = async () => {
  loading.value = true
  try {
    const res = await filesAPI.getRecentAudits()
    recentAudits.value = res.data || []
  } catch (err) {
    console.error('Error fetching recent audits:', err)
    recentAudits.value = []
  } finally {
    loading.value = false
  }
}

const formatDate = (d) => {
  if (!d) return 'N/A'
  let dateStr = d
  if (typeof d === 'string') {
    // Append 'Z' to treat ISO datetimes from backend as UTC if they lack a timezone suffix
    if (!d.endsWith('Z') && !/\+\d{2}:?\d{2}$/.test(d)) {
      dateStr = d.includes('T') ? d + 'Z' : d.replace(' ', 'T') + 'Z'
    }
  }
  try {
    const date = new Date(dateStr)
    if (isNaN(date.getTime())) return d
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric', hour: '2-digit', minute: '2-digit' })
  } catch (err) {
    return d
  }
}

const getStatusText = (s) => ({ completed: 'Completed', in_progress: 'Running', failed: 'Failed' }[s] || 'Unknown')
const navigateToDashboard = (runId) => {
  if (runId) {
    router.push({ path: '/dashboard', query: { run_id: runId } })
  } else {
    router.push('/dashboard')
  }
}
const isRelevantLog = (line) => {
  const lower = line.toLowerCase()
  
  // 1. Always keep warnings, errors, exceptions, and failures
  if (lower.includes('error') || lower.includes('failed') || lower.includes('warning') || lower.includes('exception')) {
    return true
  }
  
  // 2. Filter out repetitive file-by-file scout logs (since the progress bar covers this visually!)
  if (line.includes('[orchestrator]') && line.includes('Processing')) {
    return false
  }
  
  // 3. Keep phase checkmarks, complete indicators, and database summaries
  if (
    lower.includes('phase') || 
    lower.includes('complete') || 
    lower.includes('starting') || 
    lower.includes('running') || 
    lower.includes('synthesis') ||
    lower.includes('database') ||
    lower.includes('wrote') ||
    lower.includes('saved to') ||
    lower.includes('cancelled') ||
    lower.includes('api_server') ||
    lower.includes('flask')
  ) {
    return true
  }
  
  // 4. Filter out any remaining orchestrator numeric progress patterns
  if (line.match(/\[orchestrator\]\s+\[(\d+)\/(\d+)\]/)) {
    return false
  }
  
  return true
}

const analyzeNow = async () => {
  console.log('[Home.vue] analyzeNow triggered with path:', projectPath.value)
  
  if (!projectPath.value) { 
    alert("Path is empty!")
    return 
  }

  pathError.value = ''
  scanSuccess.value = ''
  scanError.value = ''
  scanLogs.value = []
  scanProgress.value = 0
  scanProgressText.value = 'Initializing scan...'
  isAnalyzing.value = true
  showCockpit.value = true
  activeFile.value = ''
  hasInjectedErrorSummary.value = false

  // Reset visual pipeline stepper
  scanSteps.value.forEach(s => {
    s.status = 'pending'
    s.time = ''
  })
  scanSteps.value[0].status = 'active'
  showLogs.value = false // Collapsed by default for a clean end-user experience

  let scoutStartTime = Date.now()
  let graphStartTime = null
  let aiStartTime = null
  
  try {
    const port = window.__FLASK_PORT__ || 5000
    const res = await fetch(`http://localhost:${port}/api/scan`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path: projectPath.value })
    })
    
    if (!res.ok) {
      const data = await res.json().catch(() => ({}))
      throw new Error(data.error || data.details || 'Analysis failed')
    }
    
    const reader = res.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      
      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      // Save last partial line back to buffer
      buffer = lines.pop()
      
      for (const line of lines) {
        if (!line.trim()) continue
        
        // Track the active file currently being audited
        const fileMatch = line.match(/Processing\s+(.*)/)
        if (fileMatch) {
          activeFile.value = fileMatch[1].replace(/\.+$/, '').trim()
        }
        
        // Filter and add only relevant log lines for a clean interface
        if (isRelevantLog(line)) {
          scanLogs.value.push(line)
        }
        
        // Auto scroll terminal container
        nextTick(() => {
          if (terminalContainer.value) {
            terminalContainer.value.scrollTop = terminalContainer.value.scrollHeight
          }
        })
        
        // Parse step transitions & durations dynamically
        if (line.includes('Scout Phase Complete')) {
          const elapsed = ((Date.now() - scoutStartTime) / 1000).toFixed(1)
          scanSteps.value[0].status = 'completed'
          scanSteps.value[0].time = `${elapsed}s`
          
          scanSteps.value[1].status = 'active'
          graphStartTime = Date.now()
        } else if (line.includes('Dependency Graph Phase Complete')) {
          const elapsed = ((Date.now() - graphStartTime) / 1000).toFixed(1)
          scanSteps.value[1].status = 'completed'
          scanSteps.value[1].time = `${elapsed}s`
          
          scanSteps.value[2].status = 'active'
          aiStartTime = Date.now()
        } else if (line.includes('Analysis complete!')) {
          const elapsed = ((Date.now() - aiStartTime) / 1000).toFixed(1)
          scanSteps.value[2].status = 'completed'
          scanSteps.value[2].time = `${elapsed}s`
          
          scanProgress.value = 100
          scanProgressText.value = 'Analysis completed successfully!'
          scanSuccess.value = 'Analysis complete! The dashboard will now reflect the latest data.'
        } else if (line.includes('Scan cancelled by the user.')) {
          scanProgress.value = 0
          scanProgressText.value = 'Scan cancelled.'
          scanSuccess.value = 'Scan cancelled successfully and partial database results purged.'
          scanSteps.value.forEach(s => {
            if (s.status === 'active') s.status = 'pending'
          })
        }
        
        // Parse progress patterns
        const match = line.match(/\[orchestrator\]\s+\[(\d+)\/(\d+)\]/)
        if (match) {
          const current = parseInt(match[1], 10)
          const total = parseInt(match[2], 10)
          scanProgress.value = Math.round((current / total) * 80) // 80% weight for file scouting
          scanProgressText.value = `Auditing files (${current}/${total})...`
        } else if (line.includes('targeted ESLint scan') && scanProgress.value < 85) {
          scanProgress.value = 85
          scanProgressText.value = 'Running targeted ESLint compliance check...'
        } else if (line.includes('Dependency Graph') && scanProgress.value < 90) {
          scanProgress.value = 90
          scanProgressText.value = 'Building visual component dependency graph...'
        } else if ((line.includes('Starting AI Agent Phase') || line.includes('AI Agent')) && scanProgress.value < 95) {
          scanProgress.value = 95
          scanProgressText.value = 'Synthesizing AI analysis and generating summaries...'
        }
        
        // Parse critical errors & trigger auto-expand for developer debugging
        if (line.includes('failed') || line.includes('Error:') || line.includes('Analysis failed')) {
          const activeStep = scanSteps.value.find(s => s.status === 'active')
          if (activeStep) {
            activeStep.status = 'failed'
          }
          
          // Inject explicit diagnosis about unscanned files if we have an active file
          if (activeFile.value && !hasInjectedErrorSummary.value) {
            scanLogs.value.push(`[SYSTEM WARNING] ❌ PIPELINE ABORTED: Analysis failed while auditing: ${activeFile.value}`)
            scanLogs.value.push(`[SYSTEM WARNING] ⚠️ Remaining files in the queue were skipped and not scanned.`)
            hasInjectedErrorSummary.value = true
          }
          
          showLogs.value = true // Auto-expand logs drawer so the developer can see the error!
          nextTick(() => {
            if (terminalContainer.value) {
              terminalContainer.value.scrollTop = terminalContainer.value.scrollHeight
            }
          })
        }
      }
    }
    
    await fetchRecentAudits()
  } catch (err) {
    scanError.value = err.message || 'An unexpected error occurred during analysis.'
    const activeStep = scanSteps.value.find(s => s.status === 'active')
    if (activeStep) {
      activeStep.status = 'failed'
    }
    if (activeFile.value && !hasInjectedErrorSummary.value) {
      scanLogs.value.push(`[SYSTEM WARNING] ❌ PIPELINE ABORTED: Analysis failed while auditing: ${activeFile.value}`)
      scanLogs.value.push(`[SYSTEM WARNING] ⚠️ Remaining files in the queue were skipped and not scanned.`)
      hasInjectedErrorSummary.value = true
    }
    showLogs.value = true // Reveal logs
  } finally {
    isAnalyzing.value = false
  }
}

const cancelScan = async () => {
  console.log('[Home.vue] cancelScan triggered')
  try {
    const port = window.__FLASK_PORT__ || 5000
    const res = await fetch(`http://localhost:${port}/api/scan/cancel`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    })
    const data = await res.json()
    console.log('[Home.vue] cancelScan response:', data)
    
    scanSuccess.value = 'Scan stopped and intermediate results deleted successfully.'
    isAnalyzing.value = false
    showCockpit.value = false
    scanLogs.value = []
    scanProgress.value = 0
    scanSteps.value.forEach(s => {
      s.status = 'pending'
      s.time = ''
    })
    await fetchRecentAudits()
  } catch (err) {
    console.error('Error cancelling scan:', err)
    scanError.value = 'Failed to abort the active scan.'
  }
}

const handleMessage = (event) => {
  const message = event.data
  if (!message || typeof message !== 'object') return

  if (message.command === 'setWorkspacePath') {
    // Pong from extension in response to our 'webviewReady' ping
    if (message.path !== undefined) {
      console.log('[Home.vue] Received workspace path via handshake:', message.path)
      projectPath.value = message.path
    }
  } else if (message.command === 'setPath') {
    // Legacy / visibility-change fallback
    if (message.payload !== undefined) {
      console.log('[Home.vue] Received workspace path (legacy setPath):', message.payload)
      projectPath.value = message.payload
    }
  } else if (message.type === 'selectedFolder' && message.path) {
    console.log('[Home.vue] Received selected folder from extension:', message.path)
    projectPath.value = message.path
  }
}

onMounted(() => {
  fetchRecentAudits()

  // ── Layer 1: Synchronous (most reliable) ────────────────────────────────
  // The extension injects window.__WORKSPACE_PATH__ directly into the HTML
  // <head> before the page even renders — read it immediately.
  const injectedPath = window.__WORKSPACE_PATH__
  if (injectedPath) {
    projectPath.value = injectedPath
    console.log('[Home.vue] Path from injected global:', injectedPath)
  }

  // ── Layer 2: Async ping-pong handshake (dynamic / tab-restore) ──────────
  // Register listener BEFORE sending the ping so we never miss the pong.
  window.addEventListener('message', handleMessage)

  const vscode = getVsCodeApi()
  if (vscode) {
    vscode.postMessage({ command: 'webviewReady' })
    console.log('[Home.vue] Sent webviewReady ping to extension host')
  }
})

onUnmounted(() => {
  window.removeEventListener('message', handleMessage)
})
</script>
