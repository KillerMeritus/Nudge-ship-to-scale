import { useState, useEffect } from 'react';
import { enable, disable, isEnabled } from '@tauri-apps/plugin-autostart';
import styles from './Settings.module.css';

export default function Settings() {
  const [aiModel, setAiModel] = useState('gemini');
  const [apiKey, setApiKey] = useState('');
  const [workStartTime, setWorkStartTime] = useState('09:00');
  const [workEndTime, setWorkEndTime] = useState('17:00');
  const [launchOnStartup, setLaunchOnStartup] = useState(false);

  // Fetch settings on mount
  useEffect(() => {
    fetch('http://localhost:8080/settings')
      .then(res => res.json())
      .then(data => {
        setAiModel(data.ai_model || 'gemini');
        setApiKey(data.gemini_api_key || '');
        setWorkStartTime(data.work_start_time || '09:00');
        setWorkEndTime(data.work_end_time || '17:00');
        setLaunchOnStartup(data.launch_on_startup || false);
      })
      .catch(console.error);
      
    if (window.__TAURI_INTERNALS__) {
      isEnabled().then(setLaunchOnStartup).catch(console.error);
    }
  }, []);

  const handleSave = async (e) => {
  e.preventDefault();

  try {
    const response = await fetch("http://localhost:8080/settings", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        ai_model: aiModel,
        gemini_api_key: apiKey,
        work_start_time: workStartTime,
        work_end_time: workEndTime,
        launch_on_startup: launchOnStartup,
      }),
    });

    const data = await response.json();

    console.log("Saved to backend:", data);

    // Apply OS autostart registration
    if (window.__TAURI_INTERNALS__) {
      if (launchOnStartup) {
        await enable();
      } else {
        await disable();
      }
    }

    alert("Settings saved successfully!");
  } catch (error) {
    console.error("Settings save failed:", error);
  }
};

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <h2 className={styles.title}>Settings</h2>
      </div>

      <form onSubmit={handleSave}>
        <div className={styles.section}>
          <h3 className={styles.sectionTitle}>🤖 AI Configuration</h3>
          
          <div className={styles.formGroup}>
            <label className={styles.label}>AI Model</label>
            <select
              className={styles.input}
              value={aiModel}
              onChange={(e) => setAiModel(e.target.value)}
              style={{ padding: '0.75rem', backgroundColor: 'var(--color-bg-secondary)', color: 'var(--color-text)', border: '1px solid var(--color-border)', borderRadius: '0.5rem', width: '100%' }}
            >
              <option value="gemini">Google Gemini (Requires API Key)</option>
              <option value="ollama">Local Ollama (Requires Ollama running)</option>
            </select>
          </div>

          {aiModel === 'gemini' && (
            <div className={styles.formGroup}>
              <label htmlFor="apiKey" className={styles.label}>Gemini API Key</label>
              <input 
                type="password" 
                id="apiKey"
                className={styles.input}
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                placeholder="AIzaSy..."
              />
              <p className={styles.helpText}>Required for daily productivity summaries. Your key is stored securely on your device.</p>
            </div>
          )}
          
          {aiModel === 'ollama' && (
            <div className={styles.formGroup}>
              <p className={styles.helpText} style={{ color: 'var(--color-text-muted)' }}>
                Nudge will connect to your local Ollama instance at <code>http://127.0.0.1:11434</code> using the <code>llama3</code> model. No API key needed.
              </p>
            </div>
          )}
        </div>

        <div className={styles.section}>
          <h3 className={styles.sectionTitle}>🚀 System</h3>
          
          <div className={styles.formGroup}>
            <label className={styles.label}>
              <input 
                type="checkbox" 
                checked={launchOnStartup}
                onChange={(e) => setLaunchOnStartup(e.target.checked)}
                style={{ marginRight: '8px' }}
              />
              Launch Nudge on startup
            </label>
            <p className={styles.helpText}>App will start silently in the menu bar on macOS login.</p>
          </div>
        </div>

        <div className={styles.section}>
          <h3 className={styles.sectionTitle}>⏰ Work Hours</h3>
          
          <div className={styles.formGroup}>
            <label htmlFor="startTime" className={styles.label}>Start Time</label>
            <input 
              type="time" 
              id="startTime"
              className={styles.input}
              value={workStartTime}
              onChange={(e) => setWorkStartTime(e.target.value)}
            />
          </div>

          <div className={styles.formGroup}>
            <label htmlFor="endTime" className={styles.label}>End Time</label>
            <input 
              type="time" 
              id="endTime"
              className={styles.input}
              value={workEndTime}
              onChange={(e) => setWorkEndTime(e.target.value)}
            />
            <p className={styles.helpText}>Scraping automatically pauses outside of work hours.</p>
          </div>
        </div>

        <button type="submit" className={styles.saveBtn}>Save Settings</button>
      </form>

      <div className={styles.footer}>
        <p>Nudge v0.1.0 • Privacy First</p>
      </div>
    </div>
  );
}
