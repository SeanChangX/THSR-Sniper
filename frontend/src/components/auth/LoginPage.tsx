import React, { useState } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { useMutation } from 'react-query';
import { toast } from 'react-toastify';
import { useAuthStore } from '@/store/authStore';
import { authApi, authClient, apiClient } from '@/services/api';
import { LoginCredentials } from '@/types';
import LoadingSpinner from '@/components/ui/LoadingSpinner';

const LoginPage: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { setAuth } = useAuthStore();
  const [showPassword, setShowPassword] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginCredentials>();

  const loginMutation = useMutation(authApi.login, {
    onSuccess: async (tokens) => {
      try {
        console.log('Login successful, received tokens:', { 
          access_token: tokens.access_token.substring(0, 20) + '...',
          token_type: tokens.token_type 
        });
        
        // Store token immediately in localStorage for interceptors
        localStorage.setItem('auth_token', tokens.access_token);
        localStorage.setItem('refresh_token', tokens.refresh_token);
        
        console.log('Stored tokens in localStorage');
        
        // Set token in axios headers for immediate use
        authClient.defaults.headers.common['Authorization'] = `Bearer ${tokens.access_token}`;
        apiClient.defaults.headers.common['Authorization'] = `Bearer ${tokens.access_token}`;
        
        console.log('Set axios headers for both clients');
        
        // Get user data after successful login
        const user = await authApi.getCurrentUserWithToken(tokens.access_token);
        console.log('Retrieved user data:', user);
        
        // Set auth state
        setAuth(user, tokens);
        console.log('Set auth state');
        
        toast.success('登入成功');
        
        // Redirect to intended page or dashboard
        const from = (location.state as any)?.from?.pathname || '/dashboard';
        navigate(from, { replace: true });
      } catch (error) {
        console.error('Login error:', error);
        toast.error('無法獲取用戶資訊: ' + (error as any)?.message);
      }
    },
    onError: (error: any) => {
      const message = error.message || '登入失敗';
      toast.error(message);
    },
  });

  const onSubmit = (data: LoginCredentials) => {
    loginMutation.mutate(data);
  };

  return (
    <div className="min-h-screen bg-bg-primary flex items-center justify-center px-4">
      {/* Background Effects */}
      <div className="absolute inset-0 overflow-hidden">
        <div className="absolute -top-1/2 -left-1/2 w-full h-full bg-gradient-to-br from-rog-primary/10 to-transparent rounded-full blur-3xl"></div>
        <div className="absolute -bottom-1/2 -right-1/2 w-full h-full bg-gradient-to-br from-rog-accent/10 to-transparent rounded-full blur-3xl"></div>
      </div>

      <div className="relative z-10 w-full max-w-md">
        {/* Logo Section */}
        <div className="text-center mb-8">
          <div className="w-20 h-20 bg-gradient-to-r from-rog-primary to-rog-accent rounded-xl flex items-center justify-center mx-auto mb-4">
            <img src="/thsr-sniper-logo.svg" alt="THSR Sniper" className="w-16 h-16" />
          </div>
          <h1 className="text-3xl font-bold text-text-primary font-gaming mb-2">
            THSR Sniper
          </h1>
          <p className="text-text-muted">高鐵訂票系統</p>
        </div>

        {/* Login Form */}
        <form onSubmit={handleSubmit(onSubmit)} className="rog-card">
          <div className="rog-card-header">
            <h2 className="rog-card-title">
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 16l-4-4m0 0l4-4m-4 4h14m-6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
              </svg>
              用戶登入
            </h2>
          </div>

          <div className="space-y-4">
            {/* Username Field */}
            <div className="form-group">
              <label htmlFor="username" className="form-label">
                用戶名稱
              </label>
              <input
                {...register('username', {
                  required: '請輸入用戶名稱',
                  minLength: {
                    value: 3,
                    message: '用戶名稱至少需要3個字符'
                  }
                })}
                type="text"
                id="username"
                className="rog-input"
                placeholder="輸入您的用戶名稱"
                autoComplete="username"
              />
              {errors.username && (
                <p className="text-rog-danger text-sm mt-1">
                  {errors.username.message}
                </p>
              )}
            </div>

            {/* Password Field */}
            <div className="form-group">
              <label htmlFor="password" className="form-label">
                密碼
              </label>
              <div className="relative">
                <input
                  {...register('password', {
                    required: '請輸入密碼',
                    minLength: {
                      value: 6,
                      message: '密碼至少需要6個字符'
                    }
                  })}
                  type={showPassword ? 'text' : 'password'}
                  id="password"
                  className="rog-input pr-12"
                  placeholder="輸入您的密碼"
                  autoComplete="current-password"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 transform -translate-y-1/2 text-text-muted hover:text-text-primary"
                >
                  {showPassword ? (
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.878 9.878L3 3m6.878 6.878L21 21" />
                    </svg>
                  ) : (
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                    </svg>
                  )}
                </button>
              </div>
              {errors.password && (
                <p className="text-rog-danger text-sm mt-1">
                  {errors.password.message}
                </p>
              )}
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              disabled={loginMutation.isLoading}
              className="rog-btn rog-btn-primary w-full flex items-center justify-center gap-2"
            >
              {loginMutation.isLoading ? (
                <>
                  <LoadingSpinner size="small" />
                  登入中...
                </>
              ) : (
                <>
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 16l-4-4m0 0l4-4m-4 4h14m-6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                  </svg>
                  登入
                </>
              )}
            </button>
          </div>

          {/* Register Link */}
          <div className="mt-6 text-center">
            <p className="text-text-muted">
              還沒有帳號？{' '}
              <Link
                to="/register"
                className="text-rog-primary hover:text-rog-primary-light font-medium transition-colors"
              >
                立即註冊
              </Link>
            </p>
          </div>
        </form>


      </div>
    </div>
  );
};

export default LoginPage;
