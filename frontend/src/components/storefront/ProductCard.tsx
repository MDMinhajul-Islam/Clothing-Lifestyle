import React from 'react';
import { Eye, Mic } from 'lucide-react';
import type { Product } from '../../types/catalog';

interface ProductCardProps { product: Product; onSelect: (product: Product) => void; onAskAboutProduct?: (product: Product) => void; }

export const ProductCard: React.FC<ProductCardProps> = ({ product, onSelect, onAskAboutProduct }) => {
  const [loaded, setLoaded] = React.useState(false);
  const [imageFailed, setImageFailed] = React.useState(false);
  return (
    <article className="group flex flex-col bg-white">
      <button onClick={() => onSelect(product)} className="relative aspect-[3/4] overflow-hidden bg-neutral-100 text-left" aria-label={`View ${product.name}`}>
        {!loaded && <span className="absolute inset-0 animate-shimmer bg-neutral-200" />}
        {product.image && !imageFailed ? <img src={product.image} alt={product.name} loading="lazy" onLoad={() => setLoaded(true)} onError={() => { setLoaded(true); setImageFailed(true); }} className={`h-full w-full object-cover object-top transition duration-700 group-hover:scale-105 ${loaded ? 'opacity-100' : 'opacity-0'}`} /> : <span className="absolute inset-0 grid place-items-center text-[10px] uppercase tracking-widest text-neutral-400">Image unavailable</span>}
        <span className="absolute left-3 top-3 flex flex-col gap-1">{product.isNew && <span className="bg-black px-2 py-1 text-[9px] uppercase tracking-widest text-white">New</span>}{product.isSale && <span className="bg-rose-950 px-2 py-1 text-[9px] uppercase tracking-widest text-white">Sale</span>}</span>
        <span className="absolute inset-x-3 bottom-3 flex translate-y-2 gap-2 opacity-0 transition group-hover:translate-y-0 group-hover:opacity-100">
          <span className="flex flex-1 items-center justify-center gap-1.5 bg-white px-3 py-2 text-[10px] font-semibold uppercase tracking-widest text-black"><Eye className="h-3 w-3" />View piece</span>
          {onAskAboutProduct && <span role="button" tabIndex={0} onClick={(event) => { event.stopPropagation(); onAskAboutProduct(product); }} className="grid place-items-center bg-black p-2.5 text-emerald-400" aria-label={`Ask stylist about ${product.name}`}><Mic className="h-3.5 w-3.5" /></span>}
        </span>
      </button>
      <div className="flex flex-1 flex-col py-3">
        <div className="mb-2 flex min-h-3 items-center gap-1.5">{product.colors.slice(0, 4).map((color) => <span key={color.name} className="h-2.5 w-2.5 rounded-full border border-neutral-300" style={{ backgroundColor: color.hex }} title={color.name} />)}<span className="ml-1 text-[9px] uppercase tracking-wider text-neutral-400">{product.colors[0]?.name || 'Color unavailable'}</span></div>
        <button onClick={() => onSelect(product)} className="line-clamp-1 text-left text-xs font-semibold uppercase tracking-[0.1em] text-neutral-900 hover:text-neutral-600">{product.name}</button>
        <div className="mt-1.5 flex items-baseline gap-2 font-mono text-xs"><span>${product.price.toFixed(2)}</span>{product.originalPrice && <span className="text-neutral-400 line-through">${product.originalPrice.toFixed(2)}</span>}<span className="text-[9px] text-neutral-400">{product.currency}</span></div>
        <div className="mt-2 flex items-center justify-between border-t border-neutral-100 pt-2 text-[9px] uppercase tracking-wider text-neutral-400"><span>{product.sizes.slice(0, 4).join(' · ') || 'Sizes unavailable'}</span><span className={product.inStock ? 'text-emerald-700' : 'text-neutral-400'}>{product.inStock ? 'Available' : 'Unavailable'}</span></div>
      </div>
    </article>
  );
};
