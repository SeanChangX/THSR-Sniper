// Token utility functions
export const isTokenExpired = (token: string): boolean => {
  try {
    // Decode JWT token (without verification)
    const payload = JSON.parse(atob(token.split('.')[1]));
    const currentTime = Math.floor(Date.now() / 1000);
    
    // Check if token is expired
    return payload.exp < currentTime;
  } catch (error) {
    console.error('Error decoding token:', error);
    return true; // If we can't decode, consider it expired
  }
};

export const getTokenExpiryTime = (token: string): number | null => {
  try {
    const payload = JSON.parse(atob(token.split('.')[1]));
    return payload.exp * 1000; // Convert to milliseconds
  } catch (error) {
    console.error('Error decoding token:', error);
    return null;
  }
};

export const getTimeUntilExpiry = (token: string): number => {
  const expiryTime = getTokenExpiryTime(token);
  if (!expiryTime) return 0;
  
  return expiryTime - Date.now();
};

// Check if token will expire soon (within 30 seconds)
export const isTokenExpiringSoon = (token: string): boolean => {
  const timeUntilExpiry = getTimeUntilExpiry(token);
  return timeUntilExpiry < 30000; // 30 seconds
};

// Get token expiry time in a readable format
export const getTokenExpiryInfo = (token: string): { isExpired: boolean; isExpiringSoon: boolean; timeUntilExpiry: number } => {
  const isExpired = isTokenExpired(token);
  const isExpiringSoon = isTokenExpiringSoon(token);
  const timeUntilExpiry = getTimeUntilExpiry(token);
  
  return {
    isExpired,
    isExpiringSoon,
    timeUntilExpiry: Math.max(0, timeUntilExpiry)
  };
};
