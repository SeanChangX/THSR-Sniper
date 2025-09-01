import React, { useState, useEffect } from 'react';

interface NotificationItem {
  id: string;
  type: 'success' | 'error' | 'warning' | 'info';
  message: string;
  timestamp: Date;
}

const NotificationHistory: React.FC = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);

  useEffect(() => {
    // Load notifications from localStorage
    const savedNotifications = localStorage.getItem('notificationHistory');
    if (savedNotifications) {
      try {
        const parsed = JSON.parse(savedNotifications);
        setNotifications(parsed.map((n: any) => ({
          ...n,
          timestamp: new Date(n.timestamp)
        })));
      } catch (error) {
        console.error('Failed to parse notification history:', error);
      }
    }
  }, []);

  const clearHistory = () => {
    setNotifications([]);
    localStorage.removeItem('notificationHistory');
  };

  const getTypeColor = (type: NotificationItem['type']) => {
    switch (type) {
      case 'success': return 'text-rog-success';
      case 'error': return 'text-rog-danger';
      case 'warning': return 'text-rog-warning';
      case 'info': return 'text-rog-info';
      default: return 'text-text-secondary';
    }
  };

  const getTypeIcon = (type: NotificationItem['type']) => {
    switch (type) {
      case 'success':
        return (
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
        );
      case 'error':
        return (
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        );
      case 'warning':
        return (
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z" />
          </svg>
        );
      case 'info':
        return (
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        );
      default:
        return null;
    }
  };

  const formatTime = (date: Date) => {
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    const days = Math.floor(diff / 86400000);

    if (minutes < 1) return '剛剛';
    if (minutes < 60) return `${minutes}分鐘前`;
    if (hours < 24) return `${hours}小時前`;
    if (days < 7) return `${days}天前`;
    return date.toLocaleDateString('zh-TW');
  };

  return (
    <div className="relative">
      {/* Notification History Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="relative p-2 text-text-primary hover:bg-bg-input rounded-lg transition-colors"
        title="通知歷史"
      >
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 17h5l-5 5v-5zM4 19h6a2 2 0 002-2V7a2 2 0 00-2-2H4a2 2 0 00-2 2v10a2 2 0 002 2z" />
        </svg>
        {notifications.length > 0 && (
          <span className="absolute -top-1 -right-1 bg-rog-primary text-white text-xs rounded-full w-5 h-5 flex items-center justify-center">
            {notifications.length > 9 ? '9+' : notifications.length}
          </span>
        )}
      </button>

      {/* Notification History Panel */}
      {isOpen && (
        <div className="absolute right-0 top-full mt-2 w-80 bg-bg-card border border-gray-700 rounded-lg shadow-xl z-50 max-h-96 overflow-hidden">
          <div className="flex items-center justify-between p-3 border-b border-gray-700">
            <h3 className="text-sm font-medium text-text-primary">通知歷史</h3>
            <div className="flex items-center gap-2">
              <button
                onClick={clearHistory}
                className="text-text-muted hover:text-text-primary text-xs"
                title="清除歷史"
              >
                清除
              </button>
              <button
                onClick={() => setIsOpen(false)}
                className="text-text-muted hover:text-text-primary"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          </div>
          
          <div className="overflow-y-auto max-h-80">
            {notifications.length === 0 ? (
              <div className="p-4 text-center text-text-muted text-sm">
                暫無通知記錄
              </div>
            ) : (
              <div className="p-2">
                {notifications.map((notification) => (
                  <div
                    key={notification.id}
                    className="flex items-start gap-3 p-3 hover:bg-bg-input rounded-lg transition-colors"
                  >
                    <div className={`flex-shrink-0 ${getTypeColor(notification.type)}`}>
                      {getTypeIcon(notification.type)}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm text-text-primary break-words">
                        {notification.message}
                      </p>
                      <p className="text-xs text-text-muted mt-1">
                        {formatTime(notification.timestamp)}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default NotificationHistory;
