<script setup>
import { ref, onMounted } from 'vue'
import ExecutiveSummary from './components/ExecutiveSummary.vue'
import WorstOffendersTable from './components/WorstOffendersTable.vue'
import AllFilesExplorer from './components/AllFilesExplorer.vue'
import ComponentDetailModal from './components/ComponentDetailModal.vue'

const API_BASE = 'http://127.0.0.1:5000/api'

const summary = ref(null)
const offenders = ref([])
const allFiles = ref([])
const selectedFile = ref(null)
const loadingSummary = ref(true)
const loadingOffenders = ref(true)
const loadingFiles = ref(true)

onMounted(async () => {
  // Fetch Summary
  try {
    const res = await fetch(`${API_BASE}/summary`)
    summary.value = await res.json()
  } catch (e) {
    console.error("Failed to load summary:", e)
  } finally {
    loadingSummary.value = false
  }

  // Fetch Offenders
  try {
    const res = await fetch(`${API_BASE}/worst-offenders?project=my-vue-app`)
    offenders.value = await res.json()
  } catch (e) {
    console.error("Failed to load worst offenders:", e)
  } finally {
    loadingOffenders.value = false
  }

  // Fetch All Files
  try {
    const res = await fetch(`${API_BASE}/files`)
    allFiles.value = await res.json()
  } catch (e) {
    console.error("Failed to load all files:", e)
  } finally {
    loadingFiles.value = false
  }
})

function openDrilldown(filePath) {
  selectedFile.value = filePath
}

function closeDrilldown() {
  selectedFile.value = null
}
</script>

<template>
  <div class="min-h-screen bg-gray-950 text-gray-100 font-sans">
    <!-- Header -->
    <header class="border-b border-gray-800 bg-gray-950 w-full shrink-0">
      <div class="max-w-7xl mx-auto px-8 py-5 flex flex-col justify-center">
        <h1 class="text-2xl font-bold tracking-tight text-white flex items-center">
          Code <span class="text-indigo-400 mx-1">Audit</span> Librarian
        </h1>
        <p class="text-sm font-medium text-gray-500 mt-1">Project Analysis Dashboard</p>
      </div>
    </header>

    <!-- Main Content -->
    <main class="max-w-7xl mx-auto px-8 py-10 space-y-12">

      <!-- Executive Summary -->
      <div>
        <div v-if="loadingSummary" class="flex justify-center py-10">
          <svg class="animate-spin h-8 w-8 text-indigo-400" xmlns="http://www.w3.org/2000/svg" fill="none"
            viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z">
            </path>
          </svg>
        </div>
        <ExecutiveSummary v-else-if="summary" :summary="summary" />
      </div>

      <!-- Worst Offenders -->
      <div>
        <div v-if="loadingOffenders" class="flex justify-center py-10">
          <svg class="animate-spin h-8 w-8 text-indigo-400" xmlns="http://www.w3.org/2000/svg" fill="none"
            viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z">
            </path>
          </svg>
        </div>
        <WorstOffendersTable v-else-if="offenders" :offenders="offenders" @drilldown="openDrilldown" />
      </div>

      <!-- All Files Explorer -->
      <div>
        <div v-if="loadingFiles" class="flex justify-center py-10">
          <svg class="animate-spin h-8 w-8 text-indigo-400" xmlns="http://www.w3.org/2000/svg" fill="none"
            viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z">
            </path>
          </svg>
        </div>
        <AllFilesExplorer v-else-if="allFiles && allFiles.length >= 0" :files="allFiles" @drilldown="openDrilldown" />
      </div>

    </main>

    <!-- Component Detail Modal -->
    <ComponentDetailModal v-if="selectedFile" :file-path="selectedFile" @close="closeDrilldown" />

  </div>
</template>