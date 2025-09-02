import axios, { AxiosRequestConfig, AxiosResponse } from 'axios';
import { toast } from 'react-toastify';
import { 
  User, Token, LoginCredentials, RegisterData, UserUpdate, 
  PasswordChange, THSRInfo, StationInfo, TimeSlotInfo,
  BookingRequest, ScheduledBookingRequest, BookingResponse,
  TaskStatusResponse, SchedulerStatus, BookingStats,
  BookingTask, PaginatedResponse
} from '@/types';

// API Configuration
const API_BASE_URL = import.meta.env.VITE_API_URL || '/api';
const AUTH_BASE_URL = import.meta.env.VITE_AUTH_URL || '/auth';

// Create axios instances
export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
});

export const authClient = axios.create({
  baseURL: AUTH_BASE_URL,
  timeout: 10000,
});

// Token management
let isRefreshing = false;
let failedQueue: Array<{
  resolve: (value?: any) => void;
  reject: (reason?: any) => void;
}> = [];

const processQueue = (error: any, token: string | null = null) => {
  failedQueue.forEach(({ resolve, reject }) => {
    if (error) {
      reject(error);
    } else {
      resolve(token);
    }
  });
  
  failedQueue = [];
};

// Request interceptor to add auth token
const addAuthInterceptor = (client: any) => {
  client.interceptors.request.use(
    (config: AxiosRequestConfig) => {
      // Check multiple sources for token
      let token = localStorage.getItem('auth_token');
      
      if (!token) {
        try {
          const authStorage = localStorage.getItem('auth-storage');
          if (authStorage) {
            const parsed = JSON.parse(authStorage);
            token = parsed?.state?.token || null;
          }
        } catch (e) {
          console.error('Error parsing auth storage:', e);
        }
      }
      
      if (token) {
        config.headers = config.headers || {};
        config.headers.Authorization = `Bearer ${token}`;
        console.log('Added Authorization header:', `Bearer ${token.substring(0, 20)}...`);
      } else {
        console.log('No token found in localStorage');
      }
      
      return config;
    },
    (error: any) => Promise.reject(error)
  );
};

// Response interceptor for token refresh
const addResponseInterceptor = (client: any) => {
  client.interceptors.response.use(
    (response: AxiosResponse) => response,
    async (error: any) => {
      const originalRequest = error.config;

      if (error.response?.status === 401 && !originalRequest._retry) {
        if (isRefreshing) {
          return new Promise((resolve, reject) => {
            failedQueue.push({ resolve, reject });
          }).then(token => {
            originalRequest.headers.Authorization = `Bearer ${token}`;
            return client(originalRequest);
          }).catch(err => {
            return Promise.reject(err);
          });
        }

        originalRequest._retry = true;
        isRefreshing = true;

        try {
          const refreshToken = localStorage.getItem('auth-storage')
            ? JSON.parse(localStorage.getItem('auth-storage')!)?.state?.refreshToken
            : null;

          if (!refreshToken) {
            throw new Error('No refresh token available');
          }

          const response = await authClient.post('/refresh', {
            refresh_token: refreshToken
          });

          const newToken = response.data.access_token;
          
          // Update stored token
          const authStorage = JSON.parse(localStorage.getItem('auth-storage') || '{}');
          if (authStorage.state) {
            authStorage.state.token = newToken;
            authStorage.state.refreshToken = response.data.refresh_token;
            localStorage.setItem('auth-storage', JSON.stringify(authStorage));
          }

          processQueue(null, newToken);
          originalRequest.headers.Authorization = `Bearer ${newToken}`;
          
          return client(originalRequest);
        } catch (refreshError) {
          processQueue(refreshError, null);
          
          // Clear auth data and redirect to login
          localStorage.removeItem('auth-storage');
          window.location.href = '/login';
          
          return Promise.reject(refreshError);
        } finally {
          isRefreshing = false;
        }
      }

      return Promise.reject(error);
    }
  );
};

// Add interceptors to both clients
addAuthInterceptor(apiClient);
addAuthInterceptor(authClient);
addResponseInterceptor(apiClient);
addResponseInterceptor(authClient);

// Error deduplication cache
let lastErrorTime = 0;
let lastErrorMessage = '';

// Error handler
const handleApiError = (error: any, showToast = true) => {
  const message = error.response?.data?.detail || 
                  error.response?.data?.message || 
                  error.message || 
                  'An unexpected error occurred';
  
  // Don't show toast for authentication errors that are expected
  const shouldShowToast = showToast && !(error.response?.status === 401 || error.response?.status === 403);
  
  // Deduplicate identical error messages within 1 second
  const now = Date.now();
  const isDuplicate = lastErrorMessage === message && (now - lastErrorTime) < 1000;
  
  if (shouldShowToast && !isDuplicate) {
    toast.error(message);
    lastErrorTime = now;
    lastErrorMessage = message;
  }
  
  throw new Error(message);
};

