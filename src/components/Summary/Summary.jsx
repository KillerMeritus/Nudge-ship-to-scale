import { useSummary } from '../../contexts/SummaryContext';
import styles from './Summary.module.css';

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
    <div className={styles.container}>
      <div className={styles.header}>
        <h2 className={styles.title}>Daily Summary</h2>

        <button
          className={styles.generateBtn}
          onClick={generateSummary}
          disabled={isGenerating}
        >
          {isGenerating ? "Generating..." : "✨ Generate Now"}
        </button>
      </div>

      {error && (
        <div className={styles.errorBanner} style={{
          backgroundColor: 'rgba(239, 68, 68, 0.1)',
          borderLeft: '4px solid var(--color-danger)',
          padding: '1rem',
          marginBottom: '1rem',
          borderRadius: '4px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center'
        }}>
          <span style={{ color: 'var(--color-danger)' }}>{error}</span>
          {error.includes("Settings") && (
            <button 
              onClick={() => setActiveTab('settings')}
              style={{
                backgroundColor: 'var(--color-danger)',
                color: 'white',
                border: 'none',
                padding: '0.5rem 1rem',
                borderRadius: '4px',
                cursor: 'pointer'
              }}
            >
              Go to Settings
            </button>
          )}
        </div>
      )}

      <div className={styles.summaryCard}>
        <div className={styles.cardHeader}>
          <div className={styles.cardTitle}>
            <span>🤖</span> AI Insights
          </div>

          <div className={styles.date}>
            {summaryData?.generated_at
              ? new Date(summaryData.generated_at).toLocaleDateString(
                  "en-US",
                  {
                    weekday: "long",
                    month: "short",
                    day: "numeric",
                  }
                )
              : "No summary yet"}
          </div>
          
          {summaryData?.summary && (
            <button
              onClick={handleExportMarkdown}
              style={{
                backgroundColor: 'var(--color-bg-tertiary)',
                color: 'var(--color-text)',
                border: '1px solid var(--color-border)',
                padding: '4px 12px',
                borderRadius: '4px',
                cursor: 'pointer',
                fontSize: '0.85rem'
              }}
            >
              📥 Export Markdown
            </button>
          )}
        </div>

        <div className={styles.content}>
          {summaryData?.summary ? (
            <pre
              style={{
                whiteSpace: "pre-wrap",
                fontFamily: "inherit",
                lineHeight: "1.6",
              }}
            >
              {summaryData?.summary}
            </pre>
          ) : (
            <p>
              No summary generated yet. Click{" "}
              <strong>Generate Now</strong> to create your AI productivity
              summary.
            </p>
          )}
        </div>

        <div className={styles.metrics}>
          <div className={styles.metricBox}>
            <div className={styles.metricValue}>
              {summaryData?.score
                ? `${summaryData.score}/10`
                : "--"}
            </div>

            <div className={styles.metricLabel}>
              Productivity Score
            </div>
          </div>

          <div className={styles.metricBox}>
            <div className={styles.metricValue}>
              {summaryData?.generated_at
                ? "Generated"
                : "Waiting"}
            </div>

            <div className={styles.metricLabel}>
              Summary Status
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}