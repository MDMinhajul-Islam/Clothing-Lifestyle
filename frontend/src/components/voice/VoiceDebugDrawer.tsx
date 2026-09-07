import React from 'react';
import { Terminal, ChevronDown, ChevronUp, Clock } from 'lucide-react';
import type { VoiceTurnMessage } from '../../types/voice';

interface VoiceDebugDrawerProps {
  lastTurn: VoiceTurnMessage | null;
  isOpen: boolean;
  onToggle: () => void;
}

export const VoiceDebugDrawer: React.FC<VoiceDebugDrawerProps> = ({
  lastTurn,
  isOpen,
  onToggle,
}) => {
  if (!lastTurn) return null;

  return (
    <div className="border-t border-neutral-200 bg-neutral-900 text-neutral-300 text-xs font-mono transition-all">
      {/* Drawer Toggle Header */}
      <button
        onClick={onToggle}
        className="w-full px-4 py-2 flex items-center justify-between hover:bg-neutral-800 text-neutral-400 hover:text-white transition-colors text-[11px]"
      >
        <div className="flex items-center space-x-2">
          <Terminal className="w-3.5 h-3.5 text-emerald-400" />
          <span className="font-semibold text-neutral-200">Gateway Execution Inspector</span>
          <span className="text-neutral-500">•</span>
          <span className="text-neutral-400">
            Route: <span className="text-emerald-400">{lastTurn.route || 'NONE'}</span>
          </span>
          {lastTurn.toolName && (
            <>
              <span className="text-neutral-500">•</span>
              <span className="text-neutral-400">
                Tool: <span className="text-amber-400">{lastTurn.toolName}</span>
              </span>
            </>
          )}
        </div>

        <div className="flex items-center space-x-2">
          {lastTurn.latencyMs && (
            <span className="flex items-center space-x-1 text-neutral-400">
              <Clock className="w-3 h-3" />
              <span>{lastTurn.latencyMs}ms</span>
            </span>
          )}
          {isOpen ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronUp className="w-3.5 h-3.5" />}
        </div>
      </button>

      {/* Expanded Details Panel */}
      {isOpen && (
        <div className="p-4 border-t border-neutral-800 grid grid-cols-1 md:grid-cols-3 gap-4 text-[11px] max-h-48 overflow-y-auto">
          {/* Column 1: Classification */}
          <div className="space-y-1.5">
            <span className="text-neutral-500 uppercase tracking-widest text-[10px] block">
              1. Orchestration
            </span>
            <div>Route: <span className="text-emerald-400 font-semibold">{lastTurn.route}</span></div>
            <div>Intent: <span className="text-neutral-200">{lastTurn.intent || 'N/A'}</span></div>
            <div>Execution: <span className="text-neutral-200">{lastTurn.executionStatus}</span></div>
          </div>

          {/* Column 2: Tool Resolution */}
          <div className="space-y-1.5">
            <span className="text-neutral-500 uppercase tracking-widest text-[10px] block">
              2. Deterministic Tool
            </span>
            <div>Tool Name: <span className="text-amber-300">{lastTurn.toolName || 'Direct Response'}</span></div>
            <div>Latency: <span className="text-neutral-200">{lastTurn.latencyMs}ms (Sub-second target)</span></div>
            <div>Database Access: <span className="text-emerald-400">Restricted / Gateway Only</span></div>
          </div>

          {/* Column 3: Raw Metadata */}
          <div className="space-y-1.5">
            <span className="text-neutral-500 uppercase tracking-widest text-[10px] block">
              3. Context Payload
            </span>
            <pre className="text-[10px] bg-neutral-950 p-2 border border-neutral-800 text-neutral-400 overflow-x-auto max-h-24">
              {JSON.stringify(lastTurn.rawMetadata || {}, null, 2)}
            </pre>
          </div>
        </div>
      )}
    </div>
  );
};

