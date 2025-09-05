import React, { useEffect, useRef } from 'react';
import { useAuthStore } from '@/store/authStore';
import { isTokenExpired, getTokenExpiryInfo } from '@/utils/tokenUtils';

interface TokenMonitorProps {
  onTokenExpired?: () => void;
}

const TokenMonitor: React.FC<TokenMonitorProps> = ({ onTokenExpired }) => {
  const { logout, isAuthenticated } = useAuthStore();
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    if (!isAuthenticated) {
      // Clear interval if not authenticated
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
      return;
    }

    const checkToken = () => {
      const token = localStorage.getItem('auth_token');
      
      if (token) {
        const tokenInfo = getTokenExpiryInfo(token);
        
        if (tokenInfo.isExpired) {
          console.log('Token expired during monitoring, logging out...');
          if (onTokenExpired) {
            onTokenExpired();
          } else {
            // Default behavior: clear storage and logout
            localStorage.removeItem('auth-storage');
            localStorage.removeItem('auth_token');
            localStorage.removeItem('refresh_token');
            localStorage.removeItem('notificationHistory');
            logout();
          }
        } else if (tokenInfo.isExpiringSoon) {
          console.log(`Token expiring soon: ${Math.round(tokenInfo.timeUntilExpiry / 1000)}s remaining`);
        }
      }
    };

    // Check immediately
    checkToken();

    // Set up interval to check every 10 seconds
    intervalRef.current = setInterval(checkToken, 10000);

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [isAuthenticated, logout, onTokenExpired]);

  return null; // This component doesn't render anything
};

export default TokenMonitor;
