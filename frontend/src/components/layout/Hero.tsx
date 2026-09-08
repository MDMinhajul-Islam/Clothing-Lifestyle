import React from 'react';
import { ArrowRight, CheckCircle2, Mic, PhoneCall } from 'lucide-react';
import type { Product } from '../../types/catalog';

interface HeroProps { onStartVoice: () => void; onExploreCollection: () => void; onSelectPrompt?: (prompt: string) => void; featuredProducts?: Product[] }
const prompts = ['Show me black dresses', 'Find a linen blazer', 'Check size M availability', 'Track my order'];

export const Hero: React.FC<HeroProps> = ({ onStartVoice, onExploreCollection, onSelectPrompt, featuredProducts = [] }) => {
  const [activeIndex, setActiveIndex] = React.useState(0);
  React.useEffect(() => {
    if (featuredProducts.length < 2) return;
    const timer = window.setInterval(() => setActiveIndex((index) => (index + 1) % featuredProducts.length), 4800);
    return () => window.clearInterval(timer);
  }, [featuredProducts.length]);
  const media = featuredProducts.length ? Array.from({ length: Math.min(3, featuredProducts.length) }, (_, index) => featuredProducts[(activeIndex + index) % featuredProducts.length]) : [];
  return <section className="relative overflow-hidden border-b border-neutral-200 bg-[#f2efe8] py-12 lg:min-h-[760px] lg:py-20">
    <div className="absolute -left-32 top-10 h-96 w-96 rounded-full bg-white/80 blur-3xl" />
    <div className="relative mx-auto grid max-w-[1800px] items-center gap-12 px-5 sm:px-10 lg:grid-cols-12 lg:px-16 2xl:px-24">
      <div className="space-y-8 lg:col-span-7">
        <div className="space-y-5"><h1 className="max-w-4xl font-serif-luxury text-5xl font-medium leading-[0.98] tracking-[-0.035em] text-black sm:text-7xl xl:text-8xl">Modern tailoring, <span className="italic">spoken into form.</span></h1><p className="max-w-2xl text-sm leading-7 text-neutral-700 sm:text-base">Personal styling by voice. Discover complete looks, check availability, and shop the latest collection with your NexGen personal stylist.</p></div>
        <div className="flex flex-wrap gap-3"><button onClick={onStartVoice} className="flex items-center gap-3 bg-black px-7 py-4 text-[11px] font-semibold uppercase tracking-[0.2em] text-white hover:-translate-y-0.5"><PhoneCall className="h-4 w-4 text-emerald-400" />Start live voice shopping</button><button onClick={onExploreCollection} className="flex items-center gap-2 border border-neutral-400 bg-white px-7 py-4 text-[11px] font-semibold uppercase tracking-[0.2em] hover:border-black">Browse the collection<ArrowRight className="h-4 w-4" /></button></div>
        <div className="border-t border-neutral-300 pt-5"><p className="mb-3 flex items-center gap-2 text-[10px] uppercase tracking-[0.18em] text-neutral-600"><Mic className="h-3.5 w-3.5 text-emerald-700" />Ask your stylist</p><div className="flex flex-wrap gap-2">{prompts.map((prompt) => <button key={prompt} onClick={() => onSelectPrompt?.(prompt)} className="border border-neutral-300 bg-white px-3 py-2 text-xs italic text-neutral-800 hover:border-black">“{prompt}”</button>)}</div></div>
        <div className="grid gap-3 text-[10px] uppercase tracking-[0.13em] text-neutral-600 sm:grid-cols-3">{['Personal styling by voice', 'Live availability', 'Complete-look curation'].map((item) => <div key={item} className="flex items-center gap-2"><CheckCircle2 className="h-3.5 w-3.5 text-emerald-700" />{item}</div>)}</div>
      </div>
      <div className="relative mx-auto w-full max-w-2xl lg:col-span-5 [perspective:1400px]"><div className="relative aspect-[5/6]">{media.map((product, index) => <button key={`${product.id}-${activeIndex}`} onClick={onExploreCollection} className={`cinematic-card absolute overflow-hidden bg-neutral-200 shadow-2xl transition duration-700 hover:z-20 hover:scale-[1.03] ${index === 0 ? 'inset-y-0 left-[12%] w-[66%]' : index === 1 ? 'right-0 top-[8%] h-[43%] w-[31%] rotate-3' : 'bottom-[4%] left-0 h-[38%] w-[32%] -rotate-3'}`}><img src={product.modelWalkUrl || product.videoUrl || product.image} alt={product.name} className="h-full w-full object-cover object-top" loading={index ? 'lazy' : 'eager'} /><span className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/75 to-transparent p-3 pt-12 text-left text-[9px] uppercase tracking-wider text-white">{product.name}</span></button>)}<div className="absolute bottom-[7%] right-[4%] z-30 w-[72%] bg-black/90 p-4 text-white shadow-2xl backdrop-blur-md"><p className="text-[10px] uppercase tracking-[0.18em] text-emerald-400">Live AI Shopping Assistant</p><p className="mt-3 font-serif-luxury text-base italic">“Tell me the occasion, color, or silhouette you have in mind.”</p></div></div></div>
    </div>
  </section>;
};
