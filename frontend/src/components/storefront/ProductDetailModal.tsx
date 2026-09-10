import React from 'react';
import { Check, ChevronRight, Loader2, MapPin, Mic, Sparkles, X } from 'lucide-react';
import type { Product } from '../../types/catalog';
import { resolveProductImage } from '../../lib/catalogueApi';

interface ProductDetailModalProps {
  product: Product | null;
  isLoading?: boolean;
  error?: string | null;
  onClose: () => void;
  onAddToCart: (product: Product, size: string) => void;
  onAskVoicePrompt: (prompt: string, product: Product) => void;
  matchingProducts: Product[];
  onSelectMatchingProduct: (product: Product) => void;
  onContextChange?: (product: Product) => void;
}

export const ProductDetailModal: React.FC<ProductDetailModalProps> = ({ product, isLoading = false, error, onClose, onAddToCart, onAskVoicePrompt, matchingProducts, onSelectMatchingProduct, onContextChange }) => {
  const [sizeSelection, setSizeSelection] = React.useState<{ productId: string; value: string } | null>(null);
  const [imageSelection, setImageSelection] = React.useState<{ productId: string; value: string } | null>(null);
  const [addedProductId, setAddedProductId] = React.useState<string | null>(null);
  const [failedImages, setFailedImages] = React.useState<{ productId: string; values: string[] } | null>(null);

  if (!product) return null;
  const selectedSize = sizeSelection?.productId === product.id ? sizeSelection.value : product.matchedVariant?.size || product.sizes[0] || 'One size';
  const unavailableImages = failedImages?.productId === product.id ? failedImages.values : [];
  const requestedImage = imageSelection?.productId === product.id ? imageSelection.value : product.image;
  const selectedImage = resolveProductImage(product, requestedImage, unavailableImages);
  const isAdded = addedProductId === product.id;
  const purchasable = product.inStock;
  const addToBag = () => {
    onAddToCart(product, selectedSize || product.sizes[0] || 'M');
    setAddedProductId(product.id);
    window.setTimeout(() => setAddedProductId(null), 1800);
  };

  return (
    <div className="fixed inset-0 z-50 flex justify-end overflow-y-auto bg-black/60 backdrop-blur-sm" role="dialog" aria-modal="true" aria-label={product.name}>
      <button className="fixed inset-0 cursor-default" onClick={onClose} aria-label="Close product details" />
      <article className="relative z-10 min-h-screen w-full max-w-6xl overflow-x-hidden overflow-y-auto border-l border-neutral-200 bg-white shadow-2xl">
        <header className="sticky top-0 z-20 flex items-center justify-between border-b border-neutral-200 bg-white/95 px-6 py-4 backdrop-blur-md">
          <div className="min-w-0 truncate pr-4 text-[10px] uppercase tracking-[0.18em] text-neutral-500"><span>NexGen collection</span><span className="mx-2 text-neutral-300">/</span><span>Ref. {product.commercialReference || product.id}</span></div>
          <button onClick={onClose} className="shrink-0 rounded-full p-2 text-neutral-500 hover:bg-neutral-100 hover:text-black" aria-label="Close"><X className="h-5 w-5" /></button>
        </header>

        <div className="grid min-w-0 gap-8 px-5 py-6 sm:px-8 sm:py-8 lg:grid-cols-[minmax(0,1.15fr)_minmax(19rem,0.85fr)] lg:gap-10 lg:px-10 xl:px-14">
          <div className="min-w-0">
            <div className="relative aspect-[3/4] overflow-hidden bg-neutral-100 p-3">{selectedImage ? <img src={selectedImage} alt={product.name} onError={() => setFailedImages((current) => ({ productId: product.id, values: Array.from(new Set([...(current?.productId === product.id ? current.values : []), selectedImage])) }))} className="h-full w-full object-contain object-center" /> : <span className="absolute inset-0 grid place-items-center px-6 text-center text-[10px] uppercase tracking-widest text-neutral-400">Product imagery is unavailable. Details and availability remain current.</span>}{isLoading && <span className="absolute inset-0 grid place-items-center bg-white/70"><Loader2 className="h-5 w-5 animate-spin" /></span>}</div>
            {product.gallery.filter((image) => !unavailableImages.includes(image)).length > 1 && <div className="mt-3 flex gap-2 overflow-x-auto">{product.gallery.filter((image) => !unavailableImages.includes(image)).map((image) => <button key={image} onClick={() => setImageSelection({ productId: product.id, value: image })} className={`w-16 shrink-0 overflow-hidden border bg-neutral-50 ${selectedImage === image ? 'border-black' : 'border-neutral-200 opacity-70'}`}><img src={image} alt="" onError={() => setFailedImages((current) => ({ productId: product.id, values: Array.from(new Set([...(current?.productId === product.id ? current.values : []), image])) }))} className="aspect-[3/4] h-full w-full object-contain object-center" /></button>)}</div>}
          </div>

          <div className="min-w-0 space-y-7 lg:pr-1">
            <div><p className="break-words text-[10px] uppercase tracking-[0.2em] text-neutral-400">{product.department || 'Information unavailable'} / {product.category || 'Information unavailable'}</p><h2 className="mt-2 break-words font-serif-luxury text-3xl leading-tight text-neutral-950">{product.name || 'Information unavailable'}</h2><p className="mt-3 font-mono text-lg">${product.price.toFixed(2)} <span className="text-xs text-neutral-400">{product.currency}</span></p><p className="mt-5 break-words text-sm leading-relaxed text-neutral-600">{product.longDescription || product.description || 'Information unavailable'}</p>{error && <p className="mt-3 text-xs text-amber-800">{error}</p>}</div>
            <div className="border border-neutral-200 bg-neutral-50 p-4">
              <div className="mb-3 flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[0.16em]"><Mic className="h-3.5 w-3.5 text-emerald-600" />Ask the Stylist</div>
              <div className="space-y-2"><VoiceShortcut label="Ask about size" icon={<ChevronRight className="h-3.5 w-3.5" />} onClick={() => onAskVoicePrompt('What size should I choose for this?', product)} /><VoiceShortcut label="Check availability" icon={<MapPin className="h-3.5 w-3.5" />} onClick={() => onAskVoicePrompt('Check availability for this', product)} /><VoiceShortcut label="Find a complete look" icon={<Sparkles className="h-3.5 w-3.5" />} onClick={() => onAskVoicePrompt('What matches with this?', product)} /></div>
            </div>
            <div><div className="mb-3 flex justify-between text-[10px] uppercase tracking-[0.15em]"><span>Available sizes</span><span>{product.sizes.length ? selectedSize : 'Information unavailable'}</span></div>{product.sizes.length ? <div className="grid grid-cols-4 gap-2">{product.sizes.map((size) => <button key={size} onClick={() => { setSizeSelection({ productId: product.id, value: size }); onContextChange?.({ ...product, matchedVariant: product.matchedVariant ? { ...product.matchedVariant, size } : undefined }); }} className={`border py-2.5 text-xs ${selectedSize === size ? 'border-black bg-black text-white' : 'border-neutral-200 hover:border-black'}`}>{size}</button>)}</div> : <p className="text-xs text-neutral-500">Information unavailable</p>}</div>
            <div><h3 className="mb-3 text-[10px] uppercase tracking-[0.15em]">Available colors</h3>{product.colors.length ? <div className="flex flex-wrap gap-2">{product.colors.map((color) => <span key={color.name} className={`inline-flex items-center gap-2 border px-3 py-2 text-xs ${product.matchedVariant?.color === color.name ? 'border-black bg-neutral-50' : 'border-neutral-200'}`}><span className="h-3 w-3 rounded-full border border-black/20" style={{ backgroundColor: color.hex }} />{color.name}</span>)}</div> : <p className="text-xs text-neutral-500">Information unavailable</p>}{product.matchedVariant && <p className="mt-2 text-[10px] uppercase tracking-wider text-neutral-500">Selected match · {product.matchedVariant.color || 'Color unavailable'} · SKU {product.matchedVariant.sku} · {product.matchedVariant.inStock ? 'Available' : 'Unavailable'}</p>}</div>
            <button onClick={addToBag} disabled={!purchasable} className={`flex w-full items-center justify-center gap-2 py-4 text-[11px] font-semibold uppercase tracking-[0.18em] text-white disabled:cursor-not-allowed disabled:bg-neutral-300 ${isAdded ? 'bg-emerald-700' : 'bg-black hover:bg-neutral-800'}`}>{isAdded && <Check className="h-4 w-4" />}{isAdded ? 'Added to bag' : purchasable ? `Add to bag - $${product.price.toFixed(2)}` : 'Currently unavailable'}</button>
            <div className="space-y-4 border-t border-neutral-200 pt-6 text-xs text-neutral-600"><Detail label="Composition" value={product.composition || 'Information unavailable'} /><Detail label="Care" value={product.care || 'Information unavailable'} /><Detail label="Availability" value={product.inStock ? 'Available online. Ask the stylist to check current store availability.' : 'Currently unavailable online. Ask the stylist for alternatives.'} /></div>
          </div>
        </div>
        {matchingProducts.length > 0 && <section className="border-t border-neutral-200 px-6 py-8 md:px-8"><div className="mb-5 flex items-end justify-between"><h3 className="font-serif-luxury text-xl">Complete the look</h3><span className="text-[10px] uppercase tracking-widest text-neutral-400">AI-curated pairings</span></div><div className="grid grid-cols-2 gap-4 sm:grid-cols-3">{matchingProducts.map((match) => <button key={match.id} onClick={() => onSelectMatchingProduct(match)} className="text-left"><img src={match.image} alt={match.name} className="aspect-[3/4] w-full object-cover object-top" /><span className="mt-2 block truncate text-xs">{match.name}</span><span className="font-mono text-xs text-neutral-500">${match.price.toFixed(2)}</span></button>)}</div></section>}
      </article>
    </div>
  );
};

const VoiceShortcut = ({ label, icon, onClick }: { label: string; icon: React.ReactNode; onClick: () => void }) => <button onClick={onClick} className="flex w-full items-center justify-between border border-neutral-200 bg-white px-3 py-2 text-left text-xs hover:border-black"><span>{label}</span>{icon}</button>;
const Detail = ({ label, value }: { label: string; value: string }) => <div><h4 className="mb-1 text-[10px] uppercase tracking-[0.16em] text-neutral-400">{label}</h4><p>{value}</p></div>;
