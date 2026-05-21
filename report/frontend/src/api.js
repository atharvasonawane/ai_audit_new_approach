import axios from 'axios'

// Create axios instance with base URL
const api = axios.create({
  baseURL: window.__FLASK_PORT__ ? `http://localhost:${window.__FLASK_PORT__}/api` : 'http://localhost:5000/api',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor for debugging
api.interceptors.request.use(
  (config) => {
    console.log('API Request:', config.method.toUpperCase(), config.url)
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => {
    return response
  },
  (error) => {
    if (error.response) {
      // Server responded with error status
      console.error('API Error:', error.response.status, error.response.data)
    } else if (error.request) {
      // Request made but no response
      console.error('API Error: No response received', error.request)
    } else {
      // Error in request setup
      console.error('API Error:', error.message)
    }
    return Promise.reject(error)
  }
)

// Helper to append run_id query param
const getRunQuery = (url, runId) => {
  if (!runId) return url
  return url.includes('?') ? `${url}&run_id=${runId}` : `${url}?run_id=${runId}`
}

// API endpoints
export const filesAPI = {
  // Get recent audits
  getRecentAudits: () => api.get('/recent-audits'),

  // Get all files
  getFiles: (runId) => api.get(getRunQuery('/files', runId)),
  
  // Get file metrics
  getFileMetrics: (filePath, runId) => api.get(getRunQuery(`/file-metrics/${filePath}`, runId)),
  
  // Get file AI issues
  getFileAIIssues: (filePath, runId) => api.get(getRunQuery(`/file-ai-issues/${filePath}`, runId)),
  
  // Get file ESLint flags
  getFileESLint: (filePath, runId) => api.get(getRunQuery(`/file-eslint/${filePath}`, runId)),
  
  // Get file accessibility defects
  getFileAccessibility: (filePath, runId) => api.get(getRunQuery(`/file-accessibility/${filePath}`, runId)),
  
  // Get file API calls
  getFileAPICalls: (filePath, runId) => api.get(getRunQuery(`/file-api-calls/${filePath}`, runId)),
  
  // Get project summary
  getSummary: (runId) => api.get(getRunQuery('/summary', runId)),
  
  // Get executive summary
  getExecutiveSummary: (runId) => api.get(getRunQuery('/executive-summary', runId)),
  
  // Get worst offenders
  getWorstOffenders: (limit = 10, runId) => api.get(getRunQuery(`/worst-offenders?limit=${limit}`, runId)),
  
  // Get dependency summary
  getDependencySummary: (runId) => api.get(getRunQuery('/dependency-summary', runId)),
  
  // Get full dependency graph
  getDependencyGraph: (runId) => api.get(getRunQuery('/dependency-graph', runId)),

  // Get dependency data for a specific file
  getFileDependencies: (filePath, runId) => api.get(getRunQuery(`/file-dependencies/${filePath}`, runId)),
}

export default api
