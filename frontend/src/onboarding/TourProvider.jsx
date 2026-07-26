import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext.jsx';
import { TOUR_STEPS } from '../content/helpContent.js';
import { isTourCompleted, setTourCompleted } from './tourStorage.js';

const TourContext = createContext(null);

function userKeyFrom(user) {
  if (!user) return 'anonymous';
  return String(user.userId ?? user.username ?? 'anonymous');
}

function waitForSelector(selector, { timeoutMs = 2500 } = {}) {
  if (!selector) return Promise.resolve(true);
  return new Promise((resolve) => {
    const start = performance.now();
    function tick() {
      if (document.querySelector(selector)) {
        resolve(true);
        return;
      }
      if (performance.now() - start > timeoutMs) {
        resolve(false);
        return;
      }
      window.requestAnimationFrame(tick);
    }
    tick();
  });
}

export function TourProvider({ children }) {
  const { currentUser } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [isOpen, setIsOpen] = useState(false);
  const [stepIndex, setStepIndex] = useState(0);
  const locationRef = useRef(location.pathname);
  const stepRequestIdRef = useRef(0);
  const stepIndexRef = useRef(0);
  const userKey = userKeyFrom(currentUser);

  useEffect(() => {
    locationRef.current = location.pathname;
  }, [location.pathname]);

  useEffect(() => {
    stepIndexRef.current = stepIndex;
  }, [stepIndex]);

  const completeTour = useCallback(() => {
    stepRequestIdRef.current += 1;
    setTourCompleted(userKey, true);
    setIsOpen(false);
    setStepIndex(0);
  }, [userKey]);

  const goToStep = useCallback(async (index) => {
    const step = TOUR_STEPS[index];
    if (!step) return;

    const requestId = ++stepRequestIdRef.current;
    setStepIndex(index);

    const route = step.route ?? '/';
    if (locationRef.current !== route) {
      navigate(route);
      await waitForSelector(step.selector);
    } else if (step.selector) {
      await waitForSelector(step.selector, { timeoutMs: 800 });
    }

    if (requestId !== stepRequestIdRef.current) return;
  }, [navigate]);

  const startTour = useCallback(() => {
    setIsOpen(true);
    void goToStep(0);
  }, [goToStep]);

  const next = useCallback(() => {
    const i = stepIndexRef.current;
    if (i >= TOUR_STEPS.length - 1) {
      completeTour();
      return;
    }
    void goToStep(i + 1);
  }, [completeTour, goToStep]);

  const back = useCallback(() => {
    const i = stepIndexRef.current;
    const prevIndex = Math.max(0, i - 1);
    if (prevIndex === i) return;
    void goToStep(prevIndex);
  }, [goToStep]);

  const skip = useCallback(() => {
    completeTour();
  }, [completeTour]);

  useEffect(() => {
    if (!currentUser) return undefined;
    if (isTourCompleted(userKey)) return undefined;
    const t = window.setTimeout(() => {
      startTour();
    }, 400);
    return () => window.clearTimeout(t);
  }, [currentUser, userKey]); // eslint-disable-line react-hooks/exhaustive-deps -- auto-start once per user when incomplete

  const value = useMemo(() => ({
    isOpen,
    stepIndex,
    steps: TOUR_STEPS,
    step: TOUR_STEPS[stepIndex] ?? null,
    startTour,
    next,
    back,
    skip,
    finish: completeTour,
  }), [isOpen, stepIndex, startTour, next, back, skip, completeTour]);

  return <TourContext.Provider value={value}>{children}</TourContext.Provider>;
}

export function useTour() {
  const ctx = useContext(TourContext);
  if (!ctx) throw new Error('useTour must be used within a TourProvider');
  return ctx;
}
