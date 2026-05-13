<template>
  <div id="app">
    <!-- Left Sidebar: File Explorer -->
    <aside class="sidebar">
      <div class="sidebar-header">
        <h1 class="sidebar-title">Code Audit Librarian</h1>
        <div class="project-name">{{ projectName }}</div>
      </div>

      <!-- Search/Filter -->
      <div class="search-box">
        <input
          v-model="searchQuery"
          type="text"
          placeholder="Search files..."
          class="search-input"
        />
      </div>

      <!-- Loading State -->
      <div v-if="loading" class="loading-state">
        <div class="spinner"></div>
        <p>Loading files...</p>
      </div>

      <!-- Error State -->
      <div v-else-if="error" class="error-state">
        <div class="error-icon">⚠</div>
        <p class="error-message">{{ error }}</p>
        <button @click="fetchFiles" class="retry-button">Retry</button>
      </div>

      <!-- File List -->
      <div v-else class="file-list">
        <div
          v-for="file in filteredFiles"
          :key="file.file_path"
          :class="['file-item', { active: selectedFile === file.file_path }]"
          @click="selectFile(file.file_path)"
        >
          <div class="file-name">{{ getFileName(file.file_path) }}</div>
          <div class="file-path">{{ file.file_path }}</div>
          <div class="file-badges">
            <span v-if="file.high_severity_count > 0" class="badge badge-high">
              {{ file.high_severity_count }} High
            </span>
            <span v-if="file.medium_severity_count > 0" class="badge badge-medium">
              {{ file.medium_severity_count }} Med
            </span>
            <span v-if="file.eslint_flag_count > 0" class="badge badge-eslint">
              {{ file.eslint_flag_count }} ESLint
            </span>
            <span v-if="file.accessibility_count > 0" class="badge badge-a11y">
              {{ file.accessibility_count }} A11y
            </span>
          </div>
        </div>

        <div v-if="filteredFiles.length === 0" class="no-results">
          No files match your search.
        </div>
      </div>

      <!-- Stats Footer -->
      <div v-if="!loading && !error" class="sidebar-footer">
        <div class="stat">
          <span class="stat-label">Total Files:</span>
          <span class="stat-value">{{ files.length }}</span>
        </div>
        <div class="stat">
          <span class="stat-label">Filtered:</span>
          <span class="stat-value">{{ filteredFiles.length }}</span>
        </div>
      </div>
    </aside>

    <!-- Right Main Area -->
    <main class="main-content">
      <div v-if="!selectedFile" class="welcome-screen">
        <div class="welcome-icon">📊</div>
        <h2>Welcome to Code Audit Librarian</h2>
        <p>Select a file from the sidebar to view detailed analysis</p>
        <div class="welcome-stats">
          <div class="welcome-stat">
            <div class="welcome-stat-value">{{ files.length }}</div>
            <div class="welcome-stat-label">Files Scanned</div>
          </div>
          <div class="welcome-stat">
            <div class="welcome-stat-value">{{ totalIssues }}</div>
            <div class="welcome-stat-label">Total Issues</div>
          </div>
        </div>
      </div>

      <div v-else class="file-detail">
        <div class="file-detail-header">
          <h2>{{ selectedFile }}</h2>
          <button @click="selectedFile = null" class="close-button">✕</button>
        </div>
        <div class="file-detail-content">
          <p class="placeholder-text">
            File detail tabs will be implemented in the next step.
          </p>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import axios from 'axios';

// API Configuration
const API_BASE_URL = 'http://localhost:5000/api';

// State
const files = ref([]);
const loading = ref(true);
const error = ref(null);
const selectedFile = ref(null);
const searchQuery = ref('');
const projectName = ref('Project');

// Computed
const filteredFiles = computed(() => {
  if (!searchQuery.value) {
    return files.value;
  }
  const query = searchQuery.value.toLowerCase();
  return files.value.filter(file =>
    file.file_path.toLowerCase().includes(query)
  );
});

const totalIssues = computed(() => {
  return files.value.reduce((sum, file) => {
    return sum + (file.ai_issue_count || 0) + (file.eslint_flag_count || 0) + (file.accessibility_count || 0);
  }, 0);
});

// Methods
const fetchFiles = async () => {
  loading.value = true;
  error.value = null;

  try {
    const response = await axios.get(`${API_BASE_URL}/files`);
    files.value = response.data;

    // Also fetch summary to get project name
    const summaryResponse = await axios.get(`${API_BASE_URL}/summary`);
    projectName.value = summaryResponse.data.project_name || 'Project';

    loading.value = false;
  } catch (err) {
    console.error('Failed to fetch files:', err);
    error.value = err.response?.data?.error || 'Failed to connect to API server. Make sure it\'s running on http://localhost:5000';
    loading.value = false;
  }
};

const selectFile = (filePath) => {
  selectedFile.value = filePath;
};

const getFileName = (filePath) => {
  return filePath.split('/').pop();
};

// Lifecycle
onMounted(() => {
  fetchFiles();
});
</script>

<style scoped>
/* CSS Reset & Base Styles */
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

#app {
  display: flex;
  height: 100vh;
  width: 100vw;
  overflow: hidden;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen',
    'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans', 'Helvetica Neue',
    sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  background: #0d1117;
  color: #c9d1d9;
}

/* Sidebar Styles */
.sidebar {
  width: 350px;
  background: #161b22;
  border-right: 1px solid #30363d;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.sidebar-header {
  padding: 20px;
  border-bottom: 1px solid #30363d;
  background: #0d1117;
}

