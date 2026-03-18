import React, { useEffect, useRef, useState } from 'react';

interface Thought {
  _id: string;
  message: string;
  timestamp: string;
}

interface AgentThinkingProps {
  incidentId: string;
  isRunning: boolean;
}

const AgentThinking: React.FC<AgentThinkingProps> = ({ incidentId, isRunning }) => {
  const [thoughts, setThoughts] = useState<Thought[]>([]);
  const [isOpen, setIsOpen] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  const fetchThoughts = async () => {
    try {
      const res = await fetch(`/api/incidents/${incidentId}/thoughts`);
      if (res.ok) {
        const data = await res.json();
        setThoughts(data);
      }
    } catch (e) {
      // silently fail — thoughts are non-critical
    }
  };

  useEffect(() => {
    if (!isOpen) return;
    fetchThoughts();
    if (!isRunning) return;
    const interval = setInterval(fetchThoughts, 2000);
    return () => clearInterval(interval);
  }, [isOpen, isRunning, incidentId]);

  // Auto-scroll to latest thought
  useEffect(() => {
    if (isOpen && bottomRef.current) {
      bottomRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [thoughts, isOpen]);

  const formatTime = (ts: string) => {
    return new Date(ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  };

  return (
    <div className="mt-4">
      <button
        onClick={() => setIsOpen(prev => !prev)}
        className="flex items-center gap-2 px-4 py-2 text-sm font-medium bg-gray-900 text-green-400 rounded-lg hover:bg-gray-800 transition-colors border border-gray-700"
      >
        <span>{isOpen ? '▼' : '▶'}</span>
        <span>🧠 Agent Brain</span>
        {thoughts.length > 0 && (
          <span className="ml-1 px-2 py-0.5 bg-green-900 text-green-300 rounded-full text-xs">
            {thoughts.length}
          </span>
        )}
        {isRunning && isOpen && (
          <span className="ml-1 flex items-center gap-1 text-green-400 text-xs">
            <span className="inline-block w-2 h-2 bg-green-400 rounded-full animate-pulse" />
            live
          </span>
        )}
      </button>

      {isOpen && (
        <div className="mt-2 bg-gray-950 border border-gray-800 rounded-lg p-4 max-h-96 overflow-y-auto font-mono text-sm">
          {thoughts.length === 0 ? (
            <p className="text-gray-500 italic">
              {isRunning ? 'Waiting for agent to start thinking...' : 'No thoughts recorded for this incident.'}
            </p>
          ) : (
            <div className="space-y-3">
              {thoughts.map((t) => (
                <div key={t._id} className="flex gap-3">
                  <span className="text-gray-600 text-xs shrink-0 pt-0.5">{formatTime(t.timestamp)}</span>
                  <p className="text-green-300 leading-relaxed">{t.message}</p>
                </div>
              ))}
              {isRunning && (
                <div className="flex gap-2 items-center text-green-600">
                  <span className="inline-block w-2 h-2 bg-green-500 rounded-full animate-pulse" />
                  <span className="text-xs">Agent is working...</span>
                </div>
              )}
              <div ref={bottomRef} />
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default AgentThinking;
