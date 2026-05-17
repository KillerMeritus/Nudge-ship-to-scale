import { useState, useEffect } from 'react';
import { TimerProvider } from './contexts/TimerContext';
import { ActiveTaskProvider } from './contexts/ActiveTaskContext';
import { SummaryProvider } from './contexts/SummaryContext';

import './styles/global.css';
import CurrentTask from './components/CurrentTask/CurrentTask';
import TaskList from './components/Tasks/TaskList';
import Summary from './components/Summary/Summary';
import Settings from './components/Settings/Settings';
import styles from './App.module.css';
// [DEV] Notification + sound utilities — remove demo button before shipping v1
import { sendPreset } from './utils/notify';
import { playSound } from './utils/sound';

const TABS = [
  { id: 'timer',    label: '🎯 Current Task' },
  { id: 'tasks',    label: '✅ Tasks' },
  { id: 'summary',  label: '📊 Summary' },
  { id: 'settings', label: '⚙️ Settings' },
];

export default function App() {
  const [activeTab, setActiveTab] = useState('timer');
  const [distractionCount, setDistractionCount] = useState(0);

  useEffect(() => {
    const fetchDistractions = async () => {
      try {
        const res = await fetch('http://localhost:8080/distraction/today');
        if (res.ok) {
          const data = await res.json();
          setDistractionCount(data.count || 0);
        }
      } catch (err) {
        console.error('Failed to fetch distraction count', err);
      }
    };

    // Initial fetch
    fetchDistractions();

    // Poll every 30 seconds
    const interval = setInterval(fetchDistractions, 30000);
    return () => clearInterval(interval);
  }, []);

  return (
    <TimerProvider>
      <ActiveTaskProvider>
        <SummaryProvider>
          <div className={styles.shell}>
            {/* ── NAV BAR ── */}
            <nav className={styles.nav}>
              <span className={styles.logo}>Nudge</span>
              <div className={styles.tabs} role="tablist">
                {TABS.map((tab) => (
                  <button
                    key={tab.id}
                    id={`tab-${tab.id}`}
                    role="tab"
                    aria-selected={activeTab === tab.id}
                    className={`${styles.tab} ${activeTab === tab.id ? styles.tabActive : ''}`}
                    onClick={() => setActiveTab(tab.id)}
                  >
                    {tab.label}
                    {tab.id === 'summary' && distractionCount > 0 && (
                      <span style={{
                        backgroundColor: 'var(--color-danger)',
                        color: 'white',
                        borderRadius: '12px',
                        padding: '2px 6px',
                        fontSize: '11px',
                        marginLeft: '6px',
                        fontWeight: 'bold',
                      }}>
                        {distractionCount}
                      </span>
                    )}
                  </button>
                ))}
              </div>

              {/* [DEV] Temporary — test all three notification presets. Remove before v1 release. */}
              <button
                id="dev-test-notifications"
                title="Dev: test notifications"
                style={{
                  marginLeft: 'auto',
                  padding: '4px 10px',
                  fontSize: '11px',
                  opacity: 0.5,
                  cursor: 'pointer',
                  borderRadius: '6px',
                  border: '1px solid currentColor',
                  background: 'transparent',
                  color: 'inherit',
                }}
                onClick={async () => {
                  // Fire notification + sound for each preset with staggered timing.
                  await sendPreset('DEEP_WORK_STARTED');
                  playSound('deep_work_start');
                  setTimeout(() => { sendPreset('POMODORO_COMPLETE'); playSound('pomodoro_complete'); }, 1500);
                  setTimeout(() => { sendPreset('SUMMARY_GENERATED'); playSound('summary_generated'); }, 3000);
                }}
              >
                🔔 Test
              </button>
            </nav>

            {/* ── CONTENT ── */}
            <main className={styles.content}>
              {activeTab === 'timer'    && <CurrentTask />}
              {activeTab === 'tasks'    && <TaskList />}
              {activeTab === 'summary'  && <Summary setActiveTab={setActiveTab} />}
              {activeTab === 'settings' && <Settings />}
            </main>
          </div>
        </SummaryProvider>
      </ActiveTaskProvider>
    </TimerProvider>
  );
}
