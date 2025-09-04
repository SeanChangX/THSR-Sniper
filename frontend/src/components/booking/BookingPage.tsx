import React from 'react';
import { useQuery } from 'react-query';
import { thsrApi, authApi } from '@/services/api';
import BookingForm from './BookingForm';
import LoadingSpinner from '@/components/ui/LoadingSpinner';

const BookingPage: React.FC = () => {
  // Fetch required data
  const { data: stations, isLoading: stationsLoading } = useQuery(
    'stations',
    thsrApi.getStations
  );

  const { data: timeSlots, isLoading: timeSlotsLoading } = useQuery(
    'timeSlots', 
    thsrApi.getTimeSlots
  );

  const { data: thsrInfo, isLoading: thsrInfoLoading } = useQuery(
    'thsrInfo',
    authApi.getTHSRInfo
  );

  const isLoading = stationsLoading || timeSlotsLoading || thsrInfoLoading;

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-96">
        <LoadingSpinner size="large" />
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Page Header */}
      <div className="rog-card">
        <div className="rog-card-header">
          <h1 className="rog-card-title text-2xl">
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
            </svg>
            高鐵訂票
          </h1>
        </div>
        <p className="text-text-muted">
          設定您的訂票需求，系統將自動為您搶票。
        </p>
      </div>

      {/* Booking Form */}
      <BookingForm 
        stations={stations || []}
        timeSlots={timeSlots || []}
        thsrInfo={thsrInfo}
      />

      {/* Instructions */}
      <div className="rog-card">
        <div className="rog-card-header">
          <h3 className="rog-card-title">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            使用說明
          </h3>
        </div>
        <div className="grid grid-cols-1 gap-6">
          <div>
            <h4 className="font-semibold text-text-primary mb-3">排程訂票</h4>
            <ul className="space-y-2 text-text-muted text-sm">
              <li className="flex items-start gap-2">
                <span className="text-rog-primary mt-1">•</span>
                定期重複嘗試訂票
              </li>
              <li className="flex items-start gap-2">
                <span className="text-rog-primary mt-1">•</span>
                適合熱門時段搶票
              </li>
              <li className="flex items-start gap-2">
                <span className="text-rog-primary mt-1">•</span>
                可設定嘗試間隔和最大次數
              </li>
            </ul>
          </div>
        </div>
      </div>


    </div>
  );
};

export default BookingPage;
