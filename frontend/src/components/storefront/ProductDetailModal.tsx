import React from 'react';
import { Check, ChevronRight, MapPin, Mic, Sparkles, X } from 'lucide-react';
import type { Product } from '../../types/catalog';

interface ProductDetailModalProps {
  product: Product | null;
  onClose: () => void;
  onAddToCart: (product: Product, size: string) => void;
  onAskVoicePrompt: (prompt: string) => void;
  matchingProducts: Product[];
  onSelectMatchingProduct: (product: Product) => void;
}

export const ProductDetailModal: React.FC<ProductDetailModalProps> = ({ product, onClose, onAddToCart, onAskVoicePrompt, matchingProducts, onSelectMatchingProduct }) => {
  const [sizeSelection, setSizeSelection] = React.useState<{ productId: string; value: string } | null>(null);
  const [imageSelection, setImageSelection] = React.useState<{ productId: string; value: string } | null>(null);
  const [addedProductId, setAddedProductId] = React.useState<string | null>(null);

  if (!product) return null;
  const selectedSize = sizeSelection?.productId === product.id ? sizeSelection.value : product.sizes[0] || 'M';
  const selectedImage = imageSelection?.productId === product.id ? imageSelection.value : product.image;
  const isAdded = addedProductId === product.id;
  const addToBag = () => {
    onAddToCart(product, selectedSize || product.sizes[0] || 'M');
    setAddedProductId(product.id);
    window.setTimeout(() => setAddedProductId(null), 1800);
  };

  return (
    <div className="fixed inset-0 z-50 flex justify-end overflow-y-auto bg-black/60 backdrop-blur-sm" role="dialog" aria-modal="true" aria-label={product.name}>
      <button className="fixed inset-0 cursor-default" onClick={onClose} aria-label="Close product details" />
      <article className="relative z-10 min-h-screen w-full max-w-3xl overflow-y-auto border-l border-neutral-200 bg-white shadow-2xl">
        <header className="sticky top-0 z-20 flex items-center justify-between border-b border-neutral-200 bg-white/95 px-6 py-4 backdrop-blur-md">
          <div className="text-[10px] uppercase tracking-[0.18em] text-neutral-500"><span>NexGen collection</span><span className="mx-2 text-neutral-300">/</span><span>Ref. {product.commercialReference || product.id}</span></div>
          <button onClick={onClose} className="rounded-full p-2 text-neutral-500 hover:bg-neutral-100 hover:text-black" aria-label="Close"><X className="h-5 w-5" /></button>
        </header>

        <div className="grid gap-8 p-6 md:grid-cols-[1.15fr_0.85fr] md:p-8">
          <div>
            <div className="aspect-[3/4] overflow-hidden bg-neutral-100"><img src={selectedImage || product.image} alt={product.name} className="h-full w-full object-cover object-top" /></div>
            {product.gallery.length > 1 && <div className="mt-3 flex gap-2 overflow-x-auto">{product.gallery.map((image) => <button key={image} onClick={() => setImageSelection({ productId: product.id, value: image })} className={`w-16 shrink-0 overflow-hidden border ${selectedImage === image ? 'border-black' : 'border-neutral-200 opacity-70'}`}><img src={image} alt="" className="aspect-[3/4] h-full w-full object-cover object-top" /></button>)}</div>}
          </div>

          <div className="space-y-7">
            <div><p className="text-[10px] uppercase tracking-[0.2em] text-neutral-400">{product.department} / {product.category}</p><h2 className="mt-2 font-serif-luxury text-3xl leading-tight text-neutral-950">{product.name}</h2><p className="mt-3 font-mono text-lg">${product.price.toFixed(2)} <span className="text-xs text-neutral-400">{product.currency}</span></p><p className="mt-5 text-sm leading-relaxed text-neutral-600">{product.longDescription || product.description}</p></div>
            <div className="border border-neutral-200 bg-neutral-50 p-4">
              <div className="mb-3 flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[0.16em]"><Mic className="h-3.5 w-3.5 text-emerald-600" />Ask the Live AI Shopping Assistant</div>
              <div className="space-y-2"><VoiceShortcut label="Ask about size" icon={<ChevronRight className="h-3.5 w-3.5" />} onClick={() => onAskVoicePrompt(`What size should I choose for ${product.name}?`)} /><VoiceShortcut label="Check availability" icon={<MapPin className="h-3.5 w-3.5" />} onClick={() => onAskVoicePrompt(`Check availability for ${product.name}`)} /><VoiceShortcut label="Find a complete look" icon={<Sparkles className="h-3.5 w-3.5" />} onClick={() => onAskVoicePrompt(`What matches with ${product.name}?`)} /></div>
            </div>
            <div><div className="mb-3 flex justify-between text-[10px] uppercase tracking-[0.15em]"><span>Select size</span><span>{selectedSize}</span></div><div className="grid grid-cols-4 gap-2">{product.sizes.map((size) => <button key={size} onClick={() => setSizeSelection({ productId: product.id, value: size })} className={`border py-2.5 text-xs ${selectedSize === size ? 'border-black bg-black text-white' : 'border-neutral-200 hover:border-black'}`}>{size}</button>)}</div></div>
            <button onClick={addToBag} className={`flex w-full items-center justify-center gap-2 py-4 text-[11px] font-semibold uppercase tracking-[0.18em] text-white ${isAdded ? 'bg-emerald-700' : 'bg-black hover:bg-neutral-800'}`}>{isAdded && <Check className="h-4 w-4" />}{isAdded ? 'Added to bag' : `Add to bag - $${product.price.toFixed(2)}`}</button>
            <div className="space-y-4 border-t border-neutral-200 pt-6 text-xs text-neutral-600"><Detail label="Composition" value={product.composition || 'Material information available on request.'} /><Detail label="Care" value={product.care || 'Follow the care label attached to the garment.'} /><Detail label="Availability" value={product.inStock ? 'Available online. Ask the assistant to check current store availability.' : 'Currently unavailable online. Ask the assistant for alternatives.'} /></div>
          </div>
        </div>
        {matchingProducts.length > 0 && <section className="border-t border-neutral-200 px-6 py-8 md:px-8"><div className="mb-5 flex items-end justify-between"><h3 className="font-serif-luxury text-xl">Complete the look</h3><span className="text-[10px] uppercase tracking-widest text-neutral-400">AI-curated pairings</span></div><div className="grid grid-cols-2 gap-4 sm:grid-cols-3">{matchingProducts.map((match) => <button key={match.id} onClick={() => onSelectMatchingProduct(match)} className="text-left"><img src={match.image} alt={match.name} className="aspect-[3/4] w-full object-cover object-top" /><span className="mt-2 block truncate text-xs">{match.name}</span><span className="font-mono text-xs text-neutral-500">${match.price.toFixed(2)}</span></button>)}</div></section>}
      </article>
    </div>
  );
};

const VoiceShortcut = ({ label, icon, onClick }: { label: string; icon: React.ReactNode; onClick: () => void }) => <button onClick={onClick} className="flex w-full items-center justify-between border border-neutral-200 bg-white px-3 py-2 text-left text-xs hover:border-black"><span>{label}</span>{icon}</button>;
const Detail = ({ label, value }: { label: string; value: string }) => <div><h4 className="mb-1 text-[10px] uppercase tracking-[0.16em] text-neutral-400">{label}</h4><p>{value}</p></div>;
