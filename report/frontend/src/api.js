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

// API endpoints
export const filesAPI = {
  // Get all files
  getFiles: () => api.get('/files'),
  
  // Get file metrics
  getFileMetrics: (filePath) => api.get(`/file-metrics/${filePath}`),
  
  // Get file AI issues
  getFileAIIssues: (filePath) => api.get(`/file-ai-issues/${filePath}`),
  
  // Get file ESLint flags
  getFileESLint: (filePath) => api.get(`/file-eslint/${filePath}`),
  
  // Get file accessibility defects
  getFileAccessibility: (filePath) => api.get(`/file-accessibility/${filePath}`),
  
  // Get file API calls
  getFileAPICalls: (filePath) => api.get(`/file-api-calls/${filePath}`),
  
  // Get project summary
  getSummary: () => api.get('/summary'),
  
  // Get executive summary
  getExecutiveSummary: () => api.get('/executive-summary'),
  
  // Get worst offenders
  getWorstOffenders: (limit = 10) => api.get(`/worst-offenders?limit=${limit}`),
  
  // Get dependency summary
  getDependencySummary: () => api.get('/dependency-summary'),
  
  // Get full dependency graph
  getDependencyGraph: () => api.get('/dependency-graph'),

  // Get dependency data for a specific file (imports, dependents, impact, cycle)
  getFileDependencies: (filePath) => api.get(`/file-dependencies/${filePath}`),

}

export default api
