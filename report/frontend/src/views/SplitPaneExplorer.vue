<template>
  <div class="explorer">
    <!-- Left: File List -->
    <div class="file-pane">
      <div class="file-pane-header">
        <div class="search-wrap">
          <svg class="search-icon" width="13" height="13" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="6.5" cy="6.5" r="5"/><path d="M10.5 10.5L14 14"/>
          </svg>
          <input
            v-model="searchQuery"
            type="text"
            placeholder="Search files..."
            class="search-input"
          />
        </div>
        <div class="file-count-badge">
          {{ filteredFiles.length }}
        </div>
      </div>

      <div class="file-list">
        <!-- Loading -->
        <div v-if="loading" class="file-list-loading">
          <div v-for="i in 8" :key="i" class="skeleton" :style="`height:40px;margin-bottom:4px;opacity:${1-i*0.1}`"></div>
        </div>

        <!-- Error -->
        <div v-else-if="error" class="file-list-error">
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" opacity="0.4">
            <circle cx="12" cy="12" r="10"/><path d="M12 8v4M12 16h.01"/>
          </svg>
          <p>{{ error }}</p>
          <button class="retry-btn" @click="fetchFiles">Retry</button>
        </div>

        <!-- Files -->
        <div v-else-if="filteredFiles.length > 0">
          <div
            v-for="(file, i) in filteredFiles"
            :key="i"
            class="file-row"
            :class="{ active: selectedFile?.file_path === file.file_path }"
            @click="selectFile(file)"
          >
            <div class="file-row-left">
              <svg class="file-icon" width="13" height="13" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5">
                <path d="M4 2h5l4 4v8a1 1 0 01-1 1H4a1 1 0 01-1-1V3a1 1 0 011-1z"/>
                <path d="M9 2v4h4"/>
                <path d="M6 9h4M6 12h2"/>
              </svg>
              <span class="file-name">{{ getFileName(file.file_path) }}</span>
            </div>
            <div
              class="issue-badge"
              :class="getIssueBadgeClass(file)"
            >
              {{ getTotalIssues(file) }}
            </div>
          </div>
        </div>

        <!-- Empty -->
        <div v-else class="file-list-empty">
          <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1" opacity="0.2">
            <path d="M22 19a2 2 0 01-2 2H4a2 2 0 01-2-2V5a2 2 0 012-2h5l2 3h9a2 2 0 012 2z"/>
          </svg>
          <p>No files found</p>
        </div>
      </div>
    </div>

    <!-- Right: Detail -->
    <div class="detail-pane">
      <FileDetailView v-if="selectedFilePath" :filePath="selectedFilePath" />
      <div v-else class="detail-empty">
        <div class="detail-empty-icon">
          <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <circle cx="11" cy="11" r="8"/><path d="M21 21l-4.35-4.35"/>
            <path d="M11 7v4M11 15h.01"/>
          </svg>
        </div>
        <h3>Select a file</h3>
        <p>Choose a file from the left panel to view its audit details, issues, and code snippets.</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { filesAPI } from '../api.js'
import FileDetailView from '../components/FileDetailView.vue'

const route = useRoute()
const files = ref([])
const loading = ref(false)
const error = ref(null)
const searchQuery = ref('')
const selectedFile = ref(null)
const selectedFilePath = ref(null)

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

<style scoped>
.explorer {
  display: flex;
  height: 100%;
  overflow: hidden;
}

/* File Pane */
.file-pane {
  width: 260px;
  min-width: 260px;
  background: var(--color-bg-secondary);
  border-right: 1px solid var(--color-border);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.file-pane-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px;
  border-bottom: 1px solid var(--color-border);
  flex-shrink: 0;
}

.search-wrap {
  position: relative;
  flex: 1;
}

.search-icon {
  position: absolute;
  left: 9px;
  top: 50%;
  transform: translateY(-50%);
  color: var(--color-text-tertiary);
  pointer-events: none;
}

.search-input {
  width: 100%;
  padding: 7px 10px 7px 28px;
  background: var(--color-bg-tertiary);
  border: 1px solid var(--color-border-emphasis);
  border-radius: var(--rounded-base);
  color: var(--color-text-primary);
  font-size: 12px;
  outline: none;
  transition: all 150ms;
}

.search-input:focus {
  border-color: var(--color-accent-primary);
  box-shadow: 0 0 0 2px rgba(56,139,253,0.15);
}

.search-input::placeholder { color: var(--color-text-tertiary); }

.file-count-badge {
  font-family: var(--font-mono);
  font-size: 10px;
  padding: 2px 6px;
  background: var(--color-bg-tertiary);
  border: 1px solid var(--color-border-emphasis);
  border-radius: var(--rounded-full);
  color: var(--color-text-tertiary);
  flex-shrink: 0;
}

.file-list {
  flex: 1;
  overflow-y: auto;
  padding: 6px;
}

.file-list-loading { padding: 8px; }

.file-list-error, .file-list-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 40px 16px;
  text-align: center;
  color: var(--color-text-tertiary);
  font-size: 12px;
}

.retry-btn {
  padding: 5px 12px;
  background: var(--color-accent-primary);
  color: white;
  border-radius: var(--rounded-base);
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: background 150ms;
}

.file-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 7px 8px;
  border-radius: var(--rounded-base);
  cursor: pointer;
  transition: background 120ms;
  gap: 6px;
  border-left: 2px solid transparent;
}

.file-row:hover { background: var(--color-bg-hover); }

.file-row.active {
  background: rgba(56,139,253,0.08);
  border-left-color: var(--color-accent-primary);
}

.file-row-left {
  display: flex;
  align-items: center;
  gap: 7px;
  min-width: 0;
  flex: 1;
}

.file-icon { color: var(--color-text-tertiary); flex-shrink: 0; }
.file-row.active .file-icon { color: var(--color-accent-hover); }

.file-name {
  font-family: var(--font-mono);
  font-size: 11.5px;
  color: var(--color-text-secondary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.file-row.active .file-name { color: var(--color-text-primary); }

.issue-badge {
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: 600;
  padding: 1px 6px;
  border-radius: var(--rounded-full);
  flex-shrink: 0;
}

.badge-zero { background: rgba(63,185,80,0.1);  color: var(--color-status-success); }
.badge-low  { background: rgba(63,185,80,0.1);  color: var(--color-status-success); }
.badge-med  { background: rgba(210,153,34,0.12); color: var(--color-status-warning); }
.badge-high { background: rgba(248,81,73,0.1);  color: var(--color-status-error); }

/* Detail Pane */
.detail-pane {
  flex: 1;
  overflow: hidden;
  background: var(--color-bg-primary);
}

.detail-empty {
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 40px;
  text-align: center;
}

.detail-empty-icon {
  width: 64px; height: 64px;
  border-radius: 50%;
  background: var(--color-bg-tertiary);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-text-tertiary);
  margin-bottom: 4px;
}

.detail-empty h3 {
  font-size: 16px;
  font-weight: 600;
  color: var(--color-text-primary);
}

.detail-empty p {
  font-size: 13px;
  color: var(--color-text-secondary);
  max-width: 300px;
  line-height: 1.6;
}
</style>
