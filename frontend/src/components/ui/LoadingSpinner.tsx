import React from 'react';

interface LoadingSpinnerProps {
  size?: 'small' | 'medium' | 'large';
  color?: string;
  className?: string;
}

const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({ 
  size = 'medium', 
  color = 'text-rog-primary',
  className = '' 
}) => {
  const sizeClasses = {
    small: 'w-4 h-4',
    medium: 'w-8 h-8', 
    large: 'w-16 h-16'
  };

  return (
    <div className={`inline-block ${className}`}>
      <div className={`animate-spin rounded-full border-2 border-gray-700 border-t-current ${sizeClasses[size]} ${color}`}></div>
    </div>
  );
};

export default LoadingSpinner;
