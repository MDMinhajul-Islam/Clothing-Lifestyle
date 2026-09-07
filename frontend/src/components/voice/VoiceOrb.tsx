import React from 'react';
import type { VoiceState } from '../../types/voice';

interface VoiceOrbProps {
  state: VoiceState;
  isMuted?: boolean;
}

export const VoiceOrb: React.FC<VoiceOrbProps> = ({ state, isMuted }) => {
  return (
    <div className="relative flex items-center justify-center w-28 h-28 my-2">
      {/* Outer Halo Rings */}
      {state === 'LISTENING' && !isMuted && (
        <>
          <span className="absolute w-24 h-24 rounded-full border border-emerald-400/40 animate-ping opacity-75" />
          <span className="absolute w-28 h-28 rounded-full border border-emerald-500/20 animate-pulse" />
        </>
      )}

      {state === 'THINKING' && (
        <span className="absolute w-24 h-24 rounded-full border-2 border-dashed border-neutral-400 animate-spin" />
      )}

      {state === 'SPEAKING' && (
        <>
          <span className="absolute w-24 h-24 rounded-full bg-neutral-900/10 animate-ping opacity-50" />
          <span className="absolute w-26 h-26 rounded-full border border-neutral-800/30 animate-pulse" />
        </>
      )}

      {/* Core Animated Orb */}
      <div
        className={`relative w-16 h-16 rounded-full flex items-center justify-center transition-all duration-500 shadow-xl ${
          state === 'LISTENING'
            ? 'bg-gradient-to-tr from-emerald-600 to-teal-400 shadow-emerald-500/30 scale-110'
            : state === 'SPEAKING'
            ? 'bg-gradient-to-tr from-neutral-900 via-neutral-700 to-neutral-900 shadow-neutral-900/40 scale-105'
            : state === 'THINKING'
            ? 'bg-gradient-to-tr from-neutral-600 via-neutral-400 to-neutral-700 shadow-neutral-500/30 animate-pulse'
            : 'bg-neutral-200 border border-neutral-300'
        }`}
      >
        {/* Interior Waveform Bars */}
        <div className="flex items-center space-x-1 h-6">
          <span
            className={`w-1 rounded-full transition-all duration-300 ${
              state === 'LISTENING'
                ? 'h-5 bg-white animate-bounce'
                : state === 'SPEAKING'
                ? 'h-6 bg-white animate-pulse'
                : state === 'THINKING'
                ? 'h-3 bg-white/70 animate-bounce'
                : 'h-2 bg-neutral-400'
            }`}
          />
          <span
            className={`w-1 rounded-full transition-all duration-300 delay-75 ${
              state === 'LISTENING'
                ? 'h-6 bg-white animate-bounce'
                : state === 'SPEAKING'
                ? 'h-4 bg-white animate-pulse'
                : state === 'THINKING'
                ? 'h-4 bg-white/70 animate-bounce'
                : 'h-2 bg-neutral-400'
            }`}
          />
          <span
            className={`w-1 rounded-full transition-all duration-300 delay-150 ${
              state === 'LISTENING'
                ? 'h-4 bg-white animate-bounce'
                : state === 'SPEAKING'
                ? 'h-5 bg-white animate-pulse'
                : state === 'THINKING'
                ? 'h-2 bg-white/70 animate-bounce'
                : 'h-2 bg-neutral-400'
            }`}
          />
        </div>
      </div>
    </div>
  );
};

