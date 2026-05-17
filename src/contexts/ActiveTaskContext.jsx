import React, { createContext, useContext, useState, useEffect, useRef } from 'react';
import { listen } from '@tauri-apps/api/event';

const ActiveTaskContext = createContext();

export function useActiveTask() {
  return useContext(ActiveTaskContext);
}

export function ActiveTaskProvider({ children }) {
  const [activeTask, setActiveTask] = useState(null);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [taskStatus, setTaskStatus] = useState('idle'); // 'idle', 'running', 'paused'

  const timerRef = useRef(null);

  const pauseTaskRef = useRef();

  useEffect(() => {
    let unlistenWake;
    if (window.__TAURI_INTERNALS__) {
      listen('system-wake', () => {
        if (pauseTaskRef.current) {
          pauseTaskRef.current();
        }
      }).then(fn => { unlistenWake = fn; });
    }

    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
      if (unlistenWake) unlistenWake();
    };
  }, []);

  const startTask = async (task) => {
    if (activeTask && activeTask.id !== task.id && taskStatus === 'running') {
      try { await fetch(`http://localhost:8080/tasks/${activeTask.id}/pause`, { method: "POST" }); } catch (e) { console.error(e); }
    }
    try { await fetch(`http://localhost:8080/tasks/${task.id}/start`, { method: "POST" }); } catch (e) { console.error(e); }

    if (activeTask?.id !== task.id) {
      setElapsedSeconds(0);
    }
    setActiveTask(task);
    setTaskStatus('running');
    
    if (timerRef.current) clearInterval(timerRef.current);
    timerRef.current = setInterval(() => {
      setElapsedSeconds(prev => prev + 1);
    }, 1000);
  };

  const pauseTask = async () => {
    if (taskStatus !== 'running') return;
    try { if (activeTask) await fetch(`http://localhost:8080/tasks/${activeTask.id}/pause`, { method: "POST" }); } catch (e) { console.error(e); }
    setTaskStatus('paused');
    if (timerRef.current) clearInterval(timerRef.current);
  };
  
  // Update ref so the wake event listener always has the latest function closure without re-binding
  pauseTaskRef.current = pauseTask;

  const resumeTask = async () => {
    if (taskStatus !== 'paused' || !activeTask) return;
    try { await fetch(`http://localhost:8080/tasks/${activeTask.id}/resume`, { method: "POST" }); } catch (e) { console.error(e); }
    setTaskStatus('running');
    if (timerRef.current) clearInterval(timerRef.current);
    timerRef.current = setInterval(() => {
      setElapsedSeconds(prev => prev + 1);
    }, 1000);
  };

  const clearTask = () => {
    setActiveTask(null);
    setElapsedSeconds(0);
    setTaskStatus('idle');
    if (timerRef.current) clearInterval(timerRef.current);
  };

  const value = {
    activeTask,
    elapsedSeconds,
    taskStatus,
    startTask,
    pauseTask,
    resumeTask,
    clearTask
  };

  return (
    <ActiveTaskContext.Provider value={value}>
      {children}
    </ActiveTaskContext.Provider>
  );
}
