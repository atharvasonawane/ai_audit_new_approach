<template>
  <div class="flex h-full">
    <!-- Left Pane: File Explorer -->
    <div class="w-80 bg-bg-primary border-r border-border flex flex-col overflow-hidden">
      <!-- Sticky Header with Search -->
      <div class="sticky top-0 z-10 bg-bg-primary border-b border-border p-4">
        <div class="relative">
          <Search 
            :size="16" 
            :stroke-width="2" 
            class="absolute left-3 top-1/2 transform -translate-y-1/2 text-text-tertiary"
          />
          <input
            v-model="searchQuery"
            type="text"
            placeholder="Search files..."
            class="search-input"
          />
        </div>
      </div>

      <!-- File List -->
      <div class="flex-1 overflow-y-auto">
        <!-- Loading State -->
        <div v-if="loading" class="flex items-center justify-center h-64">
          <div class="text-center">
            <Loader2 
              :size="32" 
              :stroke-width="2" 
              class="animate-spin text-accent-primary mx-auto mb-3"
            />
            <p class="text-text-secondary text-sm">Loading files...</p>
          </div>
        </div>

        <!-- Error State -->
        <div v-else-if="error" class="p-6">
          <div class="bg-bg-secondary border border-severity-error rounded-lg p-6 text-center">
            <AlertCircle 
              :size="32" 
              :stroke-width="2" 
              class="text-severity-error mx-auto mb-3"
            />
            <p class="text-text-primary font-semibold mb-2">Failed to load files</p>
            <p class="text-text-secondary text-sm mb-4">{{ error }}</p>
            <button
              @click="fetchFiles"
              class="retry-button"
            >
              <RefreshCw :size="16" :stroke-width="2" />
              <span>Retry</span>
            </button>
          </div>
        </div>

        <!-- File List -->
        <div v-else-if="files.length > 0" class="py-2">
          <div
            v-for="(file, index) in filteredFiles"
            :key="index"
            @click="selectFile(file)"
            class="file-row"
            :class="{ active: selectedFile?.file_path === file.file_path }"
          >
            <div class="flex items-center justify-between flex-1 min-w-0">
              <!-- File Icon & Name -->
              <div class="flex items-center gap-2 flex-1 min-w-0">
                <FileCode2 :size="16" :stroke-width="2" class="flex-shrink-0" />
                <span class="font-mono text-sm truncate">{{ file.file_path }}</span>
              </div>

              <!-- Issue Count Badge -->
              <div
                class="issue-badge"
                :class="getBadgeClass(file)"
              >
                {{ getTotalIssues(file) }}
              </div>
            </div>
          </div>
        </div>

        <!-- Empty State -->
        <div v-else class="flex items-center justify-center h-64">
          <div class="text-center">
            <FolderOpen 
              :size="48" 
              :stroke-width="1.5" 
              class="text-text-tertiary mx-auto mb-3"
            />
            <p class="text-text-secondary text-sm">No files found</p>
          </div>
        </div>
      </div>
    </div>

    <!-- Right Pane: File Detail View -->
    <div class="flex-1 bg-bg-primary overflow-hidden">
      <FileDetailView 
        v-if="selectedFilePath" 
        :filePath="selectedFilePath" 
      />
      <div v-else class="flex items-center justify-center h-full">
        <div class="text-center">
          <FileSearch 
            :size="64" 
            :stroke-width="1.5" 
            class="text-text-tertiary mx-auto mb-4"
          />
          <p class="text-text-secondary text-lg">Select a file to view details</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { 
  Search, 
  FileCode2, 
  Loader2, 
  AlertCircle, 
  RefreshCw,
  FolderOpen,
  FileSearch
} from 'lucide-vue-next'
import { filesAPI } from '../api.js'
import FileDetailView from '../components/FileDetailView.vue'

// State
const files = ref([])
const loading = ref(false)
const error = ref(null)
const searchQuery = ref('')
const selectedFile = ref(null)
const selectedFilePath = ref(null)

// Computed
const filteredFiles = computed(() => {
  if (!searchQuery.value) return files.value
  
  const query = searchQuery.value.toLowerCase()
  return files.value.filter(file => 
    file.file_path.toLowerCase().includes(query)
  )
})

// Methods
const fetchFiles = async () => {
  loading.value = true
  error.value = null
  
  try {
    const response = await filesAPI.getFiles()
    files.value = response.data || []
    console.log('Files loaded:', files.value.length)
  } catch (err) {
    console.error('Error fetching files:', err)
    
    // Handle different error types
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

const selectFile = (file) => {
  selectedFile.value = file
  selectedFilePath.value = file.file_path
  const totalIssues = (file.eslint_flag_count || 0) + (file.accessibility_count || 0) + (file.ai_issue_count || 0)
  console.log('File selected:', file.file_path, 'Total Issues:', totalIssues)
}

const getBadgeClass = (file) => {
  const totalIssues = (file.eslint_flag_count || 0) + (file.accessibility_count || 0) + (file.ai_issue_count || 0)
  
  if (totalIssues === 0) {
    return 'badge-success'
  } else if (totalIssues <= 5) {
    return 'badge-low'
  } else if (totalIssues <= 15) {
    return 'badge-medium'
  } else {
    return 'badge-high'
  }
}

const getTotalIssues = (file) => {
  return (file.eslint_flag_count || 0) + (file.accessibility_count || 0) + (file.ai_issue_count || 0)
}

// Lifecycle
onMounted(() => {
  fetchFiles()
})
</script>

<style scoped>
.search-input {
  width: 100%;
  padding: 8px 12px 8px 36px;
  background-color: var(--color-bg-secondary);
  border: 1px solid var(--color-border);
  border-radius: var(--rounded-base);
  color: var(--color-text-primary);
  font-size: var(--text-sm);
  transition: all 200ms ease-out;
}

.search-input:focus {
  outline: none;
  border-color: var(--color-accent-primary);
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.search-input::placeholder {
  color: var(--color-text-tertiary);
}

.file-row {
  display: flex;
  align-items: center;
  padding: 12px 16px;
  cursor: pointer;
  transition: all 200ms ease-out;
  color: var(--color-text-secondary);
  border-left: 3px solid transparent;
}

.file-row:hover {
  background-color: var(--color-bg-secondary);
  color: var(--color-text-primary);
}

.file-row.active {
  background-color: var(--color-bg-tertiary);
  color: var(--color-text-primary);
  border-left-color: var(--color-accent-primary);
}

.issue-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 32px;
  height: 20px;
  padding: 0 8px;
  border-radius: var(--rounded-full);
  font-size: var(--text-xs);
  font-weight: 600;
  flex-shrink: 0;
}

.badge-success {
  background-color: var(--color-status-success);
  color: #FFFFFF;
}

.badge-low {
  background-color: var(--color-severity-low);
  color: #FFFFFF;
}

.badge-medium {
  background-color: var(--color-severity-medium);
  color: #FFFFFF;
}

.badge-high {
  background-color: var(--color-severity-high);
  color: #FFFFFF;
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

/* Scrollbar styling */
::-webkit-scrollbar {
  width: 8px;
}

::-webkit-scrollbar-track {
  background: var(--color-bg-primary);
}

::-webkit-scrollbar-thumb {
  background: var(--color-bg-tertiary);
  border-radius: var(--rounded-base);
}

::-webkit-scrollbar-thumb:hover {
  background: var(--color-bg-hover);
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
