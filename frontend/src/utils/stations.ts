import { StationInfo } from '@/types';

// Utility function to get station name by ID
export const getStationName = (stationId: number, stations: StationInfo[] = []): string => {
  const station = stations.find(s => s.id === stationId);
  return station?.name || `站點 ${stationId}`;
};

// Utility function to format station route
export const formatStationRoute = (fromStation: number, toStation: number, stations: StationInfo[] = []): string => {
  const fromName = getStationName(fromStation, stations);
  const toName = getStationName(toStation, stations);
  return `${fromName} → ${toName}`;
};
