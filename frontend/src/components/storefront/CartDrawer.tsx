import React from 'react';
import { ShoppingBag, Trash2, X } from 'lucide-react';
import type { Product } from '../../types/catalog';

export interface CartItem {
  id: string;
  product: Product;
  size: string;
}

interface CartDrawerProps {
  isOpen: boolean;
  items: CartItem[];
  onClose: () => void;
  onRemove: (itemId: string) => void;
}

const itemPrice = (item: CartItem) => item.product.matchedVariant?.price ?? item.product.price;

export const CartDrawer: React.FC<CartDrawerProps> = ({ isOpen, items, onClose, onRemove }) => {
  const [failedImages, setFailedImages] = React.useState<string[]>([]);

  React.useEffect(() => {
    if (!isOpen) return undefined;
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', closeOnEscape);
    return () => window.removeEventListener('keydown', closeOnEscape);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const subtotal = items.reduce((total, item) => total + itemPrice(item), 0);
  const currency = items[0]?.product.currency || 'USD';

  return (
    <div className="fixed inset-0 z-[70] flex justify-end bg-black/45 backdrop-blur-sm" role="dialog" aria-modal="true" aria-label="Shopping bag">
      <button className="absolute inset-0 cursor-default" onClick={onClose} aria-label="Close shopping bag" />
      <aside className="relative flex h-full w-full max-w-md flex-col bg-[#fcfcfb] shadow-2xl">
        <header className="flex items-center justify-between border-b border-neutral-200 px-6 py-5">
          <div>
            <p className="text-[9px] font-semibold uppercase tracking-[0.22em] text-neutral-400">NexGen collection</p>
            <h2 className="mt-1 font-serif-luxury text-2xl text-neutral-950">Shopping Bag</h2>
          </div>
          <button onClick={onClose} className="rounded-full p-2 text-neutral-500 transition hover:bg-neutral-100 hover:text-black" aria-label="Close shopping bag">
            <X className="h-5 w-5" />
          </button>
        </header>

        {items.length === 0 ? (
          <div className="grid flex-1 place-items-center px-8 text-center">
            <div>
              <span className="mx-auto grid h-12 w-12 place-items-center rounded-full border border-neutral-200 bg-white"><ShoppingBag className="h-5 w-5 text-neutral-500" /></span>
              <h3 className="mt-5 font-serif-luxury text-xl">Your bag is empty</h3>
              <p className="mt-2 text-sm leading-relaxed text-neutral-500">Explore the collection and add a piece when you are ready.</p>
              <button onClick={onClose} className="mt-6 border border-black px-6 py-3 text-[10px] font-semibold uppercase tracking-[0.16em] transition hover:bg-black hover:text-white">Continue shopping</button>
            </div>
          </div>
        ) : (
          <>
            <div className="flex-1 overflow-y-auto px-5 py-2 sm:px-6">
              {items.map((item) => {
                const requestedImage = item.product.matchedVariant?.image || item.product.image;
                const fallbackImage = item.product.gallery.find((image) => image !== requestedImage && !failedImages.includes(image));
                const image = failedImages.includes(requestedImage) ? fallbackImage : requestedImage;
                return (
                  <article key={item.id} className="grid grid-cols-[5.75rem_minmax(0,1fr)_auto] gap-4 border-b border-neutral-200 py-5">
                    <div className="aspect-[3/4] overflow-hidden bg-neutral-100">
                      {image ? <img src={image} alt={item.product.name} className="h-full w-full object-contain object-center" onError={() => setFailedImages((current) => Array.from(new Set([...current, image])))} /> : <span className="grid h-full place-items-center px-2 text-center text-[8px] uppercase tracking-wider text-neutral-400">Image unavailable</span>}
                    </div>
                    <div className="min-w-0 py-1">
                      <p className="text-[9px] uppercase tracking-[0.16em] text-neutral-400">{item.product.category || 'NexGen collection'}</p>
                      <h3 className="mt-1 break-words text-sm font-medium leading-snug text-neutral-900">{item.product.name}</h3>
                      <dl className="mt-3 space-y-1 text-[11px] text-neutral-500">
                        <div className="flex gap-2"><dt>Size</dt><dd className="text-neutral-900">{item.size || 'Information unavailable'}</dd></div>
                        <div className="flex gap-2"><dt>Color</dt><dd className="text-neutral-900">{item.product.matchedVariant?.color || 'Information unavailable'}</dd></div>
                        {item.product.matchedVariant?.sku && <div className="flex gap-2"><dt>SKU</dt><dd className="break-all text-neutral-900">{item.product.matchedVariant.sku}</dd></div>}
                      </dl>
                      <p className="mt-3 font-mono text-sm text-neutral-950">${itemPrice(item).toFixed(2)} <span className="text-[9px] text-neutral-400">{item.product.currency}</span></p>
                    </div>
                    <button onClick={() => onRemove(item.id)} className="self-start rounded-full p-2 text-neutral-400 transition hover:bg-neutral-100 hover:text-red-700" aria-label={`Remove ${item.product.name} from bag`} title="Remove from bag">
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </article>
                );
              })}
            </div>
            <footer className="border-t border-neutral-200 bg-white px-6 py-5">
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-semibold uppercase tracking-[0.16em] text-neutral-500">Subtotal</span>
                <span className="font-mono text-lg text-neutral-950">${subtotal.toFixed(2)} <span className="text-[9px] text-neutral-400">{currency}</span></span>
              </div>
              <p className="mt-2 text-[10px] leading-relaxed text-neutral-400">Shipping and payment are completed during checkout.</p>
              <button onClick={onClose} className="mt-4 w-full border border-black py-3.5 text-[10px] font-semibold uppercase tracking-[0.17em] transition hover:bg-black hover:text-white">Continue shopping</button>
            </footer>
          </>
        )}
      </aside>
    </div>
  );
};
