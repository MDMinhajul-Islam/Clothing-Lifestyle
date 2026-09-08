import React from 'react';
import { AlertCircle, ArrowRight, Loader2, RefreshCw, Sparkles } from 'lucide-react';
import type { Product } from '../../types/catalog';
import { ProductCard } from './ProductCard';

interface ProductGridProps {
  products: Product[]; isLoading?: boolean; error?: string | null;
  onSelectProduct: (product: Product) => void; onAskAboutProduct?: (product: Product) => void;
  onResetFilters: () => void; onAskVoice: (prompt: string) => void;
  voiceActionNotice?: { actionText: string; route?: string; onClear: () => void } | null;
  totalMatchingCount?: number; onLoadMore?: () => void; hasMore?: boolean; isLoadingMore?: boolean;
}

export const ProductGrid: React.FC<ProductGridProps> = React.memo(({ products, isLoading, error, onSelectProduct, onAskAboutProduct, onResetFilters, onAskVoice, voiceActionNotice, totalMatchingCount = products.length, onLoadMore, hasMore = false, isLoadingMore = false }) => {
  if (isLoading) return <div className="mx-auto max-w-[1600px] px-4 py-12 sm:px-8 lg:px-12 2xl:px-16"><div className="grid grid-cols-2 gap-6 md:grid-cols-3 lg:grid-cols-4 2xl:grid-cols-5">{Array.from({ length: 10 }, (_, index) => <div key={index} className="space-y-3"><div className="aspect-[3/4] animate-shimmer bg-neutral-200" /><div className="h-3 w-3/4 bg-neutral-200" /><div className="h-3 w-1/4 bg-neutral-200" /></div>)}</div></div>;
  if (error) return <div className="mx-auto max-w-xl px-4 py-24 text-center"><AlertCircle className="mx-auto mb-4 h-8 w-8 text-neutral-400" /><h2 className="font-serif-luxury text-xl">Unable to load the collection</h2><p className="my-4 text-xs text-neutral-500">{error}</p><button onClick={onResetFilters} className="inline-flex items-center gap-2 bg-black px-5 py-3 text-[10px] uppercase tracking-widest text-white"><RefreshCw className="h-3.5 w-3.5" />Reset filters</button></div>;
  if (!products.length) return <div className="mx-auto max-w-xl px-4 py-24 text-center"><Sparkles className="mx-auto mb-4 h-7 w-7 text-neutral-400" /><p className="mb-3 text-[10px] uppercase tracking-widest text-neutral-400">0 products</p><h2 className="font-serif-luxury text-2xl">No matching pieces found</h2><p className="my-4 text-sm text-neutral-500">Try clearing a filter or ask the Live AI Shopping Assistant to broaden the search.</p><div className="flex justify-center gap-3"><button onClick={onResetFilters} className="border border-neutral-300 px-5 py-3 text-[10px] uppercase tracking-widest">Clear filters</button><button onClick={() => onAskVoice('Show me new arrivals')} className="bg-black px-5 py-3 text-[10px] uppercase tracking-widest text-white">Ask the stylist</button></div></div>;

  return (
    <section className="mx-auto max-w-[1600px] px-4 py-9 sm:px-8 lg:px-12 2xl:px-16">
      {voiceActionNotice && <div className="mb-8 flex flex-col gap-3 border border-neutral-800 bg-neutral-950 p-4 text-white sm:flex-row sm:items-center sm:justify-between"><div className="flex items-center gap-3"><span className="h-3 w-3 animate-pulse rounded-full bg-emerald-400" /><div><span className="text-[9px] font-semibold uppercase tracking-[0.18em] text-emerald-400">AI-curated results</span><p className="mt-1 text-sm italic">{voiceActionNotice.actionText}</p></div></div><button onClick={voiceActionNotice.onClear} className="text-left text-[10px] uppercase tracking-widest text-neutral-300 underline">Clear voice selection</button></div>}
      <div className="mb-6 flex items-end justify-between"><div><span className="text-[10px] uppercase tracking-[0.2em] text-neutral-400">Browse the collection</span><h2 className="mt-1 font-serif-luxury text-2xl text-neutral-950">Curated now</h2></div><p className="text-right text-[10px] uppercase tracking-wider text-neutral-400">{products.length} shown{totalMatchingCount > products.length && <><br />{totalMatchingCount.toLocaleString()} matching</>}</p></div>
      <div className="grid grid-cols-2 gap-x-4 gap-y-10 md:grid-cols-3 lg:grid-cols-4 xl:gap-x-7 2xl:grid-cols-5">{products.map((product) => <ProductCard key={product.id} product={product} onSelect={onSelectProduct} onAskAboutProduct={onAskAboutProduct} />)}</div>
      <div className="mt-14 flex flex-col items-center gap-3 border-t border-neutral-200 pt-8">{hasMore ? <button onClick={onLoadMore} disabled={isLoadingMore} className="flex items-center gap-2 bg-black px-8 py-3.5 text-[10px] font-semibold uppercase tracking-[0.2em] text-white disabled:opacity-50">{isLoadingMore ? <Loader2 className="h-4 w-4 animate-spin" /> : <ArrowRight className="h-4 w-4" />}{isLoadingMore ? 'Loading pieces' : 'Load more styles'}</button> : <p className="text-[10px] uppercase tracking-widest text-neutral-400">You have reached the end of these results</p>}</div>
    </section>
  );
});
