import React from 'react';
import { AlertTriangle, CheckCircle2, XCircle, ShieldCheck } from 'lucide-react';
import type { ConfirmationPayload } from '../../types/voice';

interface ConfirmationCardProps {
  payload: ConfirmationPayload;
  onConfirm: () => void;
  onCancel: () => void;
  isSubmitting?: boolean;
}

export const ConfirmationCard: React.FC<ConfirmationCardProps> = ({
  payload,
  onConfirm,
  onCancel,
  isSubmitting,
}) => {
  return (
    <div className="my-3 p-4 bg-amber-50/90 border border-amber-200/80 rounded-none shadow-sm text-xs">
      <div className="flex items-start space-x-3">
        <div className="p-2 bg-amber-100 rounded-full text-amber-800 shrink-0">
          <AlertTriangle className="w-4 h-4" />
        </div>

        <div className="flex-1 space-y-2">
          <div className="flex items-center justify-between">
            <h4 className="font-semibold text-neutral-900 uppercase tracking-wider text-[11px]">
              {payload.headline}
            </h4>
            <span className="flex items-center space-x-1 text-[10px] font-mono text-emerald-700 bg-emerald-100/60 px-2 py-0.5">
              <ShieldCheck className="w-3 h-3" />
              <span>HMAC Protected</span>
            </span>
          </div>

          <p className="text-neutral-700 leading-relaxed">
            {payload.summary}
          </p>

          {payload.token && (
            <div className="p-2 bg-white border border-amber-200 font-mono text-[10px] text-neutral-500 truncate">
              Token: <span className="text-neutral-900 font-medium">{payload.token}</span>
            </div>
          )}

          <div className="flex items-center space-x-3 pt-2">
            <button
              onClick={onConfirm}
              disabled={isSubmitting}
              className="flex items-center space-x-1.5 px-4 py-2 bg-black text-white hover:bg-neutral-800 text-[11px] font-medium tracking-wider uppercase transition-colors disabled:opacity-50"
            >
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
              <span>{isSubmitting ? 'Verifying...' : 'Yes, Confirm Action'}</span>
            </button>

            <button
              onClick={onCancel}
              disabled={isSubmitting}
              className="flex items-center space-x-1 px-3 py-2 bg-white text-neutral-700 hover:text-black border border-neutral-300 text-[11px] tracking-wider uppercase transition-colors"
            >
              <XCircle className="w-3.5 h-3.5 text-neutral-400" />
              <span>Cancel</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

