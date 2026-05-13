<template>
  <!-- Backdrop Overlay -->
  <Transition name="fade">
    <div
      v-if="isOpen"
      class="command-palette-backdrop"
      @click="closeModal"
    >
      <!-- Modal Container -->
      <div
        class="command-palette-modal"
        @click.stop
      >
        <!-- Search Input -->
        <div class="search-container">
          <Search 
            :size="20" 
            :stroke-width="2" 
            class="search-icon"
          />
          <input
            ref="searchInput"
            v-model="searchQuery"
            type="text"
            placeholder="Search files..."
            class="search-input"
            @keydown.down.prevent="navigateDown"
            @keydown.up.prevent="navigateUp"
            @keydown.enter.prevent="selectFile"
          />
        </div>

        <!-- Results Area -->
        <div class="results-container">
          <!-- Loading State -->
          <div v-if="loading" class="results-loading">
            <Loader2 
              :size="24" 
              :stroke-width="2" 
              class="animate-spin text-accent-primary"
            />
            <p class="text-text-secondary text-sm">Loading files...</p>
          </div>

          <!-- Error State -->
          <div v-else-if="error" class="results-empty">
            <AlertCircle 
              :size="32" 
              :stroke-width="2" 
              class="text-severity-error mb-2"
            />
            <p class="text-text-secondary text-sm">{{ error }}</p>
          </div>

          <!-- Empty State -->
          <div v-else-if="filteredFiles.length === 0" class="results-empty">
            <FileSearch 
              :size="32" 
              :stroke-width="1.5" 
              class="text-text-tertiary mb-2"
            />
            <p class="text-text-secondary text-sm">
              {{ searchQuery ? 'No files found' : 'Start typing to search...' }}
            </p>
          </div>

          <!-- Results List -->
          <div v-else class="results-list">
            <div
              v-for="(file, index) in filteredFiles"
              :key="file.file_path"
              class="result-item"
              :class="{ active: index === selectedIndex }"
              @click="selectFileByIndex(index)"
              @mouseenter="selectedIndex = index"
            >
              <FileCode2 
                :size="16" 
                :stroke-width="2" 
                class="result-icon"
              />
              <div class="result-info">
                <div class="result-filename">{{ getFileName(file.file_path) }}</div>
                <div class="result-path">{{ file.file_path }}</div>
              </div>
              <div
                class="result-badge"
                :class="getBadgeClass(file)"
              >
                {{ getTotalIssues(file) }}
              </div>
            </div>
          </div>
        </div>

        <!-- Footer -->
        <div class="palette-footer">
          <div class="footer-hint">
            <span class="footer-key">↑↓</span>
            <span class="footer-text">Navigate</span>
          </div>
          <div class="footer-hint">
            <span class="footer-key">⏎</span>
            <span class="footer-text">Select</span>
          </div>
          <div class="footer-hint">
            <span class="footer-key">Esc</span>
            <span class="footer-text">Close</span>
          </div>
        </div>
      </div>
    </div>
  </Transition>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { 
  Search, 
  FileCode2, 
  Loader2, 
  AlertCircle,
  FileSearch
} from 'lucide-vue-next'
import { filesAPI } from '../api.js'

const router = useRouter()

// State
const isOpen = ref(false)
const searchQuery = ref('')
const files = ref([])
const loading = ref(false)
const error = ref(null)
const selectedIndex = ref(0)
const searchInput = ref(null)

// Computed
const filteredFiles = computed(() => {
  if (!searchQuery.value) return files.value.slice(0, 50) // Show first 50 if no query
  
  const query = searchQuery.value.toLowerCase()
  return files.value
    .filter(file => file.file_path.toLowerCase().includes(query))
    .slice(0, 50) // Limit to 50 results for performance
})

// Methods
const openModal = async () => {
  isOpen.value = true
  selectedIndex.value = 0
  searchQuery.value = ''
  
  // Fetch files if not already loaded
  if (files.value.length === 0) {
    await fetchFiles()
  }
  
  // Focus input after modal opens
  await nextTick()
  searchInput.value?.focus()
}

const closeModal = () => {
  isOpen.value = false
  searchQuery.value = ''
  selectedIndex.value = 0
}

const fetchFiles = async () => {
  loading.value = true
  error.value = null
  
  try {
    const response = await filesAPI.getFiles()
    files.value = response.data || []
    console.log('Command Palette: Files loaded:', files.value.length)
  } catch (err) {
    console.error('Command Palette: Error fetching files:', err)
    error.value = 'Failed to load files'
  } finally {
    loading.value = false
  }
}

const navigateDown = () => {
  if (selectedIndex.value < filteredFiles.value.length - 1) {
    selectedIndex.value++
    scrollToSelected()
  }
}

const navigateUp = () => {
  if (selectedIndex.value > 0) {
    selectedIndex.value--
    scrollToSelected()
  }
}

