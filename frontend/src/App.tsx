import React, { useEffect } from 'react';
import { Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { useQuery, useQueryClient } from 'react-query';
import { useAuthStore } from '@/store/authStore';
import { authApi } from '@/services/api';
import VersionChecker from '@/components/VersionChecker';
import TokenMonitor from '@/components/TokenMonitor';
import { isTokenExpired } from '@/utils/tokenUtils';

// Components
import Layout from '@/components/Layout';
import LoginPage from '@/components/auth/LoginPage';
import RegisterPage from '@/components/auth/RegisterPage';
import Dashboard from '@/components/Dashboard';
import BookingPage from '@/components/booking/BookingPage';
import TasksPage from '@/components/tasks/TasksPage';
import ProfilePage from '@/components/profile/ProfilePage';
import LoadingSpinner from '@/components/ui/LoadingSpinner';

// Protected Route Component
const ProtectedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { isAuthenticated } = useAuthStore();
  const location = useLocation();

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return <>{children}</>;
};

// Public Route Component (redirect if authenticated)
const PublicRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { isAuthenticated } = useAuthStore();
  const location = useLocation();

  if (isAuthenticated) {
    const from = (location.state as any)?.from?.pathname || '/dashboard';
    return <Navigate to={from} replace />;
  }

  return <>{children}</>;
};

const App: React.FC = () => {
  const { isAuthenticated, setUser, logout, token } = useAuthStore();
  const queryClient = useQueryClient();

  // Version check is now handled by VersionChecker component

  // Global authentication failure handler
  useEffect(() => {
    const handleAuthLogout = () => {
      console.log('Received auth-logout event, clearing session...');
      queryClient.clear();
      logout();
    };

    // Listen for authentication failure events
    window.addEventListener('auth-logout', handleAuthLogout);
    
    return () => {
      window.removeEventListener('auth-logout', handleAuthLogout);
    };
  }, [logout, queryClient]);

  // Session validation on app start - check token expiry
  useEffect(() => {
    const validateSession = () => {
      const token = localStorage.getItem('auth_token');
      
      if (token) {
        console.log('Checking token expiry on app start...');
        if (isTokenExpired(token)) {
          console.log('Token is expired, clearing session...');
          queryClient.clear();
          localStorage.removeItem('auth-storage');
          localStorage.removeItem('auth_token');
          localStorage.removeItem('refresh_token');
          localStorage.removeItem('notificationHistory');
          // Force logout
          logout();
        } else {
          console.log('Token is still valid');
        }
      }
    };

    // Only run validation once on mount
    validateSession();
  }, []); // Remove dependencies to prevent infinite loops

  // Remove forced timeout - let authentication check work naturally

  // Auto-fetch user data if authenticated
  const { isLoading, isError, error } = useQuery(
    'currentUser',
    authApi.getCurrentUser,
    {
      enabled: isAuthenticated && !!token,
      retry: false, // Disable retry to prevent infinite loops
      staleTime: 0, // Always check fresh data
      onSuccess: (user) => {
        console.log('User data fetched successfully:', user);
        setUser(user);
      },
      onError: (err) => {
        console.error('Failed to fetch user data:', err);
        // Only logout if it's an authentication error (401/403)
        if (err && typeof err === 'object' && 'response' in err) {
          const status = (err as any).response?.status;
          if (status === 401 || status === 403) {
            console.log('Authentication error detected, logging out...');
            // Clear everything on auth error
            queryClient.clear();
            logout();
          }
        }
      },
    }
  );

  // Show loading spinner only when we have a token and are fetching user data
  // Don't show loading if there's an error or if we're not authenticated
  if (isAuthenticated && !!token && isLoading && !isError) {
    return (
      <div className="min-h-screen bg-bg-primary flex items-center justify-center">
        <LoadingSpinner size="large" />
      </div>
    );
  }

  // If we have an error and are authenticated, force logout immediately
  if (isAuthenticated && !!token && isError) {
    console.log('Authentication error detected, forcing logout immediately...');
    // Force logout immediately
    queryClient.clear();
    logout();
    return (
      <div className="min-h-screen bg-bg-primary flex items-center justify-center">
        <LoadingSpinner size="large" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-bg-primary">
      <VersionChecker />
      <TokenMonitor 
        onTokenExpired={() => {
          console.log('Token expired, clearing session...');
          queryClient.clear();
          localStorage.removeItem('auth-storage');
          localStorage.removeItem('auth_token');
          localStorage.removeItem('refresh_token');
          localStorage.removeItem('notificationHistory');
          logout();
        }}
      />
      <Routes>
        {/* Public Routes */}
        <Route 
          path="/login" 
          element={
            <PublicRoute>
              <LoginPage />
            </PublicRoute>
          } 
        />
        <Route 
          path="/register" 
          element={
            <PublicRoute>
              <RegisterPage />
            </PublicRoute>
          } 
        />

        {/* Protected Routes */}
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <Layout />
            </ProtectedRoute>
          }
        >
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard" element={<Dashboard />} />
          <Route path="booking" element={<BookingPage />} />
          <Route path="tasks" element={<TasksPage />} />
          <Route path="profile" element={<ProfilePage />} />
        </Route>

        {/* Catch all route */}
        <Route 
          path="*" 
          element={
            isAuthenticated ? (
              <Navigate to="/dashboard" replace />
            ) : (
              <Navigate to="/login" replace />
            )
          } 
        />
      </Routes>
    </div>
  );
};

export default App;