// Authentication API
export const authApi = {
  async login(credentials: LoginCredentials): Promise<Token> {
    try {
      const response = await authClient.post('/login', credentials);
      return response.data;
    } catch (error) {
      handleApiError(error);
      throw error;
    }
  },

  async register(userData: RegisterData): Promise<User> {
    try {
      const response = await authClient.post('/register', userData);
      return response.data;
    } catch (error) {
      handleApiError(error);
      throw error;
    }
  },

  async logout(): Promise<void> {
    try {
      await authClient.post('/logout');
    } catch (error) {
      // Don't throw on logout error, just log it
      console.error('Logout error:', error);
    }
  },

  async getCurrentUser(): Promise<User> {
    try {
      const response = await authClient.get('/me');
      return response.data;
    } catch (error) {
      handleApiError(error);
      throw error;
    }
  },

  async getCurrentUserWithToken(token: string): Promise<User> {
    try {
      const response = await authClient.get('/me', {
        headers: { Authorization: `Bearer ${token}` }
      });
      return response.data;
    } catch (error) {
      handleApiError(error);
      throw error;
    }
  },

  async updateProfile(userData: UserUpdate): Promise<User> {
    try {
      const response = await authClient.put('/me', userData);
      return response.data;
    } catch (error) {
      handleApiError(error);
      throw error;
    }
  },

  async changePassword(passwordData: PasswordChange): Promise<void> {
    try {
      await authClient.post('/change-password', passwordData);
    } catch (error) {
      handleApiError(error);
      throw error;
    }
  },

  async getTHSRInfo(): Promise<THSRInfo> {
    try {
      const response = await authClient.get('/thsr-info');
      return response.data;
    } catch (error) {
      handleApiError(error);
      throw error;
    }
  },

  async refreshToken(refreshToken: string): Promise<Token> {
    try {
      const response = await authClient.post('/refresh', {
        refresh_token: refreshToken
      });
      return response.data;
    } catch (error) {
      handleApiError(error, false); // Don't show toast for refresh errors
      throw error;
    }
  },
};

// THSR Booking API
export const thsrApi = {
  async getStations(): Promise<StationInfo[]> {
    try {
      const response = await apiClient.get('/stations');
      return response.data;
    } catch (error) {
      handleApiError(error);
      throw error;
    }
  },

  async getTimeSlots(): Promise<TimeSlotInfo[]> {
    try {
      const response = await apiClient.get('/times');
      return response.data;
    } catch (error) {
      handleApiError(error);
      throw error;
    }
  },

  async immediateBooking(bookingData: BookingRequest): Promise<BookingResponse> {
    try {
      const response = await apiClient.post('/book', bookingData);
      return response.data;
    } catch (error) {
      handleApiError(error);
      throw error;
    }
  },

  async scheduleBooking(bookingData: ScheduledBookingRequest): Promise<BookingResponse> {
    try {
      const response = await apiClient.post('/schedule', bookingData);
      return response.data;
    } catch (error) {
      handleApiError(error);
      throw error;
    }
  },

  async getTasks(): Promise<TaskStatusResponse[]> {
    try {
      const response = await apiClient.get('/tasks');
      return response.data;
    } catch (error) {
      handleApiError(error);
      throw error;
    }
  },

  async getTask(taskId: string): Promise<TaskStatusResponse> {
    try {
      const response = await apiClient.get(`/tasks/${taskId}`);
      return response.data;
    } catch (error) {
      handleApiError(error);
      throw error;
    }
  },

  async cancelTask(taskId: string): Promise<BookingResponse> {
    try {
      const response = await apiClient.delete(`/tasks/${taskId}`);
      return response.data;
    } catch (error) {
      handleApiError(error);
      throw error;
    }
  },

  async removeTask(taskId: string): Promise<BookingResponse> {
    try {
      const response = await apiClient.delete(`/tasks/${taskId}/remove`);
      return response.data;
    } catch (error) {
      handleApiError(error);
      throw error;
    }
  },

  async getSchedulerStatus(): Promise<SchedulerStatus> {
    try {
      const response = await apiClient.get('/scheduler/status');
      return response.data;
    } catch (error) {
      handleApiError(error);
      throw error;
    }
  },



  async getResults(params?: {
    status?: string;
    limit?: number;
    offset?: number;
  }): Promise<PaginatedResponse<BookingTask>> {
    try {
      const response = await apiClient.get('/results', { params });
      return response.data;
    } catch (error) {
      handleApiError(error);
      throw error;
    }
  },

  async getResultsStats(): Promise<BookingStats> {
    try {
      const response = await apiClient.get('/results/stats');
      return response.data;
    } catch (error) {
      handleApiError(error);
      throw error;
    }
  },

  async getTaskResult(taskId: string): Promise<{ success: boolean; task: BookingTask }> {
    try {
      const response = await apiClient.get(`/results/${taskId}`);
      return response.data;
    } catch (error) {
      handleApiError(error);
      throw error;
    }
  },

  async testTHSRConnectivity(): Promise<{
    status: 'online' | 'offline' | 'degraded' | 'timeout' | 'error';
    response_time_ms?: number;
    message: string;
    tested_at: number;
    session_info?: string;
  }> {
    try {
      const response = await apiClient.get('/health/thsr');
      return response.data;
    } catch (error) {
      handleApiError(error);
      throw error;
    }
  },
};

// Health check
export const healthApi = {
  async checkAPI(): Promise<boolean> {
    try {
      await apiClient.get('/');
      return true;
    } catch (error) {
      return false;
    }
  },

  async checkAuth(): Promise<boolean> {
    try {
      await authClient.get('/me');
      return true;
    } catch (error) {
      return false;
    }
  },
};

export default {
  auth: authApi,
  thsr: thsrApi,
  health: healthApi,
};