const scrollToSelected = () => {
  // Scroll the selected item into view
  nextTick(() => {
    const selectedElement = document.querySelector('.result-item.active')
    if (selectedElement) {
      selectedElement.scrollIntoView({ block: 'nearest', behavior: 'smooth' })
    }
  })
}

const selectFile = () => {
  if (filteredFiles.value.length > 0 && selectedIndex.value >= 0) {
    selectFileByIndex(selectedIndex.value)
  }
}

const selectFileByIndex = (index) => {
  const file = filteredFiles.value[index]
  if (file) {
    // Navigate to audit view with file query parameter
    router.push({ 
      path: '/audit', 
      query: { file: file.file_path } 
    })
    closeModal()
  }
}

const getFileName = (filePath) => {
  if (!filePath) return ''
  const parts = filePath.split('/')
  return parts[parts.length - 1]
}

const getTotalIssues = (file) => {
  return (file.eslint_flag_count || 0) + 
         (file.accessibility_count || 0) + 
         (file.ai_issue_count || 0)
}

const getBadgeClass = (file) => {
  const totalIssues = getTotalIssues(file)
  
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

// Keyboard event handler
const handleKeydown = (event) => {
  // Cmd+K (Mac) or Ctrl+K (Windows/Linux)
  if ((event.metaKey || event.ctrlKey) && event.key === 'k') {
    event.preventDefault()
    if (isOpen.value) {
      closeModal()
    } else {
      openModal()
    }
  }
  
  // Escape key
  if (event.key === 'Escape' && isOpen.value) {
    event.preventDefault()
    closeModal()
  }
}

// Watch for search query changes to reset selected index
watch(searchQuery, () => {
  selectedIndex.value = 0
})

// Lifecycle
onMounted(() => {
  // Add global keyboard listener
  window.addEventListener('keydown', handleKeydown)
})

onUnmounted(() => {
  // Remove global keyboard listener
  window.removeEventListener('keydown', handleKeydown)
})
</script>

<style scoped>
/* Backdrop */
.command-palette-backdrop {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.75);
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding-top: 15vh;
  z-index: 50;
  overflow-y: auto;
}

/* Modal Container */
.command-palette-modal {
  width: 100%;
  max-width: 600px;
  background-color: var(--color-bg-secondary);
  border: 1px solid var(--color-border);
  border-radius: var(--rounded-lg);
  box-shadow: var(--shadow-xl);
  display: flex;
  flex-direction: column;
  max-height: 70vh;
  margin: 0 16px;
}

/* Search Container */
.search-container {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 20px 24px;
  border-bottom: 1px solid var(--color-border);
}

.search-icon {
  color: var(--color-text-tertiary);
  flex-shrink: 0;
}

.search-input {
  flex: 1;
  background: transparent;
  border: none;
  outline: none;
  color: var(--color-text-primary);
  font-size: var(--text-lg);
  font-weight: 500;
}

.search-input::placeholder {
  color: var(--color-text-tertiary);
}

/* Results Container */
.results-container {
  flex: 1;
  overflow-y: auto;
  min-height: 200px;
  max-height: 400px;
}

.results-loading,
.results-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 48px 24px;
  text-align: center;
}

.results-list {
  padding: 8px;
}

/* Result Item */
.result-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  border-radius: var(--rounded-base);
  cursor: pointer;
  transition: all 150ms ease-out;
}

.result-item:hover,
.result-item.active {
  background-color: var(--color-bg-tertiary);
}

.result-item.active {
  border-left: 3px solid var(--color-accent-primary);
  padding-left: 13px;
}

.result-icon {
  color: var(--color-text-secondary);
  flex-shrink: 0;
}

.result-info {
  flex: 1;
  min-width: 0;
}

.result-filename {
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--color-text-primary);
  font-family: var(--font-mono);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.result-path {
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
  font-family: var(--font-mono);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  margin-top: 2px;
}

.result-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 28px;
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

/* Footer */
.palette-footer {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 12px 24px;
  border-top: 1px solid var(--color-border);
  background-color: var(--color-bg-primary);
}

.footer-hint {
  display: flex;
  align-items: center;
  gap: 6px;
}

.footer-key {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 24px;
  height: 20px;
  padding: 0 6px;
  background-color: var(--color-bg-tertiary);
  border: 1px solid var(--color-border);
  border-radius: var(--rounded-sm);
  font-size: var(--text-xs);
  font-weight: 600;
  color: var(--color-text-secondary);
  font-family: var(--font-mono);
}

.footer-text {
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
}

/* Scrollbar styling */
.results-container::-webkit-scrollbar {
  width: 8px;
}

.results-container::-webkit-scrollbar-track {
  background: var(--color-bg-primary);
}

.results-container::-webkit-scrollbar-thumb {
  background: var(--color-bg-tertiary);
  border-radius: var(--rounded-base);
}

.results-container::-webkit-scrollbar-thumb:hover {
  background: var(--color-bg-hover);
}

/* Fade transition */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 150ms ease-out;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
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
