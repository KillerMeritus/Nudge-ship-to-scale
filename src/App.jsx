import { useState, useEffect } from 'react';
import { TimerProvider } from './contexts/TimerContext';
import { ActiveTaskProvider } from './contexts/ActiveTaskContext';
import { SummaryProvider } from './contexts/SummaryContext';

import './styles/global.css';
import CurrentTask from './components/CurrentTask/CurrentTask';
import TaskList from './components/Tasks/TaskList';
import Summary from './components/Summary/Summary';
import Settings from './components/Settings/Settings';
import DistractionToast from './components/DistractionToast/DistractionToast';
import { sendPreset } from './utils/notify';
import { playSound } from './utils/sound';

const TABS = [
  { id: 'timer',    icon: 'timer',       label: 'Timer' },
  { id: 'tasks',    icon: 'task_alt',    label: 'Tasks' },
  { id: 'summary',  icon: 'auto_awesome',label: 'Summary' },
  { id: 'settings', icon: 'settings',    label: 'Settings' },
];

export default function App() {
  const [activeTab, setActiveTab] = useState('timer');
  const [distractionCount, setDistractionCount] = useState(0);

  useEffect(() => {
    const fetchDistractions = async () => {
      try {
        const res = await fetch('http://localhost:8080/distraction/today/count');
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
          {/* Main App Shell Layout */}
          <div className="flex h-screen w-full bg-background font-inter text-on-background selection:bg-primary selection:text-on-primary">
            
            {/* SIDEBAR */}
            <nav className="w-56 shrink-0 bg-surface-container-low border-r border-outline-variant flex flex-col pt-8 pb-4">
              <div className="px-6 mb-8 flex items-center justify-between">
                <span className="font-newsreader text-headline-md italic text-primary">Nudge</span>
              </div>
              
              <div className="flex-1 flex flex-col gap-1 px-3">
                {TABS.map((tab) => (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id)}
                    className={`flex items-center gap-3 px-3 py-2 rounded-md text-label-lg transition-colors ${
                      activeTab === tab.id 
                        ? 'bg-primary text-on-primary font-medium' 
                        : 'text-on-surface-variant hover:bg-surface-container hover:text-on-surface'
                    }`}
                  >
                    <span className="material-symbols-outlined text-[20px]">{tab.icon}</span>
                    {tab.label}
                    {tab.id === 'summary' && distractionCount > 0 && (
                      <span className={`ml-auto text-label-sm px-2 py-0.5 rounded-full font-bold ${
                        activeTab === tab.id
                          ? 'bg-on-primary text-primary'
                          : 'bg-error text-on-error'
                      }`}>
                        {distractionCount}
                      </span>
                    )}
                  </button>
                ))}
              </div>

              {/* Dev Notifier Test */}
              <div className="px-6 mt-auto">
                <button
                  className="w-full py-1.5 px-3 border border-outline-variant rounded-md text-label-sm text-on-surface-variant hover:bg-surface-container hover:text-on-surface transition-colors flex items-center justify-center gap-2 opacity-50"
                  onClick={async () => {
                    await sendPreset('DEEP_WORK_STARTED');
                    playSound('deep_work_start');
                    setTimeout(() => { sendPreset('POMODORO_COMPLETE'); playSound('pomodoro_complete'); }, 1500);
                    setTimeout(() => { sendPreset('SUMMARY_GENERATED'); playSound('summary_generated'); }, 3000);
                  }}
                  title="Test notifications"
                >
                  <span className="material-symbols-outlined text-[16px]">notifications</span>
                  Test Alerts
                </button>
              </div>
            </nav>

            {/* CONTENT AREA */}
            <main className="flex-1 overflow-y-auto bg-background">
              {activeTab === 'timer'    && <CurrentTask />}
              {activeTab === 'tasks'    && <TaskList />}
              {activeTab === 'summary'  && <Summary setActiveTab={setActiveTab} />}
              {activeTab === 'settings' && <Settings />}
            </main>
          </div>

          <DistractionToast />
        </SummaryProvider>
      </ActiveTaskProvider>
    </TimerProvider>
  );
}
