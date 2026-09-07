import React from 'react';
import { Sparkles, RefreshCw, AlertCircle } from 'lucide-react';
import type { Product } from '../../types/catalog';
import { ProductCard } from './ProductCard';

interface ProductGridProps {
  products: Product[];
  isLoading?: boolean;
  error?: string | null;
  onSelectProduct: (product: Product) => void;
  onAskAboutProduct?: (product: Product) => void;
  onResetFilters: () => void;
  onAskVoice: (prompt: string) => void;
}

export const ProductGrid: React.FC<ProductGridProps> = ({
  products,
  isLoading,
  error,
  onSelectProduct,
  onAskAboutProduct,
  onResetFilters,
  onAskVoice,
}) => {
  // Loading State
  if (isLoading) {
    return (
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-12">
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
          {Array.from({ length: 8 }).map((_, i) => (
            <div key={i} className="flex flex-col space-y-3">
              <div className="aspect-[3/4] w-full animate-shimmer bg-neutral-200" />
              <div className="h-3 w-3/4 bg-neutral-200" />
              <div className="h-3 w-1/4 bg-neutral-200" />
            </div>
          ))}
        </div>
      </div>
    );
  }

  // Error State
  if (error) {
    return (
      <div className="mx-auto max-w-2xl px-4 py-20 text-center">
        <AlertCircle className="mx-auto h-8 w-8 text-neutral-400 mb-3" />
        <h3 className="text-lg font-serif-luxury text-neutral-900 mb-2">Unable to Load Collection</h3>
        <p className="text-xs text-neutral-500 mb-6 font-mono">{error}</p>
        <button
          onClick={onResetFilters}
          className="inline-flex items-center space-x-2 px-5 py-2.5 bg-black text-white text-xs uppercase tracking-widest font-medium hover:bg-neutral-800 transition-colors"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          <span>Reset Filters</span>
        </button>
      </div>
    );
  }

  // Empty State
  if (products.length === 0) {
    return (
      <div className="mx-auto max-w-xl px-4 py-24 text-center">
        <div className="w-12 h-12 mx-auto rounded-full bg-neutral-100 flex items-center justify-center mb-4 border border-neutral-200">
          <Sparkles className="w-5 h-5 text-neutral-400" />
        </div>
        <h3 className="text-xl font-serif-luxury text-neutral-900 mb-2">
          No matching garments found
        </h3>
        <p className="text-xs text-neutral-500 leading-relaxed mb-6">
          We couldn’t find pieces matching your specific filter combination. Try clearing your filters or speak directly with NexGen Voice to find what you need.
        </p>

        <div className="flex flex-wrap items-center justify-center gap-3">
          <button
            onClick={onResetFilters}
            className="px-4 py-2 border border-neutral-300 text-neutral-800 text-xs uppercase tracking-widest hover:border-black transition-colors"
          >
            Clear Filters
          </button>
          <button
            onClick={() => onAskVoice('Show me popular new arrivals')}
            className="px-4 py-2 bg-black text-white text-xs uppercase tracking-widest hover:bg-neutral-800 transition-colors"
          >
            Ask Voice AI for New Arrivals
          </button>
        </div>
      </div>
    );
  }

  // Main Products Grid
  return (
    <section className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-8">
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-x-4 gap-y-10 sm:gap-x-6">
        {products.map((product) => (
          <ProductCard
            key={product.id}
            product={product}
            onSelect={onSelectProduct}
            onAskAboutProduct={onAskAboutProduct}
          />
        ))}
      </div>
    </section>
  );
};
