import { createContext, useContext } from 'react';
import { useTourController } from './useTourController.js';

const TourContext = createContext(null);

export function TourProvider({ children }) {
  const value = useTourController();
  return <TourContext.Provider value={value}>{children}</TourContext.Provider>;
}

export function useTour() {
  const ctx = useContext(TourContext);
  if (!ctx) throw new Error('useTour must be used within a TourProvider');
  return ctx;
}
