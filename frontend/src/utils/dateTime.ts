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
