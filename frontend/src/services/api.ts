import axios, { AxiosRequestConfig, AxiosResponse } from 'axios';
import { toast } from 'react-toastify';
import { isTokenExpired } from '@/utils/tokenUtils';
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
      // Check multiple sources for token with priority order
      let token = null;
      
      // 1. Check localStorage first (most reliable)
      token = localStorage.getItem('auth_token');
      
      // 2. Check zustand store if localStorage is empty
      if (!token) {
        try {
          const authStorage = localStorage.getItem('auth-storage');
          if (authStorage) {
            const parsed = JSON.parse(authStorage);
            token = parsed?.state?.token || null;
            // Sync to localStorage for consistency
            if (token) {
              localStorage.setItem('auth_token', token);
            }
          }
        } catch (e) {
          console.error('Error parsing auth storage:', e);
        }
      }
      
      // Always add token if available
      if (token) {
        // Check if token is expired before adding to request
        if (isTokenExpired(token)) {
          console.log('Token is expired, triggering logout...');
          handleAuthenticationFailure();
          return Promise.reject(new Error('Token expired'));
        }
        
        config.headers = config.headers || {};
        config.headers.Authorization = `Bearer ${token}`;
        console.log('Token added to request:', config.url, 'Token:', token.substring(0, 20) + '...');
      } else {
        // For protected endpoints, reject the request immediately
        if (config.url && !config.url.includes('/auth/') && !config.url.includes('/login') && !config.url.includes('/register')) {
          console.warn('Attempting to access protected endpoint without token:', config.url);
        }
      }
      
      return config;
    },
    (error: any) => Promise.reject(error)
  );
};

// Response interceptor for token refresh and error handling
const addResponseInterceptor = (client: any) => {
  client.interceptors.response.use(
    (response: AxiosResponse) => response,
    async (error: any) => {
      const originalRequest = error.config;

      // Handle 401 errors (Unauthorized)
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
          const authStorage = localStorage.getItem('auth-storage');
          const refreshToken = authStorage
            ? JSON.parse(authStorage)?.state?.refreshToken
            : null;

          if (!refreshToken) {
            // Check if user was ever authenticated by looking for any auth data
            const hasAuthData = authStorage && JSON.parse(authStorage)?.state;
            const hadToken = hasAuthData?.token || hasAuthData?.user;
            throw new Error(hadToken ? 'Session expired' : 'Authentication required');
          }

          const response = await authClient.post('/refresh', {
            refresh_token: refreshToken
          });

          const newToken = response.data.access_token;
          const newRefreshToken = response.data.refresh_token;
          
          // Update stored token
          const parsedAuthStorage = JSON.parse(authStorage!);
          if (parsedAuthStorage.state) {
            parsedAuthStorage.state.token = newToken;
            parsedAuthStorage.state.refreshToken = newRefreshToken;
            localStorage.setItem('auth-storage', JSON.stringify(parsedAuthStorage));
            localStorage.setItem('auth_token', newToken);
            localStorage.setItem('refresh_token', newRefreshToken);
          }

          // Update axios default headers for both clients
          client.defaults.headers.common['Authorization'] = `Bearer ${newToken}`;
          // Also update the other client
          if (client === authClient) {
            apiClient.defaults.headers.common['Authorization'] = `Bearer ${newToken}`;
          } else if (client === apiClient) {
            authClient.defaults.headers.common['Authorization'] = `Bearer ${newToken}`;
          }

          processQueue(null, newToken);
          originalRequest.headers.Authorization = `Bearer ${newToken}`;
          
          return client(originalRequest);
        } catch (refreshError) {
          processQueue(refreshError, null);
          
          // Check error message to determine appropriate user feedback
          const errorMessage = refreshError instanceof Error ? refreshError.message : 'Authentication failed';
          
          console.log('Refresh token failed:', {
            error: refreshError,
            errorMessage,
            authStorage: localStorage.getItem('auth-storage')
          });
          
          if (errorMessage === 'Authentication required') {
            console.log('Authentication required for protected resource - forcing logout');
            // Don't show toast for unauthenticated users, just logout
          } else {
            console.log('Session expired, forcing logout...');
            // Only show toast if user was actually authenticated
            toast.error('Your session has expired. Please login again.');
          }
          
          // Force logout immediately
          handleAuthenticationFailure();
          
          return Promise.reject(refreshError);
        } finally {
          isRefreshing = false;
        }
      }

      // Handle other auth errors (403, etc.)
      if (error.response?.status === 403) {
        console.log('Access forbidden - insufficient permissions');
        toast.error('You do not have permission to access this resource.');
        // Don't force logout for 403 - user is authenticated but lacks permission
        return Promise.reject(error);
      }

      // Handle any other 401 errors that weren't caught above
      if (error.response?.status === 401) {
        console.log('401 error detected, forcing logout...');
        handleAuthenticationFailure();
        return Promise.reject(error);
      }

      return Promise.reject(error);
    }
  );
};

// Global authentication failure handler
const handleAuthenticationFailure = () => {
  // Clear all auth data
  localStorage.removeItem('auth-storage');
  localStorage.removeItem('auth_token');
  localStorage.removeItem('refresh_token');
  localStorage.removeItem('notificationHistory');
  
  // Force store reset by triggering a custom event
  window.dispatchEvent(new CustomEvent('auth-logout'));
  
  // Redirect to login page
  if (window.location.pathname !== '/login') {
    window.location.href = '/login';
  }
};

// Add interceptors to both clients
addAuthInterceptor(apiClient);
addAuthInterceptor(authClient);
addResponseInterceptor(apiClient);
addResponseInterceptor(authClient);

// Error deduplication cache
let lastErrorTime = 0;
let lastErrorMessage = '';

// Error handler with improved deduplication
const handleApiError = (error: any, showToast = true) => {
  const message = error.response?.data?.detail || 
                  error.response?.data?.message || 
                  error.message || 
                  'An unexpected error occurred';
  
  // Don't show toast for authentication errors that will trigger auto-logout
  const isAuthError = error.response?.status === 401 || error.response?.status === 403;
  const shouldShowToast = showToast && !isAuthError;
  
  // Deduplicate identical error messages within 2 seconds
  const now = Date.now();
  const isDuplicate = lastErrorMessage === message && (now - lastErrorTime) < 2000;
  
  if (shouldShowToast && !isDuplicate) {
    toast.error(message);
    lastErrorTime = now;
    lastErrorMessage = message;
  }
  
  throw new Error(message);
};

// Special error handler for login that always shows toast
const handleLoginError = (error: any) => {
  const message = error.response?.data?.detail || 
                  error.response?.data?.message || 
                  error.message || 
                  '登入失敗';
  
  toast.error(message);
  throw new Error(message);
};

// Authentication API
export const authApi = {
  async login(credentials: LoginCredentials): Promise<Token> {
    try {
      const response = await authClient.post('/login', credentials);
      return response.data;
    } catch (error) {
      handleLoginError(error);
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
