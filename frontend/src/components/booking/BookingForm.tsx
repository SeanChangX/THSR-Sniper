import React, { useState } from 'react';
import { useForm } from 'react-hook-form';
import { useMutation } from 'react-query';
import { toast } from 'react-toastify';
import { useNavigate } from 'react-router-dom';
import { thsrApi } from '@/services/api';
import { StationInfo, TimeSlotInfo, THSRInfo, BookingFormData } from '@/types';
import LoadingSpinner from '@/components/ui/LoadingSpinner';

interface BookingFormProps {
  stations: StationInfo[];
  timeSlots: TimeSlotInfo[];
  thsrInfo: THSRInfo | null | undefined;
}

const BookingForm: React.FC<BookingFormProps> = ({ stations, timeSlots, thsrInfo }) => {
  const navigate = useNavigate();
  // Temporarily hide booking mode selection, use only scheduled booking
  const [bookingMode] = useState<'immediate' | 'scheduled'>('scheduled');
  
  const {
    register,
    handleSubmit,
    watch,
    formState: { errors },
  } = useForm<BookingFormData>({
    defaultValues: {
      fromStation: 1,
      toStation: 2,
      date: new Date().toISOString().split('T')[0],
      adultCount: 1,
      studentCount: 0,
      childCount: 0,
      seniorCount: 0,
      disabledCount: 0,
      seatPreference: 0,
      classType: 0,
      useOCR: true,
      intervalMinutes: 5,
    },
    mode: 'onChange', // Enable real-time validation
  });

  // Watch form values
  const adultCount = watch('adultCount');
  const studentCount = watch('studentCount');
  const childCount = watch('childCount');
  const seniorCount = watch('seniorCount');
  const disabledCount = watch('disabledCount');
  const fromStation = watch('fromStation');

  // Immediate booking mutation
  const immediateBookingMutation = useMutation(thsrApi.immediateBooking, {
    onSuccess: (response) => {
      if (response.success) {
        toast.success(`訂票成功！PNR代碼：${response.pnr_code}`);
        navigate('/tasks');
      } else {
        toast.error(`訂票失敗：${response.message}`);
      }
    },
    onError: (error: any) => {
      toast.error(`訂票失敗：${error.message}`);
    },
  });

  // Scheduled booking mutation
  const scheduledBookingMutation = useMutation(thsrApi.scheduleBooking, {
    onSuccess: (response) => {
      if (response.success) {
        toast.success(`排程訂票已建立！任務ID：${response.task_id}`);
        navigate('/tasks');
      } else {
        toast.error(`建立排程失敗：${response.message}`);
      }
    },
    onError: (error: any) => {
      toast.error(`建立排程失敗：${error.message}`);
    },
  });

  const onSubmit = (data: BookingFormData) => {
    // Validate THSR personal info
    if (!thsrInfo?.personal_id) {
      toast.error('請先在個人設定中設定身分證字號');
      return;
    }

    // Validate ticket counts with proper number conversion
    const adultTickets = Number(data.adultCount) || 0;
    const studentTickets = Number(data.studentCount) || 0;
    const childTickets = Number(data.childCount) || 0;
    const seniorTickets = Number(data.seniorCount) || 0;
    const disabledTickets = Number(data.disabledCount) || 0;
    
    const totalTickets = adultTickets + studentTickets + childTickets + seniorTickets + disabledTickets;
    
    console.log('Ticket validation:', {
      adult: adultTickets,
      student: studentTickets,
      child: childTickets,
      senior: seniorTickets,
      disabled: disabledTickets,
      total: totalTickets
    });
    
    if (totalTickets === 0) {
      toast.error('請至少選擇一張票');
      return;
    }

    if (totalTickets > 10) {
      toast.error(`總票數不能超過10張 (目前選擇了 ${totalTickets} 張)`);
      return;
    }

    // Validate stations
    if (data.fromStation === data.toStation) {
      toast.error('出發站和到達站不能相同');
      return;
    }

    // Validate date
    const selectedDate = new Date(data.date);
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    
    if (selectedDate < today) {
      toast.error('不能選擇過去的日期');
      return;
    }

    // Validate scheduled booking parameters
    if (bookingMode === 'scheduled') {
      if (!data.intervalMinutes || data.intervalMinutes < 1) {
        toast.error('執行間隔時間必須至少為1分鐘');
        return;
      }
      
      if (data.maxAttempts && data.maxAttempts < 1) {
        toast.error('最大嘗試次數必須至少為1次');
        return;
      }
    }

    // Validate THSR info exists
    if (!thsrInfo?.personal_id) {
      console.error('Personal ID is missing in THSR info');
      return;
    }

    const bookingData = {
      from_station: data.fromStation,
      to_station: data.toStation,
      date: data.date.replace(/-/g, '/'),
      personal_id: thsrInfo.personal_id,
      use_membership: thsrInfo.use_membership,
      ...(adultTickets > 0 && { adult_cnt: adultTickets }),
      ...(studentTickets > 0 && { student_cnt: studentTickets }),
      ...(childTickets > 0 && { child_cnt: childTickets }),
      ...(seniorTickets > 0 && { senior_cnt: seniorTickets }),
      ...(disabledTickets > 0 && { disabled_cnt: disabledTickets }),
      ...(data.departureTime && { time: data.departureTime }),
      ...(data.trainIndex && { train_index: data.trainIndex }),
      seat_prefer: data.seatPreference,
      class_type: data.classType,
      no_ocr: !data.useOCR,
    };

    if (bookingMode === 'immediate') {
      immediateBookingMutation.mutate(bookingData);
    } else {
      const scheduledData = {
        ...bookingData,
        interval_minutes: data.intervalMinutes,
        max_attempts: data.maxAttempts || undefined,
      };
      scheduledBookingMutation.mutate(scheduledData);
    }
  };

  const isSubmitting = immediateBookingMutation.isLoading || scheduledBookingMutation.isLoading;

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
      {/* Booking Mode Selection - Temporarily Hidden */}
      {/* 
      <div className="rog-card">
        <div className="rog-card-header">
          <h3 className="rog-card-title">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            訂票模式
          </h3>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <label className={`cursor-pointer p-4 border-2 rounded-lg transition-all ${
            bookingMode === 'immediate' 
              ? 'border-rog-primary bg-rog-primary/10' 
              : 'border-gray-700 hover:border-gray-600'
          }`}>
            <div className="flex items-center gap-3">
              <input
                type="radio"
                name="bookingMode"
                value="immediate"
                checked={bookingMode === 'immediate'}
                onChange={(e) => setBookingMode(e.target.value as 'immediate')}
                className="w-4 h-4 text-rog-primary"
              />
              <div>
                <h4 className="font-semibold text-text-primary">立即訂票</h4>
                <p className="text-sm text-text-muted">執行一次訂票嘗試</p>
              </div>
            </div>
          </label>

          <label className={`cursor-pointer p-4 border-2 rounded-lg transition-all ${
            bookingMode === 'scheduled' 
              ? 'border-rog-primary bg-rog-primary/10' 
              : 'border-gray-700 hover:border-gray-600'
          }`}>
            <div className="flex items-center gap-3">
              <input
                type="radio"
                name="bookingMode"
                value="scheduled"
                checked={bookingMode === 'scheduled'}
                onChange={(e) => setBookingMode(e.target.value as 'scheduled')}
                className="w-4 h-4 text-rog-primary"
              />
              <div>
                <h4 className="font-semibold text-text-primary">排程訂票</h4>
                <p className="text-sm text-text-muted">定期重複嘗試訂票</p>
              </div>
            </div>
          </label>
        </div>
      </div>
      */}

      {/* Basic Booking Information */}
      <div className="rog-card">
        <div className="rog-card-header">
          <h3 className="rog-card-title">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
            行程資訊
          </h3>
        </div>

        <div className="form-grid">
          {/* From Station */}
          <div className="form-group">
            <label htmlFor="fromStation" className="form-label">出發站</label>
            <select
              {...register('fromStation', { required: '請選擇出發站' })}
              id="fromStation"
              className="rog-select"
            >
              {stations.map((station) => (
                <option key={station.id} value={station.id}>
                  {station.name}
                </option>
              ))}
            </select>
          </div>

          {/* To Station */}
          <div className="form-group">
            <label htmlFor="toStation" className="form-label">到達站</label>
            <select
              {...register('toStation', { 
                required: '請選擇到達站',
                validate: value => value !== fromStation || '出發站和到達站不能相同'
              })}
              id="toStation"
              className="rog-select"
            >
              {stations.map((station) => (
                <option key={station.id} value={station.id}>
                  {station.name}
                </option>
              ))}
            </select>
            {errors.toStation && (
              <p className="text-rog-danger text-sm mt-1">{errors.toStation.message}</p>
            )}
          </div>

          {/* Date */}
          <div className="form-group">
            <label htmlFor="date" className="form-label">出發日期</label>
            <input
              {...register('date', { 
                required: '請選擇出發日期',
                validate: value => {
                  const selectedDate = new Date(value);
                  const today = new Date();
                  today.setHours(0, 0, 0, 0);
                  return selectedDate >= today || '不能選擇過去的日期';
                }
              })}
              type="date"
              id="date"
              className="rog-input"
            />
            {errors.date && (
              <p className="text-rog-danger text-sm mt-1">{errors.date.message}</p>
            )}
          </div>

          {/* Departure Time */}
          <div className="form-group">
            <label htmlFor="departureTime" className="form-label">出發時間（選填）</label>
            <select
              {...register('departureTime')}
              id="departureTime"
              className="rog-select"
            >
              <option value="">不指定時間</option>
              {timeSlots.map((slot) => (
                <option key={slot.id} value={slot.id}>
                  {slot.formatted_time} ({slot.time})
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Passenger Information */}
      <div className="rog-card">
        <div className="rog-card-header">
          <h3 className="rog-card-title">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
            </svg>
            乘客資訊
          </h3>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <div className="form-group">
            <label htmlFor="adultCount" className="form-label">成人票數</label>
            <input
              {...register('adultCount', { 
                min: { value: 0, message: '票數不能為負數' },
                max: { value: 10, message: '票數不能超過10張' }
              })}
              type="number"
              id="adultCount"
              min="0"
              max="10"
              className="rog-input"
            />
            {errors.adultCount && (
              <p className="text-rog-danger text-sm mt-1">{errors.adultCount.message}</p>
            )}
          </div>

          <div className="form-group">
            <label htmlFor="studentCount" className="form-label">學生票數</label>
            <input
              {...register('studentCount', { 
                min: { value: 0, message: '票數不能為負數' },
                max: { value: 10, message: '票數不能超過10張' }
              })}
              type="number"
              id="studentCount"
              min="0"
              max="10"
              className="rog-input"
            />
            {errors.studentCount && (
              <p className="text-rog-danger text-sm mt-1">{errors.studentCount.message}</p>
            )}
          </div>

          <div className="form-group">
            <label htmlFor="childCount" className="form-label">兒童票數</label>
            <input
              {...register('childCount', { 
                min: { value: 0, message: '票數不能為負數' },
                max: { value: 10, message: '票數不能超過10張' }
              })}
              type="number"
              id="childCount"
              min="0"
              max="10"
              className="rog-input"
            />
            {errors.childCount && (
              <p className="text-rog-danger text-sm mt-1">{errors.childCount.message}</p>
            )}
          </div>

          <div className="form-group">
            <label htmlFor="seniorCount" className="form-label">敬老票數</label>
            <input
              {...register('seniorCount', { 
                min: { value: 0, message: '票數不能為負數' },
                max: { value: 10, message: '票數不能超過10張' }
              })}
              type="number"
              id="seniorCount"
              min="0"
              max="10"
              className="rog-input"
            />
            {errors.seniorCount && (
              <p className="text-rog-danger text-sm mt-1">{errors.seniorCount.message}</p>
            )}
          </div>

          <div className="form-group">
            <label htmlFor="disabledCount" className="form-label">愛心票數</label>
            <input
              {...register('disabledCount', { 
                min: { value: 0, message: '票數不能為負數' },
                max: { value: 10, message: '票數不能超過10張' }
              })}
              type="number"
              id="disabledCount"
              min="0"
              max="10"
              className="rog-input"
            />
            {errors.disabledCount && (
              <p className="text-rog-danger text-sm mt-1">{errors.disabledCount.message}</p>
            )}
          </div>
        </div>

        {/* Real-time Ticket Count Display */}
        <div className="mt-4 p-3 bg-bg-input rounded-lg">
          <div className="flex items-center justify-between">
            <span className="text-text-muted text-sm">總票數</span>
            <span className={`font-semibold ${
              (Number(adultCount) || 0) + (Number(studentCount) || 0) + (Number(childCount) || 0) + 
              (Number(seniorCount) || 0) + (Number(disabledCount) || 0) > 10 
                ? 'text-rog-danger' 
                : (Number(adultCount) || 0) + (Number(studentCount) || 0) + (Number(childCount) || 0) + 
                  (Number(seniorCount) || 0) + (Number(disabledCount) || 0) === 0
                  ? 'text-rog-warning'
                  : 'text-rog-success'
            }`}>
              {(Number(adultCount) || 0) + (Number(studentCount) || 0) + (Number(childCount) || 0) + 
               (Number(seniorCount) || 0) + (Number(disabledCount) || 0)} / 10 張
            </span>
          </div>
          {(Number(adultCount) || 0) + (Number(studentCount) || 0) + (Number(childCount) || 0) + 
           (Number(seniorCount) || 0) + (Number(disabledCount) || 0) > 10 && (
            <p className="text-rog-danger text-xs mt-1">票數超過限制</p>
          )}
        </div>

        {/* Ticket Count Validation */}
        {adultCount === 0 && studentCount === 0 && childCount === 0 && seniorCount === 0 && disabledCount === 0 && (
          <p className="text-rog-danger text-sm mt-2">至少需要選擇一張票</p>
        )}
      </div>

      {/* Preferences */}
      <div className="rog-card">
        <div className="rog-card-header">
          <h3 className="rog-card-title">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 100-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 100-4m0 4v2m0-6V4" />
            </svg>
            偏好設定
          </h3>
        </div>

        <div className="form-grid">
          <div className="form-group">
            <label htmlFor="seatPreference" className="form-label">座位偏好</label>
            <select
              {...register('seatPreference')}
              id="seatPreference"
              className="rog-select"
            >
              <option value={0}>不指定</option>
              <option value={1}>靠窗</option>
              <option value={2}>靠走道</option>
            </select>
          </div>

          <div className="form-group">
            <label htmlFor="classType" className="form-label">車廂類型</label>
            <select
              {...register('classType')}
              id="classType"
              className="rog-select"
            >
              <option value={0}>標準車廂</option>
              <option value={1}>商務車廂</option>
            </select>
          </div>

          <div className="form-group">
            <label htmlFor="trainIndex" className="form-label">車次選擇（選填）</label>
            <input
              {...register('trainIndex', {
                min: { value: 1, message: '車次索引必須大於0' }
              })}
              type="number"
              id="trainIndex"
              min="1"
              className="rog-input"
              placeholder="不指定"
            />
            {errors.trainIndex && (
              <p className="text-rog-danger text-sm mt-1">{errors.trainIndex.message}</p>
            )}
          </div>

          <div className="form-group">
            <label className="form-label">驗證碼設定</label>
            <div className="flex items-center gap-3 pt-1">
              <div className="flex items-center gap-2">
                <div className="w-4 h-4 bg-rog-success rounded flex items-center justify-center">
                  <svg className="w-3 h-3 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                </div>
                <span className="text-text-secondary">OCR AI Recognition Enabled</span>
              </div>
              <input
                {...register('useOCR')}
                type="hidden"
                value="true"
              />
            </div>
          </div>
        </div>
      </div>

      {/* Scheduled Booking Settings */}
      {bookingMode === 'scheduled' && (
        <div className="rog-card border-rog-primary/30 bg-rog-primary/5">
          <div className="rog-card-header">
            <h3 className="rog-card-title">
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              排程設定
            </h3>
          </div>

          <div className="form-grid">
            <div className="form-group">
              <label htmlFor="intervalMinutes" className="form-label">重試間隔（分鐘）</label>
              <input
                {...register('intervalMinutes', {
                  required: '請設定重試間隔',
                  min: { value: 1, message: '間隔至少1分鐘' },
                  max: { value: 60, message: '間隔不能超過60分鐘' }
                })}
                type="number"
                id="intervalMinutes"
                min="1"
                max="60"
                className="rog-input"
              />
              {errors.intervalMinutes && (
                <p className="text-rog-danger text-sm mt-1">{errors.intervalMinutes.message}</p>
              )}
            </div>

            <div className="form-group">
              <label htmlFor="maxAttempts" className="form-label">最大嘗試次數（選填）</label>
              <input
                {...register('maxAttempts', {
                  min: { value: 1, message: '至少嘗試1次' }
                })}
                type="number"
                id="maxAttempts"
                min="1"
                className="rog-input"
                placeholder="不限制"
              />
              {errors.maxAttempts && (
                <p className="text-rog-danger text-sm mt-1">{errors.maxAttempts.message}</p>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Submit Button */}
      <div className="flex justify-end">
        <button
          type="submit"
          disabled={isSubmitting || !thsrInfo?.personal_id}
          className="rog-btn rog-btn-primary flex items-center gap-2 min-w-48"
        >
          {isSubmitting ? (
            <>
              <LoadingSpinner size="small" />
              建立中...
            </>
          ) : (
            <>
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
              </svg>
              建立排程
            </>
          )}
        </button>
      </div>

      {!thsrInfo?.personal_id && (
        <div className="text-center p-4 bg-rog-warning/10 border border-rog-warning/30 rounded-lg">
          <p className="text-rog-warning">
            請先在<a href="/profile" className="underline hover:text-rog-warning-light">個人設定</a>中設定身分證字號
          </p>
        </div>
      )}
    </form>
  );
};

export default BookingForm;
