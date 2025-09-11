import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from 'react-query';
import { toast } from 'react-toastify';
import { thsrApi } from '@/services/api';
import { BOOKING_STATUS } from '@/types';
import LoadingSpinner from '@/components/ui/LoadingSpinner';
import { formatStationRoute } from '@/utils/stations';
import { formatDateTimeWithTimezone, getEffectiveTaskStatus } from '@/utils/dateTime';

// Helper function to format passenger counts
const formatPassengerCounts = (task: any) => {
  const counts = [];
  
  if (task.adult_cnt && task.adult_cnt > 0) {
    counts.push(`成人 ${task.adult_cnt}`);
  }
  if (task.student_cnt && task.student_cnt > 0) {
    counts.push(`學生 ${task.student_cnt}`);
  }
  if (task.child_cnt && task.child_cnt > 0) {
    counts.push(`兒童 ${task.child_cnt}`);
  }
  if (task.senior_cnt && task.senior_cnt > 0) {
    counts.push(`敬老 ${task.senior_cnt}`);
  }
  if (task.disabled_cnt && task.disabled_cnt > 0) {
    counts.push(`愛心 ${task.disabled_cnt}`);
  }
  
  return counts.length > 0 ? counts.join(' + ') : '無乘客';
};

// Helper function to clean ANSI color codes from PNR
const cleanPNR = (pnr: string | null | undefined): string => {
  if (!pnr) return '未知';
  // Remove ANSI color codes (e.g., \u001b[38;5;46m04349325\u001b[0m)
  return pnr.replace(/\u001b\[[0-9;]*m/g, '').trim();
};

// Helper function to format departure time
const formatDepartureTime = (timeIndex: number | undefined, timeSlots: any[]): string => {
  if (!timeIndex || !timeSlots || timeSlots.length === 0) {
    return '不指定時間';
  }
  
  const timeSlot = timeSlots.find(slot => slot.id === timeIndex);
  if (timeSlot) {
    return `${timeSlot.formatted_time} (${timeSlot.time})`;
  }
  
  return `時間索引 ${timeIndex}`;
};

const TasksPage: React.FC = () => {
  const queryClient = useQueryClient();
  const [selectedStatus, setSelectedStatus] = useState<string>('all');

  // Fetch tasks with improved error handling
  const { data: tasksData, isLoading, refetch } = useQuery(
    ['tasks', selectedStatus],
    () => thsrApi.getResults({
      status: selectedStatus === 'all' ? undefined : selectedStatus,
      limit: 50
    }),
    { 
      refetchInterval: 5000,
      onError: (error: any) => {
        if (error.response?.status === 401 || error.response?.status === 403) {
          console.log('Authentication error in tasks query');
          // Error will be handled by global query client
        }
      }
    }
  );

  const { data: stations = [] } = useQuery(
    'stations', 
    thsrApi.getStations,
    {
      onError: (error: any) => {
        if (error.response?.status === 401 || error.response?.status === 403) {
          console.log('Authentication error in stations query');
          // Error will be handled by global query client
        }
      }
    }
  );

  const { data: timeSlots = [] } = useQuery(
    'timeSlots', 
    thsrApi.getTimeSlots,
    {
      onError: (error: any) => {
        if (error.response?.status === 401 || error.response?.status === 403) {
          console.log('Authentication error in timeSlots query');
          // Error will be handled by global query client
        }
      }
    }
  );

  // Cancel task mutation
  const cancelTaskMutation = useMutation(thsrApi.cancelTask, {
    onSuccess: () => {
      toast.success('任務已取消');
      queryClient.invalidateQueries(['tasks']);
    },
    onError: (error: any) => {
      toast.error(`取消失敗：${error.message}`);
    },
  });

  // Remove task mutation
  const removeTaskMutation = useMutation(thsrApi.removeTask, {
    onSuccess: () => {
      toast.success('任務已刪除');
      queryClient.invalidateQueries(['tasks']);
    },
    onError: (error: any) => {
      toast.error(`刪除失敗：${error.message}`);
    },
  });

  const handleCancelTask = (taskId: string) => {
    if (window.confirm('確定要取消這個任務嗎？')) {
      cancelTaskMutation.mutate(taskId);
    }
  };

  const handleRemoveTask = (taskId: string) => {
    if (window.confirm('確定要刪除這個任務嗎？此操作無法復原。')) {
      removeTaskMutation.mutate(taskId);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'success':
        return 'text-rog-success';
      case 'failed':
        return 'text-rog-danger';
      case 'running':
        return 'text-rog-info';
      case 'pending':
        return 'text-rog-warning';
      case 'waiting':
        return 'text-rog-info';
      case 'cancelled':
        return 'text-text-muted';
      case 'expired':
        return 'text-text-muted';
      default:
        return 'text-text-secondary';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'success':
        return (
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        );
      case 'failed':
        return (
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        );
      case 'running':
        return (
          <svg className="w-4 h-4 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
        );
      case 'pending':
        return (
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        );
      case 'waiting':
        return (
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        );
      default:
        return (
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v10a2 2 0 002 2h8a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
          </svg>
        );
    }
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="rog-card">
        <div className="rog-card-header">
          <h1 className="rog-card-title text-2xl">
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v10a2 2 0 002 2h8a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
            </svg>
            任務管理
          </h1>
          <button
            onClick={() => refetch()}
            className="rog-btn rog-btn-secondary flex items-center gap-2"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            刷新
          </button>
        </div>
        <p className="text-text-muted">
          管理您的訂票任務，查看執行狀態和結果
        </p>
      </div>

      {/* Status Filter */}
      <div className="rog-card">
        <div className="flex flex-wrap gap-2">
          <button
            onClick={() => setSelectedStatus('all')}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
              selectedStatus === 'all'
                ? 'bg-rog-primary text-white'
                : 'bg-bg-input text-text-secondary hover:bg-bg-tertiary'
            }`}
          >
            全部
          </button>
          {Object.entries(BOOKING_STATUS)
            .filter(([key]) => key !== 'expired')
            .map(([key, label]) => (
            <button
              key={key}
              onClick={() => setSelectedStatus(key)}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                selectedStatus === key
                  ? 'bg-rog-primary text-white'
                  : 'bg-bg-input text-text-secondary hover:bg-bg-tertiary'
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* Tasks List */}
      <div className="rog-card">
        {isLoading ? (
          <div className="flex items-center justify-center py-8">
            <LoadingSpinner size="large" />
          </div>
        ) : tasksData?.results && tasksData.results.length > 0 ? (
          <div className="space-y-4">
            {tasksData.results.map((task) => {
              const effectiveStatus = getEffectiveTaskStatus(task);
              return (
              <div key={task.id} className="border border-gray-700 rounded-lg p-4 hover:border-rog-primary/30 transition-colors">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      <div className={`flex items-center gap-2 ${getStatusColor(effectiveStatus)}`}>
                        {getStatusIcon(effectiveStatus)}
                        <span className="font-medium">
                          {BOOKING_STATUS[effectiveStatus as keyof typeof BOOKING_STATUS]}
                        </span>
                      </div>
                      <span className="text-text-muted text-sm">
                        #{task.id.slice(-8)}
                      </span>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-3">
                      <div>
                        <p className="text-text-muted text-sm">路線</p>
                        <p className="text-text-primary font-medium">
{formatStationRoute(task.from_station, task.to_station, stations)}
                        </p>
                      </div>
                      <div>
                        <p className="text-text-muted text-sm">出發日期</p>
                        <p className="text-text-primary">{task.date}</p>
                      </div>
                      <div>
                        <p className="text-text-muted text-sm">出發時間</p>
                        <p className="text-text-primary">
                          {formatDepartureTime(task.time, timeSlots)}
                        </p>
                      </div>
                      <div>
                        <p className="text-text-muted text-sm">乘客</p>
                        <p className="text-text-primary">
                          {formatPassengerCounts(task)}
                        </p>
                      </div>
                      <div>
                        <p className="text-text-muted text-sm">重試間隔</p>
                        <p className="text-text-primary">{task.interval_minutes} 分鐘</p>
                      </div>
                      <div>
                        <p className="text-text-muted text-sm">嘗試次數</p>
                        <p className="text-text-primary">
                          {task.attempts} {task.max_attempts ? `/ ${task.max_attempts}` : ''}
                        </p>
                      </div>
                      <div>
                        <p className="text-text-muted text-sm">建立時間</p>
                        <p className="text-text-primary">
                          {formatDateTimeWithTimezone(task.created_at)}
                        </p>
                      </div>
                    </div>

                    {effectiveStatus === 'success' && (
                      <div className="bg-rog-success/10 border border-rog-success/30 rounded-lg p-3 mb-3">
                        <p className="text-rog-success font-medium">
                          訂票成功！PNR代碼：{cleanPNR(task.success_pnr || task.result)}
                        </p>
                      </div>
                    )}

                    {effectiveStatus === 'failed' && task.error && (
                      <div className="bg-rog-danger/10 border border-rog-danger/30 rounded-lg p-3 mb-3">
                        <p className="text-rog-danger">
                          錯誤：{task.error}
                        </p>
                      </div>
                    )}

                    {effectiveStatus === 'expired' && task.status !== 'expired' && (
                      <div className="bg-rog-warning/10 border border-rog-warning/30 rounded-lg p-3 mb-3">
                        <p className="text-rog-warning font-medium">
                          此任務已過期（出發日期已過）
                        </p>
                      </div>
                    )}

                    {task.last_attempt && (
                      <p className="text-text-muted text-sm">
                        最後嘗試：{formatDateTimeWithTimezone(task.last_attempt)}
                      </p>
                    )}
                  </div>

                  {/* Action Buttons */}
                  <div className="flex items-center gap-2 ml-4">
                    {(effectiveStatus === 'pending' || effectiveStatus === 'running') && (
                      <button
                        onClick={() => handleCancelTask(task.id)}
                        disabled={cancelTaskMutation.isLoading}
                        className="rog-btn rog-btn-warning flex items-center gap-1 text-sm px-3 py-2"
                      >
                        {cancelTaskMutation.isLoading ? (
                          <LoadingSpinner size="small" />
                        ) : (
                          <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                          </svg>
                        )}
                        取消
                      </button>
                    )}
                    
                    {(effectiveStatus === 'success' || effectiveStatus === 'failed' || effectiveStatus === 'cancelled' || effectiveStatus === 'expired') && (
                      <button
                        onClick={() => handleRemoveTask(task.id)}
                        disabled={removeTaskMutation.isLoading}
                        className="rog-btn rog-btn-danger flex items-center gap-1 text-sm px-3 py-2"
                      >
                        {removeTaskMutation.isLoading ? (
                          <LoadingSpinner size="small" />
                        ) : (
                          <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                          </svg>
                        )}
                        刪除
                      </button>
                    )}
                  </div>
                </div>
              </div>
              );
            })}
          </div>
        ) : (
          <div className="text-center py-12">
            <svg className="w-16 h-16 text-text-muted mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v10a2 2 0 002 2h8a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
            </svg>
            <h3 className="text-lg font-medium text-text-primary mb-2">暫無任務</h3>
            <p className="text-text-muted mb-4">您還沒有任何訂票任務</p>
            <a href="/booking" className="rog-btn rog-btn-primary">
              建立第一個任務
            </a>
          </div>
        )}
      </div>

      {/* Pagination */}
      {tasksData && tasksData.total > tasksData.limit && (
        <div className="rog-card">
          <div className="flex items-center justify-between">
            <p className="text-text-muted text-sm">
              顯示 {tasksData.offset + 1} - {Math.min(tasksData.offset + tasksData.limit, tasksData.total)} 
              {' '}共 {tasksData.total} 項
            </p>
            {/* Pagination controls can be added here */}
          </div>
        </div>
      )}
    </div>
  );
};

export default TasksPage;
