import React, { useEffect } from 'react';

interface VersionCheckerProps {
  onUpdateDetected?: () => void;
}

const VersionChecker: React.FC<VersionCheckerProps> = ({ onUpdateDetected }) => {
  useEffect(() => {
    const checkVersion = () => {
      try {
        // Simple version check based on build time from meta tag
        const metaTag = document.querySelector('meta[name="build-time"]');
        const currentBuildTime = metaTag?.getAttribute('content') || Date.now().toString();
        const storedBuildTime = localStorage.getItem('build_time');
        
        if (!storedBuildTime) {
          // First visit
          localStorage.setItem('build_time', currentBuildTime);
          console.log('First visit detected, version stored');
          return;
        }
        
        if (storedBuildTime !== currentBuildTime) {
          // Build has changed
          console.log('New build detected, clearing cache and reloading...', {
            old: storedBuildTime,
            new: currentBuildTime
          });
          
          onUpdateDetected?.();
          
          // Clear all possible caches
          if ('caches' in window) {
            caches.keys().then(names => {
              names.forEach(name => caches.delete(name));
            });
          }
          
          // Clear localStorage except essential data
          const essentialData = {
            build_time: currentBuildTime
          };
          
          localStorage.clear();
          
          // Restore essential data
          Object.entries(essentialData).forEach(([key, value]) => {
            localStorage.setItem(key, value);
          });
          
          // Force reload
          window.location.reload();
          return;
        }
        
        console.log('No version update needed');
      } catch (error) {
        console.error('Version check failed:', error);
      }
    };

    checkVersion();
  }, [onUpdateDetected]);

  // Don't render anything, this is a background component
  return null;
};

export default VersionChecker;
