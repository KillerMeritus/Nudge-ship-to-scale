import { useEffect, useRef } from 'react';
import styles from './CurrentTask.module.css';
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
    resumeTask
  } = useActiveTask();

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

  // Calculate SVG stroke-dashoffset
  const radius = 120;
  const circumference = 2 * Math.PI * radius;
  
  let currentDuration = MODES.focus.duration;
  if (sessionType === 'short_break') currentDuration = MODES.shortBreak.duration;
  if (sessionType === 'long_break') currentDuration = MODES.longBreak.duration;

  const progress = remainingSeconds / currentDuration;
  const dashOffset = circumference - progress * circumference;

  // Task time calculations
  let taskDisplayTime = fmt(elapsedSeconds);
  let taskDashOffset = circumference;
  
  if (activeTask) {
    const taskTotalSeconds = (activeTask.estimated_hours || 0) * 3600 + (activeTask.estimated_minutes || 0) * 60;
    if (taskTotalSeconds > 0) {
      const remaining = taskTotalSeconds - elapsedSeconds;
      if (remaining < 0) {
        taskDisplayTime = `-${fmt(Math.abs(remaining))}`;
      } else {
        taskDisplayTime = fmt(remaining);
      }
      
      const taskProgress = Math.min(elapsedSeconds / taskTotalSeconds, 1);
      taskDashOffset = circumference - taskProgress * circumference;
    }
  }

  return (
    <div className={styles.container}>
      {activeTask ? (
        <div style={{ textAlign: 'center', flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
          <h2 style={{ fontSize: '24px', fontWeight: 600, color: 'var(--text-primary)', margin: '0 0 16px 0' }}>
            {activeTask.title}
          </h2>
          
          <div className={styles.timerRing}>
            <svg width="280" height="280" viewBox="0 0 280 280">
              <circle 
                className={styles.ringBackground} 
                cx="140" cy="140" r="120" 
              />
              <circle 
                className={styles.ringProgress} 
                cx="140" cy="140" r="120"
                strokeDasharray={circumference}
                strokeDashoffset={taskDashOffset}
                transform="rotate(-90 140 140)"
                style={{ stroke: 'var(--accent)' }}
              />
            </svg>
            <div className={styles.timeDisplay}>
              {taskDisplayTime}
            </div>
          </div>

          <div style={{ fontSize: '14px', color: 'var(--text-secondary)', marginTop: '24px', marginBottom: '16px' }}>
            {taskStatus === 'paused' ? 'Paused' : 'Running'}
          </div>
          {taskStatus === 'paused' ? (
            <button onClick={resumeTask} className={styles.modeBtn} style={{ background: 'var(--bg-overlay)' }}>Resume Task</button>
          ) : (
            <button onClick={pauseTask} className={styles.modeBtn} style={{ background: 'var(--bg-overlay)' }}>Pause Task</button>
          )}
        </div>
      ) : (
        <>
          <header>
            <div className={styles.modeSelector}>
              <button 
                className={`${styles.modeBtn} ${sessionType === 'focus' ? styles.modeBtnActive : ''}`}
                onClick={() => changeMode('focus')}
              >
                Focus
              </button>
              <button 
                className={`${styles.modeBtn} ${sessionType === 'short_break' ? styles.modeBtnActive : ''}`}
                onClick={() => changeMode('short_break')}
              >
                Short Break
              </button>
              <button 
                className={`${styles.modeBtn} ${sessionType === 'long_break' ? styles.modeBtnActive : ''}`}
                onClick={() => changeMode('long_break')}
              >
                Long Break
              </button>
            </div>
          </header>

          <div className={styles.timerRing}>
            <svg width="280" height="280" viewBox="0 0 280 280">
              <circle 
                className={styles.ringBackground} 
                cx="140" cy="140" r="120" 
              />
              <circle 
                className={styles.ringProgress} 
                cx="140" cy="140" r="120"
                strokeDasharray={circumference}
                strokeDashoffset={dashOffset}
                transform="rotate(-90 140 140)"
              />
            </svg>
            <div className={styles.timeDisplay}>
              {fmt(remainingSeconds)}
            </div>
          </div>

          <div className={styles.controls}>
            <button 
              className={styles.playBtn}
              onClick={toggleTimer}
            >
              {isActive ? 'Pause' : 'Start'}
            </button>
            
            <button className={styles.iconBtn} onClick={reset} title="Reset">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8" />
                <path d="M3 3v5h5" />
              </svg>
            </button>
            
            <button className={styles.iconBtn} onClick={skipTimer} title="Skip">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <polygon points="5 4 15 12 5 20 5 4" />
                <line x1="19" y1="5" x2="19" y2="19" />
              </svg>
            </button>
          </div>
        </>
      )}
    </div>
  );
}
