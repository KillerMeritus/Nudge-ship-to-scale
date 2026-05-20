import { useState, useEffect, useRef } from 'react';

const POLL_MS = 10_000;
const AUTO_DISMISS_MS = 8_000;

export default function DistractionToast() {
  const [toast, setToast] = useState(null);
  const lastTimestampRef = useRef(null);
  const dismissTimer = useRef(null);

  useEffect(() => {
    const poll = async () => {
      try {
        const res = await fetch('http://localhost:8080/distraction/latest');
        if (!res.ok) return;
        const alert = await res.json();
        if (!alert?.timestamp) return;

        // Show only if this is a newer alert than the last one we displayed
        if (alert.timestamp !== lastTimestampRef.current) {
          lastTimestampRef.current = alert.timestamp;
          setToast(alert);

          clearTimeout(dismissTimer.current);
          dismissTimer.current = setTimeout(() => setToast(null), AUTO_DISMISS_MS);
        }
      } catch {
        // backend offline — stay silent
      }
    };

    poll();
    const interval = setInterval(poll, POLL_MS);
    return () => {
      clearInterval(interval);
      clearTimeout(dismissTimer.current);
    };
  }, []);

  if (!toast) return null;

  const severityStyles = {
    high:   'border-error bg-error/10 text-error',
    medium: 'border-warning bg-warning/10 text-warning',
    low:    'border-outline bg-surface-container text-on-surface',
  };
  const iconStyles = {
    high:   'text-error',
    medium: 'text-warning',
    low:    'text-on-surface-variant',
  };
  const style = severityStyles[toast.severity] ?? severityStyles.medium;
  const iconStyle = iconStyles[toast.severity] ?? iconStyles.medium;

  return (
    <div className={`fixed bottom-6 right-6 z-50 max-w-sm w-full border-l-4 rounded-lg shadow-lg px-4 py-3 flex items-start gap-3 animate-slide-up ${style}`}>
      <span className={`material-symbols-outlined text-[22px] mt-0.5 shrink-0 ${iconStyle}`}>
        psychology_alt
      </span>
      <div className="flex-1 min-w-0">
        <p className="font-label-lg font-semibold leading-tight">Distraction detected</p>
        <p className="font-body-sm text-on-surface-variant mt-0.5 truncate">
          <span className="font-medium">{toast.app_name}</span>
          {' — '}
          {toast.reason}
        </p>
      </div>
      <button
        onClick={() => { clearTimeout(dismissTimer.current); setToast(null); }}
        className="shrink-0 text-on-surface-variant hover:text-on-surface transition-colors mt-0.5"
        aria-label="Dismiss"
      >
        <span className="material-symbols-outlined text-[18px]">close</span>
      </button>
    </div>
  );
}
