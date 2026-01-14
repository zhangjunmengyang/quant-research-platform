import axios, { type AxiosError, type AxiosInstance } from 'axios'

// API base URL - uses Vite proxy in development
const API_BASE_URL = import.meta.env.VITE_API_URL || '/api/v1'

// Create axios instance with default config
export const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor
apiClient.interceptors.request.use(
  (config) => {
    // Add auth token if available (SSR-safe)
    if (typeof window !== 'undefined') {
      const token = localStorage.getItem('token')
      if (token) {
        config.headers.Authorization = `Bearer ${token}`
      }
    }
    return config
  },
  (error) => Promise.reject(error)
)

// Response interceptor
apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError<ApiErrorResponse>) => {
    // Handle common errors
    if (error.response?.status === 401) {
      if (typeof window !== 'undefined') {
        localStorage.removeItem('token')
      }
      // Optionally redirect to login
    }

    // Extract error message
    const message =
      error.response?.data?.error || error.response?.data?.detail || error.message || 'Unknown error'

    return Promise.reject(new Error(message))
  }
)

// API response types
export interface ApiResponse<T> {
  success: boolean
  data: T | null
  error: string | null
  message: string | null
  timestamp: string
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
  total_pages: number
  has_next: boolean
  has_prev: boolean
}

export interface ApiErrorResponse {
  success: false
  error: string
  detail?: string
  code?: string
}

// Helper function to extract data from API response
export function unwrapResponse<T>(response: ApiResponse<T>): T {
  if (!response.success || response.data === null) {
    throw new Error(response.error || 'Request failed')
  }
  return response.data
}
