import { createContext, useContext, useState } from 'react';

const SummaryContext = createContext();

export function SummaryProvider({ children }) {
  const [summaryData, setSummaryData] = useState(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState(null);

  const generateSummary = async () => {
    setIsGenerating(true);
    setError(null);
    try {
      const response = await fetch('http://localhost:8080/summary/generate', {
        method: 'POST'
      });
      
      const data = await response.json();
      
      if (!response.ok) {
        throw new Error(data.detail || 'Failed to generate summary');
      }
      
      setSummaryData(data);
    } catch (err) {
      console.error("Summary generation failed:", err);
      setError(err.message);
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <SummaryContext.Provider value={{ summaryData, isGenerating, error, setError, generateSummary }}>
      {children}
    </SummaryContext.Provider>
  );
}

export function useSummary() {
  return useContext(SummaryContext);
}
