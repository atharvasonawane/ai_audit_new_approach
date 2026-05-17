<template>
  <div class="flex h-full overflow-hidden explorer">
    <!-- Left: File Pane -->
    <div class="bg-gray-50 dark:bg-gray-900 flex flex-col overflow-hidden" :style="{ width: paneWidth + 'px', minWidth: paneWidth + 'px' }">
      <!-- Header with Search -->
      <div class="flex items-center gap-2.5 p-3 border-b border-gray-200 dark:border-gray-800 shrink-0">
        <div class="relative flex-1">
          <svg class="absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-400 dark:text-gray-500 pointer-events-none opacity-80" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="11" cy="11" r="8"/>
            <path d="m21 21-4.35-4.35"/>
          </svg>
          <input
            v-model="searchQuery"
            type="text"
            placeholder="Search files..."
            class="w-full py-2 pr-3 pl-8 bg-gray-100 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 text-gray-900 dark:text-gray-100 rounded-lg text-[13px] outline-none transition-all duration-200 placeholder-gray-400 dark:placeholder-gray-500 focus:border-blue-400/40 focus:bg-blue-500/10 focus:ring-2 focus:ring-gray-300 dark:focus:ring-gray-600 caret-gray-900 dark:caret-white"
          />
        </div>
        <div class="font-mono text-[11px] py-1 px-2 bg-slate-500/15 border border-slate-400/10 rounded-md text-gray-600 dark:text-gray-400 shrink-0 font-semibold">
          {{ filteredFiles.length }}
        </div>
      </div>

      <!-- Files List -->
      <div class="flex-1 overflow-y-auto p-2 flex flex-col">
        <!-- Loading -->
        <div v-if="loading" class="p-2 flex flex-col gap-1.5">
          <div v-for="i in 6" :key="i" class="h-9 bg-gradient-to-r from-slate-400/10 to-slate-400/5 rounded-lg animate-pulse"></div>
        </div>

        <!-- Error -->
        <div v-else-if="error" class="flex flex-col items-center justify-center gap-3 py-10 px-5 text-center text-gray-500 dark:text-gray-400 flex-1">
          <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" class="opacity-40">
            <circle cx="12" cy="12" r="10"/>
            <line x1="12" y1="8" x2="12" y2="12"/>
            <line x1="12" y1="16" x2="12.01" y2="16"/>
          </svg>
          <p class="text-[12px] leading-relaxed">{{ error }}</p>
          <button class="px-3.5 py-1.5 bg-blue-500/15 text-blue-400 border border-blue-500/30 rounded-md text-[12px] font-semibold transition-all duration-200 mt-2 hover:bg-blue-500/25 hover:border-blue-500/50" @click="fetchFiles">Retry</button>
        </div>

        <!-- Files -->
        <div v-else-if="filteredFiles.length > 0" class="flex flex-col gap-1">
          <div
            v-for="(file, i) in filteredFiles"
            :key="i"
            class="group flex items-center justify-between p-2.5 rounded-lg cursor-pointer transition-all duration-200 gap-2 border-l-2 border-transparent bg-transparent hover:bg-slate-400/10 hover:border-blue-500/20"
            :class="{ 'bg-indigo-50 dark:bg-indigo-500/20 border-indigo-500 hover:bg-indigo-50 dark:hover:bg-indigo-500/20': selectedFile?.file_path === file.file_path }"
            @click="selectFile(file)"
          >
            <div class="flex items-center gap-2.5 min-w-0 flex-1">
              <svg class="shrink-0 opacity-80 transition-colors duration-200" :class="selectedFile?.file_path === file.file_path ? 'text-blue-400' : 'text-gray-400 dark:text-gray-500 group-hover:text-gray-600 dark:group-hover:text-gray-300'" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/>
                <polyline points="13 2 13 9 20 9"/>
              </svg>
              <span class="font-mono text-[12px] whitespace-nowrap overflow-hidden text-ellipsis transition-colors duration-200" :class="selectedFile?.file_path === file.file_path ? 'text-indigo-700 dark:text-indigo-300 font-medium' : 'text-gray-900 dark:text-gray-100'">{{ getFileName(file.file_path) }}</span>
            </div>
            <div class="font-mono text-[10px] font-bold py-0.5 px-1.5 rounded-md shrink-0 transition-all duration-200" 
                 :class="{
                   'bg-emerald-500/10 text-emerald-500': getIssueBadgeClass(file) === 'badge-zero' || getIssueBadgeClass(file) === 'badge-low',
                   'bg-amber-500/10 text-amber-500': getIssueBadgeClass(file) === 'badge-med',
                   'bg-red-500/10 text-red-500': getIssueBadgeClass(file) === 'badge-high'
                 }">
              {{ getTotalIssues(file) }}
            </div>
          </div>
        </div>

        <!-- Empty -->
        <div v-else class="flex flex-col items-center justify-center gap-3 py-10 px-5 text-center text-gray-500 dark:text-gray-400 flex-1">
          <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1" class="opacity-20">
            <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>
          </svg>
          <p class="text-[12px]">No files found</p>
        </div>
      </div>
    </div>

    <!-- Resizer -->
    <div class="w-1 cursor-col-resize bg-gray-200 dark:bg-white/10 hover:bg-gray-300 dark:hover:bg-gray-600 active:bg-gray-400 dark:active:bg-gray-500 transition-colors shrink-0 z-10" @mousedown="startDrag"></div>

    <!-- Right: Detail Pane -->
    <div class="flex-1 overflow-hidden bg-white dark:bg-gray-950">
      <FileDetailView v-if="selectedFilePath" :filePath="selectedFilePath" />
      <div v-else class="h-full flex flex-col items-center justify-center gap-5 p-10 text-center">
        <div class="flex flex-col items-center gap-4">
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1" class="text-gray-400 dark:text-gray-600">
            <circle cx="11" cy="11" r="8" class="opacity-30"/>
            <path d="M21 21l-4.35-4.35" class="opacity-30"/>
            <circle cx="11" cy="11" r="8" class="opacity-15"/>
            <path d="M11 8v6M11 17h.01" class="opacity-30"/>
          </svg>
          <h3 class="text-base font-bold text-gray-900 dark:text-gray-100 m-0">Select a file</h3>
          <p class="text-[13px] text-gray-500 dark:text-gray-400 max-w-[320px] leading-relaxed m-0">Choose a file from the left panel to view its audit details and code issues.</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { filesAPI } from '../api.js'
