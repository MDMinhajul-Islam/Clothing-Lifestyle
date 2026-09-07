import React from 'react';
import { Eye, Mic } from 'lucide-react';
import type { Product } from '../../types/catalog';

interface ProductCardProps {
  product: Product;
  onSelect: (product: Product) => void;
  onAskAboutProduct?: (product: Product) => void;
}

export const ProductCard: React.FC<ProductCardProps> = ({
  product,
  onSelect,
  onAskAboutProduct,
}) => {
  const [imageLoaded, setImageLoaded] = React.useState(false);

  return (
    <div className="group relative flex flex-col bg-white transition-all">
      {/* Image Frame */}
      <div 
        onClick={() => onSelect(product)}
        className="relative aspect-[3/4] w-full overflow-hidden bg-neutral-100 cursor-pointer"
      >
        {!imageLoaded && (
          <div className="absolute inset-0 animate-shimmer" />
        )}

        <img
          src={product.image}
          alt={product.name}
          loading="lazy"
          onLoad={() => setImageLoaded(true)}
          className={`h-full w-full object-cover object-top transition-transform duration-700 ease-out group-hover:scale-105 ${
            imageLoaded ? 'opacity-100' : 'opacity-0'
          }`}
        />

        {/* Badges */}
        <div className="absolute top-2.5 left-2.5 flex flex-col gap-1 z-10 pointer-events-none">
          {product.isNew && (
            <span className="bg-black text-white text-[9px] uppercase tracking-widest px-2 py-0.5 font-mono">
              New
            </span>
          )}
          {product.isSale && (
            <span className="bg-rose-950 text-white text-[9px] uppercase tracking-widest px-2 py-0.5 font-mono">
              Sale
            </span>
          )}
        </div>

        {/* Hover Quick Actions Overlay */}
        <div className="absolute inset-x-0 bottom-0 p-3 bg-gradient-to-t from-black/70 via-black/30 to-transparent opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-between gap-2">
          <button
            onClick={(e) => {
              e.stopPropagation();
              onSelect(product);
            }}
            className="flex-1 py-2 bg-white/90 hover:bg-white text-black text-[10px] tracking-widest uppercase font-medium flex items-center justify-center space-x-1 transition-colors"
          >
            <Eye className="w-3 h-3" />
            <span>View Details</span>
          </button>

          {onAskAboutProduct && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                onAskAboutProduct(product);
              }}
              className="p-2 bg-black/80 hover:bg-black text-white rounded-none transition-colors"
              title="Ask NexGen Voice about this piece"
            >
              <Mic className="w-3.5 h-3.5 text-emerald-400" />
            </button>
          )}
        </div>
      </div>

      {/* Product Meta */}
      <div className="pt-3 pb-2 flex flex-col flex-1">
        {/* Color Palette Indicators */}
        {product.colors.length > 0 && (
          <div className="flex items-center space-x-1.5 mb-1.5">
            {product.colors.map((c, i) => (
              <span
                key={i}
                className="w-2.5 h-2.5 rounded-full border border-neutral-300 inline-block"
                style={{ backgroundColor: c.hex }}
                title={c.name}
              />
            ))}
            <span className="text-[10px] text-neutral-400 font-mono">
              {product.colors[0].name}
            </span>
          </div>
        )}

        {/* Name */}
        <h3 
          onClick={() => onSelect(product)}
          className="text-xs uppercase tracking-wider text-neutral-900 font-medium line-clamp-1 hover:underline cursor-pointer"
        >
          {product.name}
        </h3>

        {/* Price & Currency */}
        <div className="mt-1 flex items-baseline space-x-2 font-mono text-xs">
          <span className="text-neutral-900 font-semibold">
            ${product.price.toFixed(2)}
          </span>
          {product.originalPrice && (
            <span className="text-neutral-400 line-through text-[11px]">
              ${product.originalPrice.toFixed(2)}
            </span>
          )}
          <span className="text-[10px] text-neutral-400 uppercase font-sans">
            {product.currency}
          </span>
        </div>

        {/* Available sizes */}
        <div className="mt-2 pt-2 border-t border-neutral-100 flex items-center justify-between text-[10px] text-neutral-400 font-mono">
          <span>Sizes: {product.sizes.slice(0, 4).join(' · ')}</span>
          <span className="text-[9px] text-neutral-300">CDN Verified</span>
        </div>
      </div>
    </div>
  );
};
