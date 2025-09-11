import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { User, Token, THSRInfo } from '@/types';

interface AuthState {
  user: User | null;
  token: string | null;
  refreshToken: string | null;
  isAuthenticated: boolean;
  thsrInfo: THSRInfo | null;
  
  // Actions
  setAuth: (user: User, tokens: Token) => void;
  setUser: (user: User) => void;
  setTHSRInfo: (info: THSRInfo) => void;
  updateToken: (token: string) => void;
  logout: () => void;
  clearAuth: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      token: null,
      refreshToken: null,
      isAuthenticated: false,
      thsrInfo: null,

      setAuth: (user: User, tokens: Token) => {
        set({
          user,
          token: tokens.access_token,
          refreshToken: tokens.refresh_token,
          isAuthenticated: true,
        });
        // Store token for persistence - only in localStorage, let zustand handle the rest
        if (typeof window !== 'undefined') {
          localStorage.setItem('auth_token', tokens.access_token);
          localStorage.setItem('refresh_token', tokens.refresh_token);
        }
      },

      setUser: (user: User) => {
        set({ user });
      },

      setTHSRInfo: (info: THSRInfo) => {
        set({ thsrInfo: info });
      },

      updateToken: (token: string) => {
        set({ token });
      },

      logout: () => {
        set({
          user: null,
          token: null,
          refreshToken: null,
          isAuthenticated: false,
          thsrInfo: null,
        });
        // Clear all auth-related localStorage
        localStorage.removeItem('auth-storage');
        localStorage.removeItem('auth_token');
        localStorage.removeItem('refresh_token');
        // Clear notification history to prevent data leakage
        localStorage.removeItem('notificationHistory');
      },

      clearAuth: () => {
        get().logout();
      },
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({
        user: state.user,
        token: state.token,
        refreshToken: state.refreshToken,
        isAuthenticated: state.isAuthenticated,
        thsrInfo: state.thsrInfo,
      }),
    }
  )
);