import FileDetailView from '../components/FileDetailView.vue'
import { useSearch } from '../composables/useSearch'

const route = useRoute()
const { searchQuery } = useSearch()
const files = ref([])
const loading = ref(false)
const error = ref(null)
const selectedFile = ref(null)
const selectedFilePath = ref(null)

const paneWidth = ref(280)
const isDragging = ref(false)

const startDrag = () => {
  isDragging.value = true
  document.addEventListener('mousemove', onDrag)
  document.addEventListener('mouseup', stopDrag)
  document.body.style.cursor = 'col-resize'
  document.body.style.userSelect = 'none'
}

const onDrag = (e) => {
  if (isDragging.value) {
    const container = document.querySelector('.explorer')
    if (container) {
      const rect = container.getBoundingClientRect()
      let newWidth = e.clientX - rect.left
      if (newWidth < 200) newWidth = 200
      if (newWidth > 600) newWidth = 600
      paneWidth.value = newWidth
    }
  }
}

const stopDrag = () => {
  isDragging.value = false
  document.removeEventListener('mousemove', onDrag)
  document.removeEventListener('mouseup', stopDrag)
  document.body.style.cursor = ''
  document.body.style.userSelect = ''
}

const filteredFiles = computed(() => {
  if (!searchQuery.value) return files.value
  const q = searchQuery.value.toLowerCase()
  return files.value.filter(f => f.file_path.toLowerCase().includes(q))
})

const getFileName = (p) => p ? p.split('/').pop() : p
const getTotalIssues = (f) => (f.eslint_flag_count||0) + (f.accessibility_count||0) + (f.ai_issue_count||0)
const getIssueBadgeClass = (f) => {
  const n = getTotalIssues(f)
  if (n === 0) return 'badge-zero'
  if (n <= 5)  return 'badge-low'
  if (n <= 15) return 'badge-med'
  return 'badge-high'
}

const fetchFiles = async () => {
  loading.value = true; error.value = null
  try {
    const res = await filesAPI.getFiles()
    files.value = res.data || []
  } catch (err) {
    error.value = err.code === 'ERR_NETWORK' ? 'Cannot connect to API server' : err.message || 'Error'
  } finally { loading.value = false }
}

const selectFile = (file) => {
  selectedFile.value = file
  selectedFilePath.value = file.file_path
}

onMounted(fetchFiles)

watch(() => route.query.file, (p) => {
  if (p && files.value.length > 0) {
    const f = files.value.find(x => x.file_path === p)
    if (f) selectFile(f)
  }
}, { immediate: true })

watch(files, (arr) => {
  if (arr.length > 0 && route.query.file) {
    const f = arr.find(x => x.file_path === route.query.file)
    if (f) selectFile(f)
  }
})
</script>
