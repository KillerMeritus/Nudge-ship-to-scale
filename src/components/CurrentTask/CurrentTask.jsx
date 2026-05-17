import { useEffect, useRef, useState } from 'react';
import { invoke } from '@tauri-apps/api/core';
import { listen } from '@tauri-apps/api/event';
import { useTimer } from '../../contexts/TimerContext';
import { useActiveTask } from '../../contexts/ActiveTaskContext';
import { sendPreset } from '../../utils/notify';
import { playSound } from '../../utils/sound';

const MODES = {
  focus:      { id: 'focus',      label: 'Focus',       duration: 25 * 60 },
  shortBreak: { id: 'short_break', label: 'Short Break',  duration: 5  * 60 },
  longBreak:  { id: 'long_break',  label: 'Long Break',   duration: 15 * 60 },
};

/** Format seconds → "MM:SS" or "HH:MM:SS" */
function fmt(seconds) {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60).toString().padStart(2, '0');
  const s = (seconds % 60).toString().padStart(2, '0');
  if (h > 0) return `${h}:${m}:${s}`;
  return `${m}:${s}`;
}

export default function CurrentTask() {
  const {
    status,
    remainingSeconds,
    sessionType,
    start,
    pause,
    reset,
    changeMode
  } = useTimer();

  const {
    activeTask,
    elapsedSeconds,
    taskStatus,
    pauseTask,
    resumeTask,
  } = useActiveTask();

  const [tasks, setTasks] = useState([]);

  useEffect(() => {
    fetch('http://localhost:8080/tasks')
      .then(res => res.json())
      .then(data => setTasks(data))
      .catch(console.error);
  }, []);

  const isActive = status === 'running';
  
  const isActiveRef = useRef(isActive);
  const sessionTypeRef = useRef(sessionType);
  
  useEffect(() => { isActiveRef.current = isActive; }, [isActive]);
  useEffect(() => { sessionTypeRef.current = sessionType; }, [sessionType]);

  // ── Push timer state to tray every tick ────────────────────────────────────
  useEffect(() => {
    if (!window.__TAURI_INTERNALS__) return;

    let modeConfig = MODES.focus;
    if (sessionType === 'short_break') modeConfig = MODES.shortBreak;
    if (sessionType === 'long_break') modeConfig = MODES.longBreak;

    let label = '';
    if (activeTask) {
      label = `Task: ${activeTask.title} (${fmt(elapsedSeconds)})`;
    } else {
      label = isActive
        ? `${modeConfig.label}: ${fmt(remainingSeconds)} remaining`
        : remainingSeconds === modeConfig.duration
          ? '' // idle / reset — show default "Idle" in tray
          : `${modeConfig.label}: ${fmt(remainingSeconds)} (paused)`;
    }

    invoke('update_tray_timer', { label }).catch(() => {
      // Silently ignore — tray label update is non-critical
    });
  }, [remainingSeconds, isActive, sessionType, activeTask, elapsedSeconds]);

  // ── Listen for tray menu events emitted by Rust ────────────────────────────
  useEffect(() => {
    if (!window.__TAURI_INTERNALS__) return;

    const unlistenStart = listen('tray-start-focus', () => {
      if (!isActiveRef.current) {
        start();
        if (sessionTypeRef.current === 'focus') {
           sendPreset('DEEP_WORK_STARTED');
           playSound('deep_work_start');
        }
      }
    });

    const unlistenPause = listen('tray-pause-timer', () => {
      if (isActiveRef.current) {
        pause();
      }
    });

    return () => {
      unlistenStart.then((fn) => fn());
      unlistenPause.then((fn) => fn());
    };
  }, [start, pause]);

  // ── Timer controls ─────────────────────────────────────────────────────────
  const toggleTimer = () => {
    if (isActive) {
      pause();
    } else {
      start();
      if (sessionType === 'focus') {
        sendPreset('DEEP_WORK_STARTED');
        playSound('deep_work_start');
      }
    }
  };

  const skipTimer = () => {
    if (sessionType === 'focus') {
      changeMode('short_break');
    } else {
      changeMode('focus');
    }
  };

  const toggleTaskTimer = () => {
    if (taskStatus === 'running') {
      pauseTask();
    } else {
      resumeTask();
    }
  };

  // Determine what to display
  let currentDuration = MODES.focus.duration;
  if (sessionType === 'short_break') currentDuration = MODES.shortBreak.duration;
  if (sessionType === 'long_break') currentDuration = MODES.longBreak.duration;

  const displayTime = activeTask 
    ? fmt(elapsedSeconds)
    : fmt(remainingSeconds);

  // Next tasks logic
  const upcomingTasks = tasks
    .filter(t => t.status === 'todo' && (!activeTask || t.id !== activeTask.id))
    .slice(0, 3); // Get top 3 upcoming

  return (
    <div className="flex flex-col items-center justify-center relative h-full overflow-y-auto w-full p-8">
      
      {/* Background Focus Pattern (Optional/Subtle) */}
      <div className="absolute inset-0 z-0 opacity-[0.02] pointer-events-none flex items-center justify-center">
        {/* Can put an SVG pattern here in the future if desired */}
      </div>

      {/* Mode Selector (Only shown if no active task is running, to keep it simple) */}
      {!activeTask && (
        <div className="absolute top-8 left-1/2 -translate-x-1/2 flex items-center gap-2 bg-surface-container-low rounded-full p-1 z-20 shadow-sm border border-outline-variant">
           <button 
             onClick={() => changeMode('focus')}
             className={`px-4 py-1.5 rounded-full text-label-md transition-colors ${
               sessionType === 'focus' ? 'bg-primary text-on-primary font-bold shadow' : 'text-on-surface-variant hover:text-on-surface'
             }`}
           >
             Focus
           </button>
           <button 
             onClick={() => changeMode('short_break')}
             className={`px-4 py-1.5 rounded-full text-label-md transition-colors ${
               sessionType === 'short_break' ? 'bg-primary text-on-primary font-bold shadow' : 'text-on-surface-variant hover:text-on-surface'
             }`}
           >
             Short Break
           </button>
           <button 
             onClick={() => changeMode('long_break')}
             className={`px-4 py-1.5 rounded-full text-label-md transition-colors ${
               sessionType === 'long_break' ? 'bg-primary text-on-primary font-bold shadow' : 'text-on-surface-variant hover:text-on-surface'
             }`}
           >
             Long Break
           </button>
        </div>
      )}

      <div className="w-full max-w-5xl mx-auto px-margin-desktop flex flex-col md:flex-row items-center justify-center min-h-full gap-12 lg:gap-24 relative z-10">
        
        {/* Left: Timer Section */}
        <div className="flex flex-col items-center">
          
          {/* Timer Display */}
          <div className="relative flex items-center justify-center w-64 h-64 md:w-80 md:h-80 rounded-full border border-outline bg-surface-container-lowest/70 backdrop-blur-md shadow-sm mb-stack-lg transition-colors">
            
            {/* Inner subtle ring for depth */}
            <div className="absolute inset-2 rounded-full border border-surface-variant opacity-50"></div>
            
            <span className={`font-headline-xl text-headline-xl md:scale-125 tracking-tight transition-colors ${
                (activeTask && taskStatus === 'running') || (!activeTask && isActive) ? 'text-primary' : 'text-on-surface'
              }`} 
              style={{ fontFeatureSettings: "'tnum' 1" }}>
              {displayTime}
            </span>
            
          </div>

          {/* Controls */}
          <div className="flex items-center gap-4">
            {activeTask ? (
              <button 
                onClick={toggleTaskTimer}
                className="px-8 py-3 bg-primary text-on-primary font-label-lg rounded-lg hover:bg-surface-tint transition-colors focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2 focus:ring-offset-surface"
              >
                {taskStatus === 'running' ? 'Pause Task' : 'Resume Task'}
              </button>
            ) : (
              <>
                <button 
                  onClick={toggleTimer}
                  className="px-8 py-3 bg-primary text-on-primary font-label-lg rounded-lg hover:bg-surface-tint transition-colors focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2 focus:ring-offset-surface w-32 text-center"
                >
                  {isActive ? 'Pause' : 'Start'}
                </button>
                <button 
                  onClick={reset}
                  className="px-8 py-3 bg-transparent text-on-surface font-label-lg rounded-lg hover:bg-surface-container transition-all focus:outline-none border border-transparent hover:border-outline-variant"
                >
                  Reset
                </button>
                <button 
                  onClick={skipTimer}
                  className="px-8 py-3 bg-transparent text-on-surface font-label-lg rounded-lg hover:bg-surface-container transition-all focus:outline-none border border-transparent hover:border-outline-variant"
                >
                  Skip
                </button>
              </>
            )}
          </div>
        </div>

        {/* Right: Focus Dashboard Section */}
        <div className="flex flex-col max-w-md w-full gap-8">
          
          {/* Current Focus */}
          <div>
            <h2 className="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-widest mb-3">
              {activeTask ? 'Current Focus' : 'Pomodoro Status'}
            </h2>
            <h1 className={`font-headline-lg text-headline-lg mb-4 leading-tight ${activeTask ? 'text-on-surface' : 'text-on-surface-variant italic'}`}>
              {activeTask ? activeTask.title : 'No specific task selected. Just focusing.'}
            </h1>
            
            {activeTask && (
              <div className="flex items-center gap-2 text-on-surface-variant">
                <span className="material-symbols-outlined text-[18px]">schedule</span>
                <span className="font-label-md text-label-md">
                  {Math.floor(elapsedSeconds / 60)} mins elapsed
                </span>
                {activeTask.estimated_minutes && (
                  <>
                    <span className="mx-1">•</span>
                    <span className="font-label-md text-label-md">
                      {activeTask.estimated_minutes} min est.
                    </span>
                  </>
                )}
              </div>
            )}
          </div>
          
          <hr className="border-outline-variant/50 w-16" />
          
          {/* Coming Up Next */}
          <div>
            <h3 className="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-widest mb-4">Coming Up Next</h3>
            {upcomingTasks.length > 0 ? (
              <ul className="space-y-4">
                {upcomingTasks.map(t => (
                  <li key={t.id} className="flex items-start gap-3">
                    <div className="w-5 h-5 rounded border border-outline-variant mt-0.5 shrink-0 bg-surface-container"></div>
                    <span className="font-body-md text-body-md text-on-surface">{t.title}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-body-md text-on-surface-variant italic">No upcoming tasks.</p>
            )}
          </div>
        </div>

      </div>
    </div>
  );
}
