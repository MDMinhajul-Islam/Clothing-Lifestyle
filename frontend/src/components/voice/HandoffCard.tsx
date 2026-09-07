import React from 'react';
import { UserCheck, Clock, CheckCircle } from 'lucide-react';
import type { HandoffDetails } from '../../types/voice';

interface HandoffCardProps {
  details: HandoffDetails;
}

export const HandoffCard: React.FC<HandoffCardProps> = ({ details }) => {
  return (
    <div className="my-3 p-4 bg-neutral-900 text-white text-xs border border-neutral-800 shadow-md">
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center space-x-2">
          <div className="p-1.5 bg-emerald-500/20 text-emerald-400 rounded-full">
            <UserCheck className="w-4 h-4" />
          </div>
          <div>
            <h4 className="font-semibold uppercase tracking-wider text-[11px] text-white">
              Concierge Stylist Escalation
            </h4>
            <span className="text-[10px] text-neutral-400 font-mono">{details.department}</span>
          </div>
        </div>

        <span className="px-2 py-0.5 bg-neutral-800 text-neutral-300 font-mono text-[10px]">
          Queue: {details.assignedQueue}
        </span>
      </div>

      <p className="text-neutral-300 text-[11px] leading-relaxed mb-3">
        {details.reason}
      </p>

      <div className="pt-2 border-t border-neutral-800 flex items-center justify-between text-[10px] text-neutral-400 font-mono">
        <div className="flex items-center space-x-1.5">
          <Clock className="w-3 h-3 text-neutral-400" />
          <span>Est. connection time: ~{details.estimatedWaitMinutes} min</span>
        </div>
        <div className="flex items-center space-x-1 text-emerald-400">
          <CheckCircle className="w-3 h-3" />
          <span>Cart & Context Synced</span>
        </div>
      </div>
    </div>
  );
};

