import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { useMutation } from 'react-query';
import { toast } from 'react-toastify';
import { authApi } from '@/services/api';
import { RegisterData } from '@/types';
import LoadingSpinner from '@/components/ui/LoadingSpinner';

const RegisterPage: React.FC = () => {
  const navigate = useNavigate();
  const [showPassword, setShowPassword] = useState(false);

  const {
    register,
    handleSubmit,
    watch,
    formState: { errors },
  } = useForm<RegisterData & { confirmPassword: string }>();

  const password = watch('password');

  const registerMutation = useMutation(authApi.register, {
    onSuccess: () => {
      toast.success('註冊成功！請登入您的帳號');
      navigate('/login');
    },
    onError: (error: any) => {
      const message = error.message || '註冊失敗';
      toast.error(message);
    },
  });

  const onSubmit = (data: RegisterData & { confirmPassword: string }) => {
    const { confirmPassword, ...registerData } = data;
    registerMutation.mutate(registerData);
  };

  return (
    <div className="min-h-screen bg-bg-primary flex items-center justify-center px-4 py-8">
      {/* Background Effects */}
      <div className="absolute inset-0 overflow-hidden">
        <div className="absolute -top-1/2 -left-1/2 w-full h-full bg-gradient-to-br from-rog-primary/10 to-transparent rounded-full blur-3xl"></div>
        <div className="absolute -bottom-1/2 -right-1/2 w-full h-full bg-gradient-to-br from-rog-accent/10 to-transparent rounded-full blur-3xl"></div>
      </div>

      <div className="relative z-10 w-full max-w-2xl">
        {/* Logo Section */}
        <div className="text-center mb-8">
          <div className="w-20 h-20 bg-gradient-to-r from-rog-primary to-rog-accent rounded-xl flex items-center justify-center mx-auto mb-4">
            <img src="/thsr-sniper-logo.svg" alt="THSR Sniper" className="w-16 h-16" />
          </div>
          <h1 className="text-3xl font-bold text-text-primary font-gaming mb-2">
            建立新帳號
          </h1>
          <p className="text-text-muted">加入 THSR Sniper 開始自動搶票</p>
        </div>

        {/* Register Form */}
        <form onSubmit={handleSubmit(onSubmit)} className="rog-card">
          <div className="rog-card-header">
            <h2 className="rog-card-title">
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M18 9v3m0 0v3m0-3h3m-3 0h-3m-2-5a4 4 0 11-8 0 4 4 0 018 0zM3 20a6 6 0 0112 0v1H3v-1z" />
              </svg>
              用戶註冊
            </h2>
          </div>

          <div className="space-y-6">
            {/* Basic Information */}
            <div className="form-grid">
              <div className="form-group">
                <label htmlFor="username" className="form-label">
                  用戶名稱 *
                </label>
                <input
                  {...register('username', {
                    required: '請輸入用戶名稱',
                    minLength: {
                      value: 3,
                      message: '用戶名稱至少需要3個字符'
                    },
                    pattern: {
                      value: /^[a-zA-Z0-9_]+$/,
                      message: '用戶名稱只能包含字母、數字和底線'
                    }
                  })}
                  type="text"
                  id="username"
                  className="rog-input"
                  placeholder="輸入用戶名稱"
                  autoComplete="username"
                />
                {errors.username && (
                  <p className="text-rog-danger text-sm mt-1">
                    {errors.username.message}
                  </p>
                )}
              </div>

              <div className="form-group">
                <label htmlFor="email" className="form-label">
                  電子郵件 *
                </label>
                <input
                  {...register('email', {
                    required: '請輸入電子郵件',
                    pattern: {
                      value: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
                      message: '請輸入有效的電子郵件格式'
                    }
                  })}
                  type="email"
                  id="email"
                  className="rog-input"
                  placeholder="輸入電子郵件"
                  autoComplete="email"
                />
                {errors.email && (
                  <p className="text-rog-danger text-sm mt-1">
                    {errors.email.message}
                  </p>
                )}
              </div>
            </div>

            {/* Full Name */}
            <div className="form-group">
              <label htmlFor="full_name" className="form-label">
                真實姓名
              </label>
              <input
                {...register('full_name')}
                type="text"
                id="full_name"
                className="rog-input"
                placeholder="輸入真實姓名（選填）"
                autoComplete="name"
              />
            </div>

            {/* Password Fields */}
            <div className="form-grid">
              <div className="form-group">
                <label htmlFor="password" className="form-label">
                  密碼 *
                </label>
                <div className="relative">
                  <input
                    {...register('password', {
                      required: '請輸入密碼',
                      minLength: {
                        value: 8,
                        message: '密碼至少需要8個字符'
                      },
                      pattern: {
                        value: /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]/,
                        message: '密碼必須包含大小寫字母、數字和特殊字符'
                      }
                    })}
                    type={showPassword ? 'text' : 'password'}
                    id="password"
                    className="rog-input pr-12"
                    placeholder="輸入密碼"
                    autoComplete="new-password"
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

              <div className="form-group">
                <label htmlFor="confirmPassword" className="form-label">
                  確認密碼 *
                </label>
                <input
                  {...register('confirmPassword', {
                    required: '請確認密碼',
                    validate: value => value === password || '密碼不一致'
                  })}
                  type={showPassword ? 'text' : 'password'}
                  id="confirmPassword"
                  className="rog-input"
                  placeholder="再次輸入密碼"
                  autoComplete="new-password"
                />
                {errors.confirmPassword && (
                  <p className="text-rog-danger text-sm mt-1">
                    {errors.confirmPassword.message}
                  </p>
                )}
              </div>
            </div>

            {/* THSR Information */}
            <div className="border-t border-gray-700 pt-6">
              <h3 className="text-lg font-semibold text-text-primary mb-4 flex items-center gap-2">
                <svg className="w-5 h-5 text-rog-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                </svg>
                高鐵資訊設定
              </h3>
              
              <div className="form-grid">
                <div className="form-group">
                  <label htmlFor="thsr_personal_id" className="form-label">
                    身分證字號
                  </label>
                  <input
                    {...register('thsr_personal_id', {
                      pattern: {
                        value: /^[A-Z][12][0-9]{8}$/,
                        message: '請輸入有效的身分證字號格式'
                      }
                    })}
                    type="text"
                    id="thsr_personal_id"
                    className="rog-input"
                    placeholder="A123456789"
                    maxLength={10}
                  />
                  {errors.thsr_personal_id && (
                    <p className="text-rog-danger text-sm mt-1">
                      {errors.thsr_personal_id.message}
                    </p>
                  )}
                </div>

                <div className="form-group">
                  <label className="form-label">會員設定</label>
                  <div className="flex items-center gap-3 pt-1">
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        {...register('thsr_use_membership')}
                        type="checkbox"
                        className="w-4 h-4 text-rog-primary bg-bg-input border-gray-600 rounded focus:ring-rog-primary focus:ring-2"
                      />
                      <span className="text-text-secondary">使用高鐵會員</span>
                    </label>
                  </div>
                </div>
              </div>
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              disabled={registerMutation.isLoading}
              className="rog-btn rog-btn-primary w-full flex items-center justify-center gap-2"
            >
              {registerMutation.isLoading ? (
                <>
                  <LoadingSpinner size="small" />
                  註冊中...
                </>
              ) : (
                <>
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M18 9v3m0 0v3m0-3h3m-3 0h-3m-2-5a4 4 0 11-8 0 4 4 0 018 0zM3 20a6 6 0 0112 0v1H3v-1z" />
                  </svg>
                  建立帳號
                </>
              )}
            </button>
          </div>

          {/* Login Link */}
          <div className="mt-6 text-center">
            <p className="text-text-muted">
              已經有帳號了？{' '}
              <Link
                to="/login"
                className="text-rog-primary hover:text-rog-primary-light font-medium transition-colors"
              >
                立即登入
              </Link>
            </p>
          </div>
        </form>
      </div>
    </div>
  );
};

export default RegisterPage;
