import { useSummary } from '../../contexts/SummaryContext';
import ReactMarkdown from 'react-markdown';

export default function Summary({ setActiveTab }) {
  const { summaryData, isGenerating, error, generateSummary } = useSummary();

  const handleExportMarkdown = () => {
    if (!summaryData?.summary) return;
    
    const blob = new Blob([summaryData.summary], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `nudge-summary-${new Date().toISOString().split('T')[0]}.md`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="max-w-container-md mx-auto px-margin-mobile md:px-margin-desktop py-stack-lg flex flex-col gap-stack-lg">
      <header className="flex flex-col gap-unit">
        <h1 className="font-headline-xl text-headline-xl text-on-surface">Daily Summary</h1>
        <p className="font-body-md text-body-md text-on-surface-variant">
          {summaryData?.generated_at ? new Date(summaryData.generated_at).toLocaleDateString("en-US", { weekday: "long", month: "short", day: "numeric" }) : "Your productivity overview"}
        </p>
      </header>

      {/* Error Banner */}
      {error && (
        <div className="bg-error/10 border-l-4 border-error p-4 rounded-r-md flex justify-between items-center">
          <span className="text-error font-body-md">{error}</span>
          {error.includes("Settings") && (
            <button 
              onClick={() => setActiveTab('settings')}
              className="bg-error text-on-error px-4 py-1.5 rounded-md font-label-md hover:opacity-90 transition-opacity"
            >
              Go to Settings
            </button>
          )}
        </div>
      )}

      {/* AI Insight Card */}
      <div className="bg-surface-container-low border border-outline-variant rounded-xl p-stack-md flex flex-col gap-stack-sm shadow-sm">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-primary">
            <span className="material-symbols-outlined text-[20px]">auto_awesome</span>
            <h2 className="font-label-lg font-bold uppercase tracking-wider">AI Insight</h2>
          </div>
        </div>
        
        <div className="font-body-lg text-body-lg text-on-surface leading-relaxed">
          {summaryData?.summary ? (
            <div className="prose prose-stone prose-lg max-w-none font-newsreader prose-h2:text-primary prose-h3:text-primary prose-a:text-primary prose-a:no-underline hover:prose-a:underline">
              <ReactMarkdown>{summaryData.summary}</ReactMarkdown>
            </div>
          ) : (
            <p className="italic text-on-surface-variant">
              No summary generated yet. Click "Generate Now" below to create your AI productivity summary.
            </p>
          )}
        </div>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-2 gap-stack-md">
        <div className="bg-surface-container-low border border-outline-variant rounded-xl p-stack-sm flex flex-col items-center justify-center gap-unit text-center">
          <div className="font-headline-xl text-headline-xl text-on-surface">
            {summaryData?.score ? `${summaryData.score}/10` : "--"}
          </div>
          <div className="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-widest">
            Productivity Score
          </div>
        </div>
        
        <div className="bg-surface-container-low border border-outline-variant rounded-xl p-stack-sm flex flex-col items-center justify-center gap-unit text-center">
          <div className="font-headline-xl text-[2rem] text-on-surface">
            {summaryData?.generated_at ? "Done" : "Waiting"}
          </div>
          <div className="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-widest">
            Status
          </div>
        </div>
      </div>

      {/* Actions */}
      <div className="flex flex-col sm:flex-row items-center gap-4 mt-stack-md">
        <button
          onClick={generateSummary}
          disabled={isGenerating}
          className="w-full sm:w-auto px-8 py-3 bg-primary text-on-primary font-label-lg rounded-lg hover:bg-surface-tint disabled:opacity-50 transition-colors shadow-sm"
        >
          {isGenerating ? "Generating..." : "✨ Generate Now"}
        </button>
        
        {summaryData?.summary && (
          <button
            onClick={handleExportMarkdown}
            className="w-full sm:w-auto px-4 py-3 text-primary hover:underline font-label-lg transition-colors flex items-center justify-center gap-2"
          >
            <span className="material-symbols-outlined text-[20px]">download</span>
            Export to Markdown
          </button>
        )}
      </div>
    </div>
  );
}