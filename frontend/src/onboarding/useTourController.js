import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext.jsx';
import { TOUR_STEPS } from '../content/helpContent.js';
import { setTourCompleted, userKeyFrom } from './tourStorage.js';
import { waitForSelector } from './tourWait.js';
import { useTourAutoStart } from './useTourAutoStart.js';

export function useTourController() {
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

  const skip = useCallback(() => completeTour(), [completeTour]);

  useTourAutoStart({ currentUser, userKey, startTour });

  return useMemo(() => ({
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
}
