import React, { useState } from 'react';
import { useForm } from 'react-hook-form';
import { useMutation, useQuery, useQueryClient } from 'react-query';
import { toast } from 'react-toastify';
import { useAuthStore } from '@/store/authStore';
import { authApi } from '@/services/api';
import { UserUpdate, PasswordChange } from '@/types';
import LoadingSpinner from '@/components/ui/LoadingSpinner';
import { formatDateWithTimezone } from '@/utils/dateTime';

const ProfilePage: React.FC = () => {
  const { user, setUser, setTHSRInfo } = useAuthStore();
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<'profile' | 'thsr' | 'password'>('profile');

  // Fetch THSR info
  const { data: thsrInfo, isLoading: thsrLoading } = useQuery(
    'thsrInfo',
    authApi.getTHSRInfo,
    {
      onSuccess: (data) => {
        setTHSRInfo(data);
      }
    }
  );

  // Profile form
  const {
    register: registerProfile,
    handleSubmit: handleProfileSubmit,
    formState: { errors: profileErrors }
  } = useForm<UserUpdate>({
    defaultValues: {
      full_name: user?.full_name || '',
      email: user?.email || '',
    }
  });

  // THSR form
  const {
    register: registerTHSR,
    handleSubmit: handleTHSRSubmit,
    formState: { errors: thsrErrors },
    setValue: setTHSRValue
  } = useForm<Pick<UserUpdate, 'thsr_personal_id' | 'thsr_use_membership'>>();

  // Password form
  const {
    register: registerPassword,
    handleSubmit: handlePasswordSubmit,
    formState: { errors: passwordErrors },
    reset: resetPassword,
    watch
  } = useForm<PasswordChange>();

  // Update profile mutation
  const updateProfileMutation = useMutation(authApi.updateProfile, {
    onSuccess: (updatedUser) => {
      setUser(updatedUser);
      toast.success('個人資料更新成功');
      queryClient.invalidateQueries('currentUser');
    },
    onError: (error: any) => {
      toast.error(`更新失敗：${error.message}`);
    },
  });

  // Change password mutation
  const changePasswordMutation = useMutation(authApi.changePassword, {
    onSuccess: () => {
      toast.success('密碼修改成功，請重新登入');
      resetPassword();
      // Redirect to login after password change
      setTimeout(() => {
        window.location.href = '/login';
      }, 2000);
    },
    onError: (error: any) => {
      toast.error(`密碼修改失敗：${error.message}`);
    },
  });

  // Set THSR form values when data loads
  React.useEffect(() => {
    if (thsrInfo) {
      setTHSRValue('thsr_personal_id', thsrInfo.personal_id || '');
      setTHSRValue('thsr_use_membership', thsrInfo.use_membership);
    }
  }, [thsrInfo, setTHSRValue]);

  const onProfileSubmit = (data: UserUpdate) => {
    updateProfileMutation.mutate(data);
  };

  const onTHSRSubmit = (data: Pick<UserUpdate, 'thsr_personal_id' | 'thsr_use_membership'>) => {
    updateProfileMutation.mutate(data);
  };

  const onPasswordSubmit = (data: PasswordChange) => {
    const { confirm_password, ...passwordData } = data;
    changePasswordMutation.mutate(passwordData);
  };

  const password = watch('new_password');

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="rog-card">
        <div className="rog-card-header">
          <h1 className="rog-card-title text-2xl">
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
            </svg>
            個人設定
          </h1>
        </div>
        <p className="text-text-muted">
          管理您的個人資料和帳號設定
        </p>
      </div>

      {/* Tabs */}
      <div className="rog-card">
        <div className="flex flex-wrap gap-1 border-b border-gray-700 pb-4">
          <button
            onClick={() => setActiveTab('profile')}
            className={`nav-tab ${activeTab === 'profile' ? 'active' : ''}`}
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
            </svg>
            基本資料
          </button>
          <button
            onClick={() => setActiveTab('thsr')}
            className={`nav-tab ${activeTab === 'thsr' ? 'active' : ''}`}
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
            </svg>
            高鐵設定
          </button>
          <button
            onClick={() => setActiveTab('password')}
            className={`nav-tab ${activeTab === 'password' ? 'active' : ''}`}
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
            </svg>
            修改密碼
          </button>
        </div>

        {/* Profile Tab */}
        {activeTab === 'profile' && (
          <form onSubmit={handleProfileSubmit(onProfileSubmit)} className="mt-6 space-y-6">
            <div className="form-grid">
              <div className="form-group">
                <label htmlFor="username" className="form-label">用戶名稱</label>
                <input
                  type="text"
                  id="username"
                  value={user?.username || ''}
                  disabled
                  className="rog-input opacity-50 cursor-not-allowed"
                />
                <p className="text-text-muted text-sm mt-1">用戶名稱無法修改</p>
              </div>

              <div className="form-group">
                <label htmlFor="email" className="form-label">電子郵件</label>
                <input
                  {...registerProfile('email', {
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
                />
                {profileErrors.email && (
                  <p className="text-rog-danger text-sm mt-1">{profileErrors.email.message}</p>
                )}
              </div>
            </div>

            <div className="form-group">
              <label htmlFor="full_name" className="form-label">真實姓名</label>
              <input
                {...registerProfile('full_name')}
                type="text"
                id="full_name"
                className="rog-input"
                placeholder="輸入真實姓名"
              />
            </div>

            <div className="flex justify-end">
              <button
                type="submit"
                disabled={updateProfileMutation.isLoading}
                className="rog-btn rog-btn-primary flex items-center gap-2"
              >
                {updateProfileMutation.isLoading ? (
                  <>
                    <LoadingSpinner size="small" />
                    更新中...
                  </>
                ) : (
                  <>
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                    更新資料
                  </>
                )}
              </button>
            </div>
          </form>
        )}

        {/* THSR Tab */}
        {activeTab === 'thsr' && (
          <div className="mt-6">
            {thsrLoading ? (
              <div className="flex items-center justify-center py-8">
                <LoadingSpinner />
              </div>
            ) : (
              <form onSubmit={handleTHSRSubmit(onTHSRSubmit)} className="space-y-6">
                <div className="bg-rog-info/10 border border-rog-info/30 rounded-lg p-4">
                  <div className="flex items-start gap-3">
                    <svg className="w-5 h-5 text-rog-info mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <div>
                      <h4 className="font-semibold text-rog-info mb-1">資料安全說明</h4>
                      <p className="text-text-muted text-sm">
                        您的身分證字號將被加密保護，僅用於高鐵訂票服務。
                      </p>
                    </div>
                  </div>
                </div>

                <div className="form-group">
                  <label htmlFor="thsr_personal_id" className="form-label">身分證字號</label>
                  <input
                    {...registerTHSR('thsr_personal_id', {
                      pattern: {
                        value: /^[A-Z][12][0-9]{8}$/,
                        message: '請輸入有效的身分證字號格式（如：A123456789）'
                      }
                    })}
                    type="text"
                    id="thsr_personal_id"
                    className="rog-input"
                    placeholder="A123456789"
                    maxLength={10}
                  />
                  {thsrErrors.thsr_personal_id && (
                    <p className="text-rog-danger text-sm mt-1">{thsrErrors.thsr_personal_id.message}</p>
                  )}
                  <p className="text-text-muted text-sm mt-1">
                    訂票時需要使用身分證字號進行驗證
                  </p>
                </div>

                <div className="form-group">
                  <label className="form-label">會員設定</label>
                  <div className="flex items-center gap-3 pt-1">
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        {...registerTHSR('thsr_use_membership')}
                        type="checkbox"
                        className="w-4 h-4 text-rog-primary bg-bg-input border-gray-600 rounded focus:ring-rog-primary focus:ring-2"
                      />
                      <span className="text-text-secondary">使用高鐵會員帳號訂票</span>
                    </label>
                  </div>
                  <p className="text-text-muted text-sm mt-1">
                    會員可享有優先訂票和累積點數等優惠
                  </p>
                </div>

                <div className="flex justify-end">
                  <button
                    type="submit"
                    disabled={updateProfileMutation.isLoading}
                    className="rog-btn rog-btn-primary flex items-center gap-2"
                  >
                    {updateProfileMutation.isLoading ? (
                      <>
                        <LoadingSpinner size="small" />
                        更新中...
                      </>
                    ) : (
                      <>
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                        </svg>
                        更新設定
                      </>
                    )}
                  </button>
                </div>
              </form>
            )}
          </div>
        )}

        {/* Password Tab */}
        {activeTab === 'password' && (
          <form onSubmit={handlePasswordSubmit(onPasswordSubmit)} className="mt-6 space-y-6">
            <div className="bg-rog-warning/10 border border-rog-warning/30 rounded-lg p-4">
              <div className="flex items-start gap-3">
                <svg className="w-5 h-5 text-rog-warning mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
                <div>
                  <h4 className="font-semibold text-rog-warning mb-1">安全提醒</h4>
                  <p className="text-text-muted text-sm">
                    修改密碼後，您需要重新登入。請確保密碼包含大小寫字母、數字和特殊字符。
                  </p>
                </div>
              </div>
            </div>

            <div className="form-group">
              <label htmlFor="current_password" className="form-label">目前密碼</label>
              <input
                {...registerPassword('current_password', {
                  required: '請輸入目前密碼'
                })}
                type="password"
                id="current_password"
                className="rog-input"
                placeholder="輸入目前密碼"
              />
              {passwordErrors.current_password && (
                <p className="text-rog-danger text-sm mt-1">{passwordErrors.current_password.message}</p>
              )}
            </div>

            <div className="form-group">
              <label htmlFor="new_password" className="form-label">新密碼</label>
              <input
                {...registerPassword('new_password', {
                  required: '請輸入新密碼',
                  minLength: {
                    value: 8,
                    message: '密碼至少需要8個字符'
                  },
                  pattern: {
                    value: /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]/,
                    message: '密碼必須包含大小寫字母、數字和特殊字符'
                  }
                })}
                type="password"
                id="new_password"
                className="rog-input"
                placeholder="輸入新密碼"
              />
              {passwordErrors.new_password && (
                <p className="text-rog-danger text-sm mt-1">{passwordErrors.new_password.message}</p>
              )}
            </div>

            <div className="form-group">
              <label htmlFor="confirm_password" className="form-label">確認新密碼</label>
              <input
                {...registerPassword('confirm_password', {
                  required: '請確認新密碼',
                  validate: (value: string | undefined) => !value || value === password || '密碼不一致'
                })}
                type="password"
                id="confirm_password"
                className="rog-input"
                placeholder="再次輸入新密碼"
              />
              {passwordErrors.confirm_password && (
                <p className="text-rog-danger text-sm mt-1">{passwordErrors.confirm_password.message}</p>
              )}
            </div>

            <div className="flex justify-end">
              <button
                type="submit"
                disabled={changePasswordMutation.isLoading}
                className="rog-btn rog-btn-danger flex items-center gap-2"
              >
                {changePasswordMutation.isLoading ? (
                  <>
                    <LoadingSpinner size="small" />
                    修改中...
                  </>
                ) : (
                  <>
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                    </svg>
                    修改密碼
                  </>
                )}
              </button>
            </div>
          </form>
        )}
      </div>

      {/* Account Info */}
      <div className="rog-card">
        <div className="rog-card-header">
          <h3 className="rog-card-title">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            帳號資訊
          </h3>
        </div>
        <div className="text-center">
          <div className="inline-block">
            <p className="text-text-muted text-sm">註冊時間</p>
            <p className="text-text-primary font-medium">
{user?.created_at ? formatDateWithTimezone(user.created_at) : '-'}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ProfilePage;
