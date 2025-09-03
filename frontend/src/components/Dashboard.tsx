import React from 'react';
import { useQuery } from 'react-query';
import { Link } from 'react-router-dom';
import { thsrApi } from '@/services/api';
import { useAuthStore } from '@/store/authStore';
import LoadingSpinner from '@/components/ui/LoadingSpinner';
import { formatStationRoute } from '@/utils/stations';

const Dashboard: React.FC = () => {
  const { user } = useAuthStore();

  // Fetch dashboard data with improved error handling
  const { data: schedulerStatus, isLoading: statusLoading } = useQuery(
    'schedulerStatus',
    thsrApi.getSchedulerStatus,
    { 
      refetchInterval: 600000, // 10 minutes
      onError: (error: any) => {
        if (error.response?.status === 401 || error.response?.status === 403) {
          console.log('Authentication error in scheduler status query');
          // Error will be handled by global query client
        }
      }
    }
  );

  const { data: stats, isLoading: statsLoading } = useQuery(
    'bookingStats',
    thsrApi.getResultsStats,
    { 
      refetchInterval: 10000,
      onError: (error: any) => {
        if (error.response?.status === 401 || error.response?.status === 403) {
          console.log('Authentication error in booking stats query');
          // Error will be handled by global query client
        }
      }
    }
  );

  const { data: tasks, isLoading: tasksLoading } = useQuery(
    'recentTasks',
    () => thsrApi.getResults({ limit: 5 }),
    { 
      refetchInterval: 5000,
      onError: (error: any) => {
        if (error.response?.status === 401 || error.response?.status === 403) {
          console.log('Authentication error in recent tasks query');
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

  return (
    <div className="space-y-8">
      {/* Welcome Section */}
      <div className="rog-card">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-text-primary font-gaming mb-2">
              歡迎回來，{user?.full_name || user?.username}！
            </h1>
            <p className="text-text-muted">
              Ride the Fast Rail, Book Even Faster.
            </p>
          </div>
          <div className="w-20 h-20 bg-gradient-to-r from-rog-primary to-rog-accent rounded-xl flex items-center justify-center">
            <img src="/thsr-sniper-logo.svg" alt="THSR Sniper" className="w-16 h-16" />
          </div>
        </div>
      </div>

      {/* Status Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {/* System Status */}
        <div className="rog-card">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-text-primary">系統狀態</h3>
            <div className={`status-dot ${schedulerStatus?.running ? 'online' : 'offline'}`}></div>
          </div>
          {statusLoading ? (
            <LoadingSpinner />
          ) : (
            <div>
              <p className="text-2xl font-bold text-text-primary mb-1">
                {schedulerStatus?.running ? '運行中' : '已停止'}
              </p>
              <p className="text-text-muted text-sm">
                總任務數: {schedulerStatus?.total_tasks || 0}
              </p>
              {/* THSR Connectivity Status - DISABLED */}
              {/* {schedulerStatus?.thsr_connectivity && (
                <div className="mt-2 pt-2 border-t border-border-subtle">
                  <div className="flex items-center gap-2">
                    <div className={`w-2 h-2 rounded-full ${
                      schedulerStatus.thsr_connectivity.status === 'online' ? 'bg-rog-success' :
                      schedulerStatus.thsr_connectivity.status === 'degraded' ? 'bg-rog-warning' :
                      'bg-rog-danger'
                    }`}></div>
                    <span className="text-xs text-text-muted">
                      {schedulerStatus.thsr_connectivity.status === 'online' ? '高鐵官網正常' :
                       schedulerStatus.thsr_connectivity.status === 'degraded' ? '高鐵官網異常' :
                       schedulerStatus.thsr_connectivity.status === 'timeout' ? '高鐵官網逾時' :
                       '高鐵官網離線'}
                    </span>
                  </div>
                  {schedulerStatus.thsr_connectivity.response_time_ms && (
                    <p className="text-xs text-text-muted">
                      回應時間: {schedulerStatus.thsr_connectivity.response_time_ms}ms
                    </p>
                  )}
                  {schedulerStatus.thsr_connectivity.status !== 'online' && (
                    <p className="text-xs text-rog-danger mt-1">
                      {schedulerStatus.thsr_connectivity.message}
                    </p>
                  )}
                </div>
              )} */}
            </div>
          )}
        </div>

        {/* Success Rate */}
        <div className="rog-card">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-text-primary">成功率</h3>
            <svg className="w-5 h-5 text-rog-success" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          {statsLoading ? (
            <LoadingSpinner />
          ) : (
            <div>
              <p className="text-2xl font-bold text-rog-success mb-1">
                {stats?.success_rate || 0}%
              </p>
              <p className="text-text-muted text-sm">
                總嘗試: {stats?.total_attempts || 0}
              </p>
            </div>
          )}
        </div>

        {/* Active Tasks */}
        <div className="rog-card">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-text-primary">進行中任務</h3>
            <svg className="w-5 h-5 text-rog-info" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          {statsLoading ? (
            <LoadingSpinner />
          ) : (
            <div>
              <p className="text-2xl font-bold text-rog-info mb-1">
                {stats?.active_tasks || 0}
              </p>
              <p className="text-text-muted text-sm">
                平均嘗試: {stats?.average_attempts || 0}
              </p>
            </div>
          )}
        </div>

        {/* Completed Tasks */}
        <div className="rog-card">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-text-primary">已完成</h3>
            <svg className="w-5 h-5 text-rog-warning" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v10a2 2 0 002 2h8a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
            </svg>
          </div>
          {statsLoading ? (
            <LoadingSpinner />
          ) : (
            <div>
              <p className="text-2xl font-bold text-rog-warning mb-1">
                {stats?.completed_tasks || 0}
              </p>
              <p className="text-text-muted text-sm">
                總任務: {stats?.total_tasks || 0}
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Quick Booking */}
        <div className="rog-card">
          <div className="rog-card-header">
            <h3 className="rog-card-title">
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
              </svg>
              快速訂票
            </h3>
          </div>
          <p className="text-text-muted mb-4">
            立即開始新的訂票任務，系統將自動為您搶票
          </p>
          <Link to="/booking" className="rog-btn rog-btn-primary w-full">
            開始訂票
          </Link>
        </div>

        {/* Task Management */}
        <div className="rog-card">
          <div className="rog-card-header">
            <h3 className="rog-card-title">
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v10a2 2 0 002 2h8a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
              </svg>
              任務管理
            </h3>
          </div>
          <p className="text-text-muted mb-4">
            查看和管理您的訂票任務，追蹤執行狀態
          </p>
          <Link to="/tasks" className="rog-btn rog-btn-secondary w-full">
            管理任務
          </Link>
        </div>
      </div>

      {/* Recent Tasks */}
      <div className="rog-card">
        <div className="rog-card-header">
          <h3 className="rog-card-title">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            最近任務
          </h3>
          <Link to="/tasks" className="text-rog-primary hover:text-rog-primary-light text-sm font-medium">
            查看全部
          </Link>
        </div>

        {tasksLoading ? (
          <div className="flex items-center justify-center py-8">
            <LoadingSpinner />
          </div>
        ) : tasks?.results && tasks.results.length > 0 ? (
          <div className="space-y-3">
            {tasks.results.slice(0, 5).map((task) => (
              <div key={task.id} className="flex items-center justify-between p-3 bg-bg-input rounded-lg">
                <div className="flex items-center gap-3">
                  <div className={`w-3 h-3 rounded-full ${
                    task.status === 'success' ? 'bg-rog-success' :
                    task.status === 'failed' ? 'bg-rog-danger' :
                    task.status === 'running' ? 'bg-rog-info animate-pulse' :
                    'bg-rog-warning'
                  }`}></div>
                  <div>
                    <p className="text-text-primary font-medium">
{formatStationRoute(task.from_station, task.to_station, stations)}
                    </p>
                    <p className="text-text-muted text-sm">
                      {task.date} • 嘗試 {task.attempts} 次
                    </p>
                  </div>
                </div>
                <div className="text-right">
                  <p className={`text-sm font-medium ${
                    task.status === 'success' ? 'text-rog-success' :
                    task.status === 'failed' ? 'text-rog-danger' :
                    task.status === 'running' ? 'text-rog-info' :
                    'text-rog-warning'
                  }`}>
                    {task.status === 'success' ? '成功' :
                     task.status === 'failed' ? '失敗' :
                     task.status === 'running' ? '執行中' :
                     task.status === 'pending' ? '等待中' :
                     task.status === 'cancelled' ? '已取消' : '已過期'}
                  </p>
                  {task.status === 'success' && (task.result || (task as any).success_pnr) && (
                    <p className="text-text-muted text-xs">
                      PNR: {task.result || (task as any).success_pnr}
                    </p>
                  )}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-8">
            <svg className="w-12 h-12 text-text-muted mx-auto mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v10a2 2 0 002 2h8a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
            </svg>
            <p className="text-text-muted">暫無任務記錄</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default Dashboard;