.sidebar-title {
  font-size: 18px;
  font-weight: 600;
  color: #58a6ff;
  margin-bottom: 8px;
}

.project-name {
  font-size: 13px;
  color: #8b949e;
  font-family: 'Courier New', monospace;
}

/* Search Box */
.search-box {
  padding: 16px;
  border-bottom: 1px solid #30363d;
}

.search-input {
  width: 100%;
  padding: 8px 12px;
  background: #0d1117;
  border: 1px solid #30363d;
  border-radius: 6px;
  color: #c9d1d9;
  font-size: 14px;
  outline: none;
  transition: border-color 0.2s;
}

.search-input:focus {
  border-color: #58a6ff;
}

.search-input::placeholder {
  color: #6e7681;
}

/* Loading State */
.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  color: #8b949e;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 3px solid #30363d;
  border-top-color: #58a6ff;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin-bottom: 16px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* Error State */
.error-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  text-align: center;
}

.error-icon {
  font-size: 48px;
  margin-bottom: 16px;
}

.error-message {
  color: #f85149;
  font-size: 14px;
  margin-bottom: 20px;
  line-height: 1.5;
}

.retry-button {
  padding: 8px 16px;
  background: #238636;
  color: #ffffff;
  border: none;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.2s;
}

.retry-button:hover {
  background: #2ea043;
}

/* File List */
.file-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.file-list::-webkit-scrollbar {
  width: 8px;
}

.file-list::-webkit-scrollbar-track {
  background: #0d1117;
}

.file-list::-webkit-scrollbar-thumb {
  background: #30363d;
  border-radius: 4px;
}

.file-list::-webkit-scrollbar-thumb:hover {
  background: #484f58;
}

.file-item {
  padding: 12px;
  margin-bottom: 4px;
  background: #0d1117;
  border: 1px solid #30363d;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
}

.file-item:hover {
  background: #161b22;
  border-color: #58a6ff;
}

.file-item.active {
  background: #1f6feb;
  border-color: #1f6feb;
}

.file-item.active .file-name,
.file-item.active .file-path {
  color: #ffffff;
}

.file-name {
  font-size: 14px;
  font-weight: 500;
  color: #c9d1d9;
  margin-bottom: 4px;
  font-family: 'Courier New', monospace;
}

.file-path {
  font-size: 12px;
  color: #8b949e;
  margin-bottom: 8px;
  font-family: 'Courier New', monospace;
  word-break: break-all;
}

.file-badges {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.badge {
  padding: 2px 8px;
  font-size: 11px;
  font-weight: 600;
  border-radius: 12px;
  white-space: nowrap;
}

.badge-high {
  background: #da3633;
  color: #ffffff;
}

.badge-medium {
  background: #d29922;
  color: #000000;
}

.badge-eslint {
  background: #6e7681;
  color: #ffffff;
}

.badge-a11y {
  background: #8957e5;
  color: #ffffff;
}

.no-results {
  padding: 40px 20px;
  text-align: center;
  color: #8b949e;
  font-size: 14px;
}

/* Sidebar Footer */
.sidebar-footer {
  padding: 16px;
  border-top: 1px solid #30363d;
  background: #0d1117;
  display: flex;
  justify-content: space-between;
}

.stat {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.stat-label {
  font-size: 11px;
  color: #8b949e;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.stat-value {
  font-size: 18px;
  font-weight: 600;
  color: #58a6ff;
}

/* Main Content Area */
.main-content {
  flex: 1;
  background: #0d1117;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
}

.main-content::-webkit-scrollbar {
  width: 10px;
}

.main-content::-webkit-scrollbar-track {
  background: #0d1117;
}

.main-content::-webkit-scrollbar-thumb {
  background: #30363d;
  border-radius: 5px;
}

.main-content::-webkit-scrollbar-thumb:hover {
  background: #484f58;
}

/* Welcome Screen */
.welcome-screen {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  padding: 40px;
  text-align: center;
}

.welcome-icon {
  font-size: 80px;
  margin-bottom: 24px;
  opacity: 0.8;
}

.welcome-screen h2 {
  font-size: 32px;
  font-weight: 600;
  color: #c9d1d9;
  margin-bottom: 12px;
}

.welcome-screen p {
  font-size: 16px;
  color: #8b949e;
  margin-bottom: 40px;
}

.welcome-stats {
  display: flex;
  gap: 60px;
}

.welcome-stat {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.welcome-stat-value {
  font-size: 48px;
  font-weight: 700;
  color: #58a6ff;
}

.welcome-stat-label {
  font-size: 14px;
  color: #8b949e;
  text-transform: uppercase;
  letter-spacing: 1px;
}

/* File Detail View */
.file-detail {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.file-detail-header {
  padding: 24px 32px;
  border-bottom: 1px solid #30363d;
  background: #161b22;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.file-detail-header h2 {
  font-size: 20px;
  font-weight: 600;
  color: #c9d1d9;
  font-family: 'Courier New', monospace;
}

.close-button {
  width: 32px;
  height: 32px;
  background: transparent;
  border: 1px solid #30363d;
  border-radius: 6px;
  color: #8b949e;
  font-size: 18px;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
}

.close-button:hover {
  background: #30363d;
  color: #c9d1d9;
}

.file-detail-content {
  flex: 1;
  padding: 32px;
}

.placeholder-text {
  color: #8b949e;
  font-size: 16px;
  text-align: center;
  padding: 60px 20px;
}
</style>
