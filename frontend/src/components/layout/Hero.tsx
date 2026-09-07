import React from 'react';
import { ArrowRight, CheckCircle2, Mic, PhoneCall } from 'lucide-react';

interface HeroProps {
  onStartVoice: () => void;
  onExploreCollection: () => void;
  onSelectPrompt?: (prompt: string) => void;
}

const prompts = [
  'Show me black dresses for an evening event',
  'What matches with a linen blazer?',
  'Check availability for size M',
  'Track my order',
];

export const Hero: React.FC<HeroProps> = ({ onStartVoice, onExploreCollection, onSelectPrompt }) => (
  <section className="overflow-hidden border-b border-neutral-200/70 bg-gradient-to-b from-[#f4f1eb] via-[#faf9f6] to-white py-12 lg:py-20">
    <div className="mx-auto grid max-w-[1600px] grid-cols-1 items-center gap-12 px-4 sm:px-8 lg:grid-cols-12 lg:px-12 2xl:px-16">
      <div className="space-y-7 lg:col-span-7">
        <div className="inline-flex items-center gap-2 rounded-full border border-neutral-200 bg-white/80 px-3.5 py-1.5 text-[10px] font-medium uppercase tracking-[0.2em] text-neutral-700">
          <span className="h-2 w-2 animate-pulse rounded-full bg-emerald-500" />
          NexGen AI Fashion & Voice Commerce
        </div>
        <div className="space-y-4">
          <h1 className="max-w-4xl font-serif-luxury text-5xl font-light leading-[1.02] tracking-tight text-neutral-950 sm:text-6xl xl:text-8xl">
            Modern tailoring, <span className="italic">spoken into form.</span>
          </h1>
          <p className="max-w-2xl text-sm leading-relaxed text-neutral-600 sm:text-base">
            Personal styling by voice. Browse the collection, discover complete looks, check availability, and track orders through a live AI shopping experience.
          </p>
        </div>
        <div className="flex flex-wrap gap-3">
          <button onClick={onStartVoice} className="flex items-center gap-3 bg-black px-7 py-4 text-[11px] font-semibold uppercase tracking-[0.2em] text-white transition-transform hover:-translate-y-0.5">
            <PhoneCall className="h-4 w-4 text-emerald-400" /> Start live voice shopping
          </button>
          <button onClick={onExploreCollection} className="flex items-center gap-2 border border-neutral-300 bg-white px-7 py-4 text-[11px] font-semibold uppercase tracking-[0.2em] text-neutral-900 hover:border-black">
            Browse the collection <ArrowRight className="h-4 w-4" />
          </button>
        </div>
        <div className="border-t border-neutral-200 pt-5">
          <div className="mb-3 flex items-center gap-2 text-[10px] uppercase tracking-[0.18em] text-neutral-500">
            <Mic className="h-3.5 w-3.5 text-emerald-600" /> Try a voice request
          </div>
          <div className="flex flex-wrap gap-2">
            {prompts.map((prompt) => (
              <button key={prompt} onClick={() => onSelectPrompt ? onSelectPrompt(prompt) : onStartVoice()} className="border border-neutral-200 bg-white px-3 py-2 text-left text-xs italic text-neutral-700 hover:border-black">
                “{prompt}”
              </button>
            ))}
          </div>
        </div>
        <div className="grid grid-cols-1 gap-3 text-[10px] uppercase tracking-[0.13em] text-neutral-500 sm:grid-cols-3">
          {['Personal styling by voice', 'Availability checks', 'Complete-look curation'].map((item) => (
            <div key={item} className="flex items-center gap-2"><CheckCircle2 className="h-3.5 w-3.5 text-emerald-600" />{item}</div>
          ))}
        </div>
      </div>

      <div className="relative mx-auto w-full max-w-lg lg:col-span-5">
        <div className="relative aspect-[3/4] overflow-hidden bg-neutral-200 shadow-2xl">
          <img src="https://static.zara.net/assets/public/c3e1/96d8/59d548568418/4e180af2076e/03152205485-p/03152205485-p.jpg?ts=1783689777150&w=1920" alt="Editorial tailored fashion" className="h-full w-full object-cover object-top" />
          <div className="absolute inset-0 bg-gradient-to-t from-black/65 via-transparent to-transparent" />
          <div className="absolute inset-x-5 bottom-5 border border-white/20 bg-black/80 p-4 text-white backdrop-blur-md">
            <div className="mb-3 flex items-center justify-between text-[10px] uppercase tracking-[0.18em]">
              <span className="flex items-center gap-2 text-emerald-400"><span className="h-2 w-2 animate-pulse rounded-full bg-emerald-400" />Live AI shopping assistant</span>
              <span className="text-neutral-400">Connected</span>
            </div>
            <p className="font-serif-luxury text-base italic leading-snug">“Tell me the occasion, color, or silhouette you have in mind.”</p>
            <div className="mt-4 flex h-6 items-center gap-1 border-t border-white/10 pt-3">
              {[3, 5, 2, 6, 4, 7, 3, 5, 2, 4].map((height, index) => <span key={index} className="w-1 animate-pulse bg-emerald-400" style={{ height: `${height * 2}px` }} />)}
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>
);
