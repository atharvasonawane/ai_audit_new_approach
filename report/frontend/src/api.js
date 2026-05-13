import axios from 'axios'

// Create axios instance with base URL
const api = axios.create({
  baseURL: 'http://localhost:5000/api',
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
  
  // Get file details by ID
  getFileById: (fileId) => api.get(`/files/${fileId}`),
  
  // Get file issues
  getFileIssues: (fileId) => api.get(`/files/${fileId}/issues`),
}

export default api
