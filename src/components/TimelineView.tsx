import React, { useState, useEffect, useRef } from 'react';
import { TimelineEvent } from '../types/incident';

interface TimelineViewProps {
  events: TimelineEvent[];
}

const ThinkingIndicator = () => (
  <div className="flex space-x-1 items-center ml-2">
    <div className="w-1.5 h-1.5 bg-blue-500 rounded-full animate-typing-1"></div>
    <div className="w-1.5 h-1.5 bg-blue-500 rounded-full animate-typing-2"></div>
    <div className="w-1.5 h-1.5 bg-blue-500 rounded-full animate-typing-3"></div>
  </div>
);

const TimelineView: React.FC<TimelineViewProps> = ({ events }) => {
  const [visibleCount, setVisibleCount] = useState(0);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (events.length > 0 && visibleCount === 0) {
      setVisibleCount(1);
    }
  }, [events.length, visibleCount]);

  useEffect(() => {
    if (visibleCount > 0 && visibleCount < events.length) {
      const timer = setTimeout(() => {
        setVisibleCount((prev) => prev + 1);
      }, 20); // 80ms fast stagger delay 
      return () => clearTimeout(timer);
    }
  }, [visibleCount, events.length]);

  useEffect(() => {
    if (bottomRef.current && visibleCount > 1) {
      // Smoothly scroll the container downwards as new items appear
      bottomRef.current.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
  }, [visibleCount]);

  const visibleEvents = events.slice(0, visibleCount);

  return (
    <div className="flow-root">
      <ul className="-mb-8">
        {visibleEvents.map((event, eventIdx) => {
          const isAbsoluteLast = eventIdx === events.length - 1;
          const isActive = isAbsoluteLast && !['completed', 'failed', 'pr_created'].includes(event.status.toLowerCase());

          return (
            <li 
              key={eventIdx} 
              className="animate-timeline-enter"
            >
              <div className="relative pb-8">
                {!isAbsoluteLast ? (
                  <span className="absolute top-4 left-4 -ml-px h-full w-0.5 bg-gray-200" aria-hidden="true" />
                ) : null}
                <div className="relative flex space-x-3">
                  <div>
                    <span className="relative flex h-8 w-8 items-center justify-center">
                      {isActive && (
                        <span className="absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75 animate-ping"></span>
                      )}
                      <span className="relative flex h-8 w-8 bg-blue-500 rounded-full items-center justify-center ring-8 ring-white">
                        <span className="text-white text-xs font-bold">
                          {eventIdx + 1}
                        </span>
                      </span>
                    </span>
                  </div>
                  <div className="min-w-0 flex-1 pt-1.5 flex justify-between space-x-4">
                    <div className="flex items-center">
                      <p className="text-sm text-gray-500">
                        {event.message} <span className="font-medium text-gray-900">({event.status})</span>
                      </p>
                      {isActive && <ThinkingIndicator />}
                    </div>
                    <div className="text-right text-sm whitespace-nowrap text-gray-500">
                      <time dateTime={event.timestamp}>
                        {new Date(event.timestamp).toLocaleTimeString()}
                      </time>
                    </div>
                  </div>
                </div>
              </div>
            </li>
          );
        })}
      </ul>
      {/* Invisible anchor for staggered smooth scrolling */}
      <div ref={bottomRef} className="h-1 pb-4 w-full" />
    </div>
  );
};

export default TimelineView;
