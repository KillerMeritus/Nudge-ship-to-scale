import { useState, useEffect } from 'react';
import { enable, disable, isEnabled } from '@tauri-apps/plugin-autostart';

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
        headers: { "Content-Type": "application/json" },
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
    <div className="max-w-container-md mx-auto px-margin-mobile md:px-margin-desktop py-stack-lg flex flex-col gap-stack-lg">
      <header className="flex flex-col gap-unit">
        <h1 className="font-headline-xl text-headline-xl text-on-surface">Settings</h1>
        <p className="font-body-lg text-body-lg text-on-surface-variant">Configure Nudge to fit your workflow.</p>
      </header>

      <form onSubmit={handleSave} className="flex flex-col gap-stack-lg">
        
        {/* AI Configuration */}
        <section className="flex flex-col gap-stack-sm">
          <h2 className="font-headline-lg text-headline-lg text-on-surface">AI Configuration</h2>
          <p className="font-body-md text-body-md text-on-surface-variant mb-unit">
            Choose how Nudge analyzes your productivity.
          </p>
          
          <div className="flex flex-col gap-2">
            <label className="font-label-md text-on-surface">AI Model</label>
            <select
              value={aiModel}
              onChange={(e) => setAiModel(e.target.value)}
              className="bg-surface-container-low border border-outline-variant rounded-md px-4 py-3 font-body-md text-on-surface focus:border-primary focus:ring-1 focus:ring-primary outline-none transition-colors"
            >
              <option value="gemini">Google Gemini (Requires API Key)</option>
              <option value="ollama">Local Ollama (Requires Ollama running)</option>
            </select>
          </div>

          {aiModel === 'gemini' && (
            <div className="flex flex-col gap-2 mt-unit">
              <label htmlFor="apiKey" className="font-label-md text-on-surface">Gemini API Key</label>
              <input 
                type="password" 
                id="apiKey"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                placeholder="AIzaSy..."
                className="bg-surface-container-low border border-outline-variant rounded-md px-4 py-3 font-body-md text-on-surface placeholder-outline-variant focus:border-primary focus:ring-1 focus:ring-primary outline-none transition-colors"
              />
              <p className="font-label-sm text-on-surface-variant italic mt-1">
                Required for daily productivity summaries. Your key is stored securely on your device.
              </p>
            </div>
          )}
          
          {aiModel === 'ollama' && (
            <div className="bg-surface-variant/30 border border-outline-variant rounded-md p-4 mt-unit">
              <p className="font-body-md text-on-surface-variant">
                Nudge will connect to your local Ollama instance at <code className="font-mono text-sm bg-surface-container px-1 rounded">http://127.0.0.1:11434</code> using the <code className="font-mono text-sm bg-surface-container px-1 rounded">qwen2.5:0.5b</code> model (ultra-fast, tiny). No API key needed.
              </p>
            </div>
          )}
        </section>

        <hr className="border-outline-variant/50" />

        {/* System Settings */}
        <section className="flex flex-col gap-stack-sm">
          <h2 className="font-headline-lg text-headline-lg text-on-surface">System</h2>
          
          <label className="flex items-center gap-3 cursor-pointer group mt-unit">
            <div className="relative">
              <input 
                type="checkbox" 
                checked={launchOnStartup}
                onChange={(e) => setLaunchOnStartup(e.target.checked)}
                className="sr-only peer"
              />
              <div className="w-11 h-6 bg-surface-variant peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-surface-variant after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary"></div>
            </div>
            <div className="flex flex-col">
              <span className="font-label-lg text-on-surface">Launch Nudge on startup</span>
              <span className="font-label-sm text-on-surface-variant">App will start silently in the menu bar on macOS login.</span>
            </div>
          </label>
        </section>

        <hr className="border-outline-variant/50" />

        {/* Work Hours */}
        <section className="flex flex-col gap-stack-sm">
          <h2 className="font-headline-lg text-headline-lg text-on-surface">Work Hours</h2>
          <p className="font-body-md text-body-md text-on-surface-variant mb-unit">
            Scraping automatically pauses outside of work hours.
          </p>
          
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-stack-md">
            <div className="flex flex-col gap-2">
              <label htmlFor="startTime" className="font-label-md text-on-surface">Start Time</label>
              <input 
                type="time" 
                id="startTime"
                value={workStartTime}
                onChange={(e) => setWorkStartTime(e.target.value)}
                className="bg-surface-container-low border border-outline-variant rounded-md px-4 py-3 font-body-md text-on-surface focus:border-primary focus:ring-1 focus:ring-primary outline-none transition-colors"
              />
            </div>

            <div className="flex flex-col gap-2">
              <label htmlFor="endTime" className="font-label-md text-on-surface">End Time</label>
              <input 
                type="time" 
                id="endTime"
                value={workEndTime}
                onChange={(e) => setWorkEndTime(e.target.value)}
                className="bg-surface-container-low border border-outline-variant rounded-md px-4 py-3 font-body-md text-on-surface focus:border-primary focus:ring-1 focus:ring-primary outline-none transition-colors"
              />
            </div>
          </div>
        </section>

        {/* Actions */}
        <div className="flex justify-end pt-stack-sm">
          <button 
            type="submit" 
            className="px-8 py-3 bg-primary text-on-primary font-label-lg rounded-lg hover:bg-surface-tint transition-colors shadow-sm focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2 focus:ring-offset-background"
          >
            Save Preferences
          </button>
        </div>
      </form>
    </div>
  );
}
