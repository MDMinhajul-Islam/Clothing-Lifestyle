import React from 'react';
import { HelpCircle, ChevronRight } from 'lucide-react';
import type { ClarificationPrompt as ClarificationType } from '../../types/voice';

interface ClarificationPromptProps {
  prompt: ClarificationType;
  onSelectOption: (option: string) => void;
}

export const ClarificationPrompt: React.FC<ClarificationPromptProps> = ({
  prompt,
  onSelectOption,
}) => {
  return (
    <div className="my-3 p-3.5 bg-neutral-50 border border-neutral-200 text-xs">
      <div className="flex items-center space-x-2 mb-2 text-neutral-800 font-medium">
        <HelpCircle className="w-3.5 h-3.5 text-neutral-500" />
        <span className="uppercase tracking-wider text-[11px] font-mono">{prompt.prompt}</span>
      </div>

      <div className="flex flex-wrap gap-1.5 pt-1">
        {prompt.options.map((option, idx) => (
          <button
            key={idx}
            onClick={() => onSelectOption(option)}
            className="flex items-center space-x-1 px-3 py-1.5 bg-white border border-neutral-200 hover:border-black text-neutral-800 text-xs transition-colors"
          >
            <span>{option}</span>
            <ChevronRight className="w-3 h-3 text-neutral-400" />
          </button>
        ))}
      </div>
    </div>
  );
};

