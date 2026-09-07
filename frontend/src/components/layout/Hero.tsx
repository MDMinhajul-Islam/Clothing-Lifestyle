import React from 'react';
import { Mic, Sparkles, ArrowRight } from 'lucide-react';

interface HeroProps {
  onStartVoice: () => void;
  onExploreCollection: () => void;
}

export const Hero: React.FC<HeroProps> = ({ onStartVoice, onExploreCollection }) => {
  return (
    <section className="relative overflow-hidden bg-gradient-to-b from-[#f7f6f4] via-[#fbfbfb] to-[#fbfbfb] pt-8 pb-16 border-b border-neutral-200/60">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 items-center">
          {/* Left Editorial Copy */}
          <div className="lg:col-span-7 space-y-6">
            <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-neutral-100 border border-neutral-200/80 text-[11px] font-mono uppercase tracking-widest text-neutral-700">
              <Sparkles className="w-3 h-3 text-neutral-900" />
              <span>Autumn / Winter Collection — Voice Interactive</span>
            </div>

            <h1 className="text-4xl sm:text-6xl lg:text-7xl font-light tracking-tight text-neutral-900 font-serif-luxury leading-[1.05]">
              Modern tailoring <br />
              <span className="italic font-normal">spoken into form.</span>
            </h1>

            <p className="max-w-xl text-sm sm:text-base text-neutral-600 font-light leading-relaxed">
              Experience the next frontier of fashion commerce. Browse 6,000+ curated styles, check real-time boutique stock, receive bespoke pairing advice, and resolve orders simply by talking.
            </p>

            {/* CTA Buttons */}
            <div className="flex flex-wrap items-center gap-4 pt-2">
              <button
                onClick={onStartVoice}
                className="group flex items-center space-x-3 px-6 py-3.5 bg-black text-white text-xs uppercase tracking-[0.2em] font-medium rounded-none hover:bg-neutral-800 transition-all shadow-md shadow-black/5"
              >
                <Mic className="w-4 h-4 text-emerald-400 group-hover:scale-110 transition-transform" />
                <span>Start Voice Shopping</span>
              </button>

              <button
                onClick={onExploreCollection}
                className="group flex items-center space-x-2 px-6 py-3.5 border border-neutral-300 text-neutral-800 text-xs uppercase tracking-[0.2em] font-medium rounded-none hover:border-black hover:bg-white transition-all"
              >
                <span>Browse Catalog</span>
                <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-1 transition-transform" />
              </button>
            </div>

            {/* Quick voice inspiration pills */}
            <div className="pt-4 border-t border-neutral-200/60">
              <span className="text-[11px] uppercase tracking-wider text-neutral-500 font-mono block mb-2">
                Try saying:
              </span>
              <div className="flex flex-wrap gap-2 text-xs text-neutral-700">
                <span className="px-2.5 py-1 bg-white border border-neutral-200/80 rounded-sm italic">
                  “Show me black dresses under $100”
                </span>
                <span className="px-2.5 py-1 bg-white border border-neutral-200/80 rounded-sm italic">
                  “What matches with the linen blazer?”
                </span>
                <span className="px-2.5 py-1 bg-white border border-neutral-200/80 rounded-sm italic">
                  “Where is my order #ZUS-2025-00001?”
                </span>
              </div>
            </div>
          </div>

          {/* Right Editorial Imagery / Voice Visualizer Feature */}
          <div className="lg:col-span-5 relative">
            <div className="relative aspect-[3/4] max-w-md mx-auto overflow-hidden bg-neutral-200 shadow-2xl border border-neutral-200">
              <img
                src="https://static.zara.net/assets/public/c3e1/96d8/59d548568418/4e180af2076e/03152205485-p/03152205485-p.jpg?ts=1783689777150&w=1920"
                alt="NexGen Editorial Showcase"
                className="w-full h-full object-cover object-top hover:scale-105 transition-transform duration-700"
              />
              <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent"></div>

              {/* Floating Voice HUD Card */}
              <div className="absolute bottom-4 left-4 right-4 p-4 glass-dark text-white text-xs rounded-none border border-white/20">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center space-x-2">
                    <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse"></span>
                    <span className="text-[10px] tracking-widest uppercase font-mono text-neutral-300">
                      Live Voice AI Mode
                    </span>
                  </div>
                  <span className="text-[10px] font-mono text-neutral-400">98.4% Accuracy</span>
                </div>
                <p className="font-serif-luxury text-sm italic text-neutral-100">
                  “I found 12 dresses with tailored draping. Showing the Ruched Halter Dress now.”
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};

