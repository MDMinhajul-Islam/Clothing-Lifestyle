import { ArrowUpRight, Sparkles } from 'lucide-react';
import type { Product } from '../../types/catalog';

interface StyledEditProps { products: Product[]; onSelectProduct: (product: Product) => void; onAskVoice: (prompt: string) => void }

export const StyledEdit = ({ products, onSelectProduct, onAskVoice }: StyledEditProps) => {
  const edit = products.slice(0, 4);
  if (edit.length < 3) return null;
  return (
    <section id="styled-edit" className="overflow-hidden bg-[#171714] py-16 text-white lg:py-24">
      <div className="mx-auto max-w-[1700px] px-4 sm:px-8 lg:px-12 2xl:px-16">
        <div className="mb-10 flex flex-col gap-5 sm:flex-row sm:items-end sm:justify-between"><div><p className="flex items-center gap-2 text-[10px] uppercase tracking-[0.22em] text-emerald-400"><Sparkles className="h-3.5 w-3.5" />Selected for the season</p><h2 className="mt-3 font-serif-luxury text-4xl font-light sm:text-6xl">New arrivals</h2></div><button onClick={() => onAskVoice('Style a complete look for me')} className="self-start border-b border-white/50 pb-1 text-[10px] uppercase tracking-[0.18em] hover:border-emerald-400 hover:text-emerald-400">Style this by voice</button></div>
        <div className="grid grid-cols-2 gap-3 md:grid-cols-12 md:gap-5 [perspective:1400px]">
          {edit.map((product, index) => <button key={product.id} onClick={() => onSelectProduct(product)} className={`group relative overflow-hidden text-left ${index === 0 ? 'col-span-2 md:col-span-5 md:row-span-2' : index === 1 ? 'md:col-span-4' : 'md:col-span-3'}`}>
            <div className={`overflow-hidden bg-neutral-800 ${index === 0 ? 'aspect-[4/5]' : 'aspect-[3/4]'}`}><img src={product.image} alt={product.name} className="h-full w-full object-cover object-top transition duration-700 ease-out group-hover:scale-105 group-hover:[transform:scale(1.05)_rotateY(-2deg)]" /></div>
            <div className="absolute inset-0 bg-gradient-to-t from-black/75 via-transparent to-transparent" />
            <div className="absolute inset-x-0 bottom-0 flex items-end justify-between p-4 sm:p-6"><div><span className="text-[9px] uppercase tracking-[0.18em] text-neutral-300">Look {String(index + 1).padStart(2, '0')}</span><h3 className="mt-1 max-w-xs font-serif-luxury text-lg leading-tight sm:text-2xl">{product.name}</h3><p className="mt-1 font-mono text-xs text-neutral-300">${product.price.toFixed(2)}</p></div><ArrowUpRight className="h-5 w-5 transition-transform group-hover:-translate-y-1 group-hover:translate-x-1" /></div>
          </button>)}
        </div>
      </div>
    </section>
  );
};
