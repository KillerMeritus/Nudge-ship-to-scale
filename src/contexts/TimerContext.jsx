import React, { createContext, useContext, useState, useEffect, useRef } from 'react';

const TimerContext = createContext();

export function useTimer() {
  return useContext(TimerContext);
}

export function TimerProvider({ children }) {
  // 'idle', 'running', 'paused'
  const [status, setStatus] = useState('idle');
  
  // 'focus', 'short_break', 'long_break'
  const [sessionType, setSessionType] = useState('focus');
  
  // Default to 25 minutes
  const [remainingSeconds, setRemainingSeconds] = useState(25 * 60);
  const [sessionCount, setSessionCount] = useState(0);

  const timerRef = useRef(null);

  useEffect(() => {
    // Cleanup interval on unmount
    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
    };
  }, []);

  const handleSessionComplete = () => {
    setStatus('idle');
    
    if (sessionType === 'focus') {
      const nextCount = sessionCount + 1;
      setSessionCount(nextCount);
      
      // Default to long break every 4 sessions
      if (nextCount > 0 && nextCount % 4 === 0) {
        setSessionType('long_break');
        setRemainingSeconds(15 * 60); // 15 mins
      } else {
        setSessionType('short_break');
        setRemainingSeconds(5 * 60); // 5 mins
      }
    } else {
      // Return to focus after a break
      setSessionType('focus');
      setRemainingSeconds(25 * 60); // 25 mins
    }
  };

  const start = () => {
    if (status === 'running') return;
    
    setStatus('running');
    
    timerRef.current = setInterval(() => {
      setRemainingSeconds((prev) => {
        if (prev <= 1) {
          clearInterval(timerRef.current);
          handleSessionComplete();
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
  };

  const pause = () => {
    if (status !== 'running') return;
    
    setStatus('paused');
    if (timerRef.current) {
      clearInterval(timerRef.current);
    }
  };

  const reset = () => {
    setStatus('idle');
    if (timerRef.current) {
      clearInterval(timerRef.current);
    }
    
    if (sessionType === 'focus') {
      setRemainingSeconds(25 * 60);
    } else if (sessionType === 'short_break') {
      setRemainingSeconds(5 * 60);
    } else if (sessionType === 'long_break') {
      setRemainingSeconds(15 * 60);
    }
  };

  const changeMode = (newMode) => {
    setStatus('idle');
    if (timerRef.current) clearInterval(timerRef.current);
    setSessionType(newMode);
    
    if (newMode === 'focus') {
      setRemainingSeconds(25 * 60);
    } else if (newMode === 'short_break') {
      setRemainingSeconds(5 * 60);
    } else if (newMode === 'long_break') {
      setRemainingSeconds(15 * 60);
    }
  };

  const value = {
    status,
    remainingSeconds,
    sessionType,
    sessionCount,
    start,
    pause,
    reset,
    changeMode
  };

  return (
    <TimerContext.Provider value={value}>
      {children}
    </TimerContext.Provider>
  );
}
