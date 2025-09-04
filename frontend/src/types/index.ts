// User and Authentication Types
export interface User {
  id: number;
  username: string;
  email: string;
  full_name?: string;
  is_active: boolean;
  is_verified: boolean;
  created_at: string;
  thsr_use_membership: boolean;
  has_thsr_id: boolean;
}

export interface LoginCredentials {
  username: string;
  password: string;
}

export interface RegisterData {
  username: string;
  email: string;
  password: string;
  full_name?: string;
  thsr_personal_id?: string;
  thsr_use_membership: boolean;
}

export interface Token {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface UserUpdate {
  full_name?: string;
  email?: string;
  thsr_personal_id?: string;
  thsr_use_membership?: boolean;
  preferences?: Record<string, any>;
}

export interface PasswordChange {
  current_password: string;
  new_password: string;
  confirm_password?: string;
}

export interface THSRInfo {
  personal_id?: string;
  use_membership: boolean;
}

// THSR Booking Types
export interface StationInfo {
  id: number;
  name: string;
}

export interface TimeSlotInfo {
  id: number;
  time: string;
  formatted_time: string;
}

export interface BookingRequest {
  from_station: number;
  to_station: number;
  date: string;
  personal_id: string;
  use_membership: boolean;
  adult_cnt?: number;
  student_cnt?: number;
  child_cnt?: number;
  senior_cnt?: number;
  disabled_cnt?: number;
  time?: number;
  train_index?: number;
  seat_prefer?: number;
  class_type?: number;
  no_ocr?: boolean;
}

export interface ScheduledBookingRequest extends BookingRequest {
  interval_minutes: number;
  max_attempts?: number;
}

export interface BookingResponse {
  success: boolean;
  message: string;
  pnr_code?: string;
  task_id?: string;
}

export interface TaskStatusResponse {
  id: string;
  status: string;
  from_station: number;
  to_station: number;
  date: string;
  user_id?: string;
  interval_minutes: number;
  attempts: number;
  last_attempt?: string;
  success_pnr?: string;
  error_message?: string;
  created_at: string;
}

export interface BookingTask {
  id: string;
  status: 'pending' | 'running' | 'success' | 'failed' | 'cancelled' | 'expired';
  from_station: number;
  to_station: number;
  date: string;
  user_id?: string;
  adult_cnt?: number;
  student_cnt?: number;
  child_cnt?: number;
  senior_cnt?: number;
  disabled_cnt?: number;
  personal_id: string;
  use_membership: boolean;
  interval_minutes: number;
  max_attempts?: number;
  attempts: number;
  created_at: string;
  last_attempt?: string;
  time?: number;
  seat_prefer?: number;
  class_type?: number;
  no_ocr?: boolean;
  result?: string;
  success_pnr?: string;
  error?: string;
}

export interface SchedulerStatus {
  running: boolean;
  total_tasks: number;
  status_breakdown: Record<string, number>;
  storage_path: string;
  thsr_connectivity?: THSRConnectivityStatus;
}

export interface THSRConnectivityStatus {
  status: 'online' | 'offline' | 'degraded' | 'timeout' | 'error';
  response_time_ms?: number;
  message: string;
  tested_at: number;
  session_info?: string;
}

export interface BookingStats {
  success: boolean;
  total_tasks: number;
  total_attempts: number;
  average_attempts: number;
  status_breakdown: Record<string, number>;
  success_rate: number;
  completed_tasks: number;
  active_tasks: number;
}

// Form Types
export interface BookingFormData {
  fromStation: number;
  toStation: number;
  date: string;
  adultCount: number;
  studentCount: number;
  childCount: number;
  seniorCount: number;
  disabledCount: number;
  departureTime?: number;
  trainIndex?: number;
  seatPreference: number;
  classType: number;
  useOCR: boolean;
  intervalMinutes: number;
  maxAttempts?: number;
}

// API Response Types
export interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  message?: string;
  error?: string;
}

export interface PaginatedResponse<T> {
  success: boolean;
  total: number;
  offset: number;
  limit: number;
  results: T[];
}

// UI State Types
export interface AlertState {
  type: 'success' | 'error' | 'warning' | 'info';
  message: string;
  show: boolean;
}

export interface LoadingState {
  [key: string]: boolean;
}

// Constants
export const SEAT_PREFERENCES = {
  0: '不指定',
  1: '靠窗',
  2: '靠走道'
} as const;

export const CLASS_TYPES = {
  0: '標準車廂',
  1: '商務車廂'
} as const;

export const BOOKING_STATUS = {
  pending: '等待中',
  running: '執行中',
  success: '成功',
  failed: '失敗',
  cancelled: '已取消',
  expired: '已過期'
} as const;

export type SeatPreference = keyof typeof SEAT_PREFERENCES;
export type ClassType = keyof typeof CLASS_TYPES;
export type BookingStatus = keyof typeof BOOKING_STATUS;
