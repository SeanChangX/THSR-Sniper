// Utility function to format dates with user's timezone and show UTC offset
export const formatDateTimeWithTimezone = (dateString: string | Date): string => {
  const date = new Date(dateString);
  
  // Format the date in user's local timezone
  const formattedDate = date.toLocaleString('zh-TW', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false
    // No timeZone specified - use user's browser timezone automatically
  });
  
  return `${formattedDate} (Local)`;
};

// Utility function for short date formatting with timezone
export const formatDateWithTimezone = (dateString: string | Date): string => {
  const date = new Date(dateString);
  
  // Format the date in user's locale
  const formattedDate = date.toLocaleDateString('zh-TW', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit'
  });
  
  return `${formattedDate} (Local)`;
};

// Utility function to check if a booking task is expired based on departure date
export const isTaskExpired = (taskDate: string): boolean => {
  try {
    // Parse the task date (format: YYYY/MM/DD)
    const [year, month, day] = taskDate.split('/').map(Number);
    const bookingDate = new Date(year, month - 1, day); // month is 0-indexed in Date constructor
    
    // Get today's date (local timezone)
    const today = new Date();
    today.setHours(0, 0, 0, 0); // Reset time to start of day for accurate date comparison
    
    // Set booking date to start of day for accurate comparison
    bookingDate.setHours(0, 0, 0, 0);
    
    // // Debug logging
    // console.log('Date comparison:', {
    //   taskDate,
    //   bookingDate: bookingDate.toISOString().split('T')[0],
    //   today: today.toISOString().split('T')[0],
    //   isExpired: bookingDate < today
    // });
    
    // Task is expired if booking date is before today
    return bookingDate < today;
  } catch (error) {
    console.error('Error parsing task date:', taskDate, error);
    return false; // If we can't parse the date, don't mark as expired
  }
};

// Utility function to get the effective status of a task (considering expiration)
export const getEffectiveTaskStatus = (task: { status: string; date: string }): string => {
  // If task is already marked as expired by backend, return as is
  if (task.status === 'expired') {
    return 'expired';
  }
  
  // If departure date has passed, mark as expired regardless of current status
  if (isTaskExpired(task.date)) {
    return 'expired';
  }
  
  // For all other cases, return the original status
  return task.status;
};
