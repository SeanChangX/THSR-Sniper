import React from 'react';
import { Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { useQuery } from 'react-query';
import { useAuthStore } from '@/store/authStore';
import { authApi } from '@/services/api';

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

  // Auto-fetch user data if authenticated
  const { isLoading } = useQuery(
    'currentUser',
    authApi.getCurrentUser,
    {
      enabled: isAuthenticated && !!token,
      retry: false,
      onSuccess: (user) => {
        setUser(user);
      },
      onError: (err) => {
        console.error('Failed to fetch user data:', err);
        // Only logout if it's an authentication error (401/403)
        if (err && typeof err === 'object' && 'response' in err && 
            ((err.response as any)?.status === 401 || (err.response as any)?.status === 403)) {
          logout();
        }
      },
    }
  );

  // Show loading spinner while checking authentication
  if (isAuthenticated && isLoading) {
    return (
      <div className="min-h-screen bg-bg-primary flex items-center justify-center">
        <LoadingSpinner size="large" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-bg-primary">
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
