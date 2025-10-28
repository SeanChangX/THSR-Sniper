import React, { useState } from 'react';
import { Outlet, NavLink, useLocation } from 'react-router-dom';
import { useQueryClient } from 'react-query';
import { useAuthStore } from '@/store/authStore';
import { authApi } from '@/services/api';
import { toast } from 'react-toastify';
import NotificationHistory from '@/components/ui/NotificationHistory';

// Icons (using simple SVG for now, replace with your preferred icon library)
const DashboardIcon = () => (
  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" />
  </svg>
);

const BookingIcon = () => (
  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
  </svg>
);

const TasksIcon = () => (
  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v10a2 2 0 002 2h8a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01" />
  </svg>
);

const ProfileIcon = () => (
  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
  </svg>
);

const LogoutIcon = () => (
  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
  </svg>
);

const MenuIcon = () => (
  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
  </svg>
);

const CloseIcon = () => (
  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
  </svg>
);

const Layout: React.FC = () => {
  const { user, logout } = useAuthStore();
  const queryClient = useQueryClient();
  const location = useLocation();
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  const handleLogout = async () => {
    try {
      // Clear all React Query cache to prevent data leakage
      queryClient.clear();
      
      // Call logout API
      await authApi.logout();
      
      // Clear auth state and localStorage
      logout();

      toast.success('登出成功');
    } catch (error) {
      // Even if API call fails, we still logout locally
      queryClient.clear();
      logout();
      toast.success('登出成功');
    }
  };

  const navigation = [
    { name: '控制台', href: '/dashboard', icon: DashboardIcon },
    { name: '訂票', href: '/booking', icon: BookingIcon },
    { name: '任務管理', href: '/tasks', icon: TasksIcon },
    { name: '個人設定', href: '/profile', icon: ProfileIcon },
  ];

  const isActive = (path: string) => location.pathname === path;

  return (
    <div className="min-h-screen bg-bg-primary">
      {/* Header */}
      <header className="bg-bg-card border-b border-gray-800 shadow-lg">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16 header-content">
            {/* Logo */}
            <div className="flex items-center gap-2 sm:gap-3 min-w-0 flex-shrink-0">
              <div className="w-8 h-8 sm:w-10 sm:h-10 bg-gradient-to-r from-rog-primary to-rog-accent rounded-lg flex items-center justify-center flex-shrink-0">
                <img src="/thsr-sniper-logo.svg" alt="THSR Sniper" className="w-6 h-6 sm:w-8 sm:h-8" />
              </div>
              <div className="min-w-0">
                <h1 className="text-sm sm:text-xl font-bold text-text-primary font-gaming truncate">
                  THSR Sniper
                </h1>
                <p className="text-xs text-text-muted hidden sm:block">高鐵訂票系統</p>
              </div>
            </div>

            {/* Desktop Navigation */}
            <nav className="hidden lg:flex space-x-1">
              {navigation.map((item) => {
                const Icon = item.icon;
                return (
                  <NavLink
                    key={item.name}
                    to={item.href}
                    className={`nav-tab ${isActive(item.href) ? 'active' : ''}`}
                  >
                    <Icon />
                    <span className="hidden xl:inline">{item.name}</span>
                  </NavLink>
                );
              })}
            </nav>

            {/* Tablet Navigation (icons only) */}
            <nav className="hidden md:flex lg:hidden space-x-1">
              {navigation.map((item) => {
                const Icon = item.icon;
                return (
                  <NavLink
                    key={item.name}
                    to={item.href}
                    className={`nav-tab ${isActive(item.href) ? 'active' : ''}`}
                    title={item.name}
                  >
                    <Icon />
                  </NavLink>
                );
              })}
            </nav>

            {/* User Menu */}
            <div className="flex items-center gap-2 sm:gap-4 min-w-0">
              <div className="hidden md:block text-right min-w-0">
                <p className="text-sm font-medium text-text-primary truncate">
                  {user?.full_name || user?.username}
                </p>
                <p className="text-xs text-text-muted truncate">{user?.email}</p>
              </div>
              
              <NotificationHistory />
              
              <button
                onClick={handleLogout}
                className="rog-btn rog-btn-secondary flex items-center gap-1 sm:gap-2 px-2 sm:px-6 py-2 sm:py-3 text-xs sm:text-sm"
              >
                <LogoutIcon />
                <span className="hidden sm:inline">登出</span>
              </button>

              {/* Mobile menu button */}
              <button
                onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
                className="lg:hidden p-2 text-text-primary hover:bg-bg-input rounded-lg flex-shrink-0"
              >
                {isMobileMenuOpen ? <CloseIcon /> : <MenuIcon />}
              </button>
            </div>
          </div>
        </div>

        {/* Mobile Navigation */}
        {isMobileMenuOpen && (
          <div className="lg:hidden border-t border-gray-800 bg-bg-secondary">
            <div className="px-4 py-4 space-y-2">
              {/* User info on mobile */}
              <div className="pb-4 border-b border-gray-700">
                <p className="text-sm font-medium text-text-primary">
                  {user?.full_name || user?.username}
                </p>
                <p className="text-xs text-text-muted">{user?.email}</p>
              </div>
              
              {/* Navigation items */}
              {navigation.map((item) => {
                const Icon = item.icon;
                return (
                  <NavLink
                    key={item.name}
                    to={item.href}
                    onClick={() => setIsMobileMenuOpen(false)}
                    className={`flex items-center gap-3 px-3 py-2 rounded-lg transition-colors ${
                      isActive(item.href)
                        ? 'bg-rog-primary text-white'
                        : 'text-text-secondary hover:bg-bg-input hover:text-text-primary'
                    }`}
                  >
                    <Icon />
                    {item.name}
                  </NavLink>
                );
              })}
            </div>
          </div>
        )}
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 pb-20">
        <Outlet />
      </main>

      {/* Status Bar */}
      <div className="fixed bottom-0 left-0 right-0 bg-bg-card border-t border-gray-800 px-4 py-2">
        <div className="max-w-7xl mx-auto flex items-center justify-between text-sm">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <div className="status-dot online"></div>
              <span className="text-text-secondary">系統運行中</span>
            </div>
            <div className="flex items-center gap-3">
              <span className="text-text-muted">© 2025 THSR Sniper</span>
              <a
                href="https://github.com/SeanChangX/THSR-Sniper"
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-1.5 text-text-secondary hover:text-rog-primary transition-colors"
                title="View on GitHub"
              >
                <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                  <path fillRule="evenodd" d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z" clipRule="evenodd" />
                </svg>
                <span className="hidden sm:inline text-sm">GitHub</span>
              </a>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Layout;
