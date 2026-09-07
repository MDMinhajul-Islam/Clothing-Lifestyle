import React from 'react';
import { X, Mic, Check, ShieldCheck, MapPin, Sparkles, ChevronRight } from 'lucide-react';
import type { Product } from '../../types/catalog';

interface ProductDetailModalProps {
  product: Product | null;
  onClose: () => void;
  onAddToCart: (product: Product, size: string) => void;
  onAskVoicePrompt: (prompt: string) => void;
  matchingProducts: Product[];
  onSelectMatchingProduct: (product: Product) => void;
}

export const ProductDetailModal: React.FC<ProductDetailModalProps> = ({
  product,
  onClose,
  onAddToCart,
  onAskVoicePrompt,
  matchingProducts,
  onSelectMatchingProduct,
}) => {
  const [userSelectedSize, setUserSelectedSize] = React.useState<string | null>(null);
  const [userSelectedImage, setUserSelectedImage] = React.useState<string | null>(null);
  const [addedAnimation, setAddedAnimation] = React.useState<boolean>(false);
  const [prevProductId, setPrevProductId] = React.useState<string | null>(null);

  if (product && product.id !== prevProductId) {
    setPrevProductId(product.id);
    setUserSelectedSize(null);
    setUserSelectedImage(null);
    setAddedAnimation(false);
  }

  if (!product) return null;

  const selectedSize = userSelectedSize ?? (product.sizes[1] || product.sizes[0] || 'M');
  const selectedImage = userSelectedImage ?? product.image;

  const handleAddToCart = () => {
    onAddToCart(product, selectedSize);
    setAddedAnimation(true);
    setTimeout(() => setAddedAnimation(false), 2000);
  };

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-black/60 backdrop-blur-sm flex justify-end transition-opacity">
      {/* Click outside backdrop to close */}
      <div className="fixed inset-0" onClick={onClose} />

      {/* Side Detail Panel */}
      <div className="relative w-full max-w-2xl bg-white shadow-2xl h-full min-h-screen overflow-y-auto z-10 flex flex-col border-l border-neutral-200">
        {/* Sticky Header */}
        <div className="sticky top-0 z-20 flex items-center justify-between border-b border-neutral-200 bg-white/95 px-6 py-4 backdrop-blur-md">
          <div className="flex items-center space-x-2">
            <span className="font-mono text-[10px] uppercase tracking-widest text-neutral-400">
              REF. {product.commercialReference || product.id}
            </span>
            <span className="text-neutral-300">•</span>
            <span className="inline-flex items-center text-[10px] font-mono text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded">
              <ShieldCheck className="w-3 h-3 mr-1" />
              Reference Catalogue Item
            </span>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-neutral-400 hover:text-black hover:bg-neutral-100 rounded-full transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content Body */}
        <div className="p-6 space-y-8 flex-1">
          {/* Main Imagery */}
          <div className="space-y-3">
            <div className="aspect-[3/4] w-full overflow-hidden bg-neutral-100 border border-neutral-200">
              <img
                src={selectedImage || product.image}
                alt={product.name}
                className="h-full w-full object-cover object-top transition-all duration-500"
              />
            </div>

            {/* Gallery thumbnails */}
            {product.gallery.length > 1 && (
              <div className="flex space-x-2 overflow-x-auto pb-1">
                {product.gallery.map((img, idx) => (
                  <button
                    key={idx}
                    onClick={() => setUserSelectedImage(img)}
                    className={`relative aspect-[3/4] w-16 overflow-hidden border transition-all ${
                      selectedImage === img
                        ? 'border-black ring-1 ring-black'
                        : 'border-neutral-200 opacity-60 hover:opacity-100'
                    }`}
                  >
                    <img src={img} alt="thumbnail" className="h-full w-full object-cover object-top" />
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Title & Price */}
          <div>
            <h2 className="text-2xl font-serif-luxury uppercase tracking-wider text-neutral-900">
              {product.name}
            </h2>
            <div className="mt-2 flex items-baseline space-x-3 font-mono">
              <span className="text-xl font-medium text-neutral-900">
                ${product.price.toFixed(2)}
              </span>
              {product.originalPrice && (
                <span className="text-sm text-neutral-400 line-through">
                  ${product.originalPrice.toFixed(2)}
                </span>
              )}
              <span className="text-xs uppercase text-neutral-500 font-sans">
                {product.currency}
              </span>
            </div>
            <p className="mt-4 text-xs text-neutral-600 leading-relaxed">
              {product.longDescription || product.description}
            </p>
          </div>

          {/* Voice Prompt Shortcuts (Voice Commerce Feature) */}
          <div className="p-4 bg-neutral-50 border border-neutral-200 rounded-none space-y-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <Mic className="w-3.5 h-3.5 text-emerald-600" />
                <span className="text-[11px] font-mono uppercase tracking-wider font-semibold text-neutral-900">
                  Ask NexGen Voice Assistant
                </span>
              </div>
              <span className="text-[10px] font-mono text-neutral-400">Hands-Free</span>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 pt-1">
              <button
                onClick={() => onAskVoicePrompt(`What size should I choose for ${product.name}?`)}
                className="px-2.5 py-1.5 bg-white border border-neutral-200 hover:border-black text-[11px] text-neutral-700 text-left transition-colors flex items-center justify-between"
              >
                <span>Ask about size</span>
                <ChevronRight className="w-3 h-3 text-neutral-400" />
              </button>
              <button
                onClick={() => onAskVoicePrompt(`Check availability for ${product.name} at Fifth Ave store`)}
                className="px-2.5 py-1.5 bg-white border border-neutral-200 hover:border-black text-[11px] text-neutral-700 text-left transition-colors flex items-center justify-between"
              >
                <span>Check stock</span>
                <MapPin className="w-3 h-3 text-neutral-400" />
              </button>
              <button
                onClick={() => onAskVoicePrompt(`What matches with ${product.name}?`)}
                className="px-2.5 py-1.5 bg-white border border-neutral-200 hover:border-black text-[11px] text-neutral-700 text-left transition-colors flex items-center justify-between"
              >
                <span>Find pairings</span>
                <Sparkles className="w-3 h-3 text-neutral-400" />
              </button>
            </div>
          </div>

          {/* Size Selector */}
          <div>
            <div className="flex items-center justify-between mb-2 text-xs">
              <span className="font-mono uppercase tracking-wider text-neutral-700 font-medium">
                Select Size: <span className="text-black font-semibold">{selectedSize}</span>
              </span>
              <button
                onClick={() => onAskVoicePrompt(`What size should I choose for ${product.name}?`)}
                className="text-[11px] text-neutral-500 underline hover:text-black font-mono"
              >
                Size Advisor
              </button>
            </div>
            <div className="grid grid-cols-5 gap-2">
              {product.sizes.map((s) => (
                <button
                  key={s}
                  onClick={() => setUserSelectedSize(s)}
                  className={`py-2.5 text-xs font-mono uppercase tracking-wider border transition-all ${
                    selectedSize === s
                      ? 'bg-black text-white border-black font-semibold'
                      : 'bg-white text-neutral-800 border-neutral-200 hover:border-neutral-400'
                  }`}
                >
                  {s}
                </button>
              ))}
            </div>
          </div>

          {/* Add To Cart Action */}
          <div className="space-y-2 pt-2">
            <button
              onClick={handleAddToCart}
              className={`w-full py-3.5 text-xs uppercase tracking-[0.2em] font-medium transition-all flex items-center justify-center space-x-2 ${
                addedAnimation
                  ? 'bg-emerald-700 text-white'
                  : 'bg-black text-white hover:bg-neutral-800'
              }`}
            >
              {addedAnimation ? (
                <>
                  <Check className="w-4 h-4" />
                  <span>Added to Shopping Bag</span>
                </>
              ) : (
                <span>Add to Bag — ${product.price.toFixed(2)}</span>
              )}
            </button>
          </div>

          {/* Composition & Care Details */}
          <div className="border-t border-neutral-200 pt-6 space-y-4 text-xs">
            <div>
              <h4 className="font-mono text-[11px] uppercase tracking-wider text-neutral-400 mb-1">
                Composition & Materials
              </h4>
              <p className="text-neutral-700">{product.composition || '100% Sustainable Cotton'}</p>
            </div>

            <div>
              <h4 className="font-mono text-[11px] uppercase tracking-wider text-neutral-400 mb-1">
                Care Instructions
              </h4>
              <p className="text-neutral-700">{product.care || 'Machine wash max 30C/86F delicate cycle.'}</p>
            </div>

            <div>
              <h4 className="font-mono text-[11px] uppercase tracking-wider text-neutral-400 mb-1">
                Boutique Availability
              </h4>
              <p className="text-neutral-700 flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-emerald-500 inline-block"></span>
                In stock at Fifth Ave Flagship and SoHo NYC (Ask voice for live counts)
              </p>
            </div>
          </div>

          {/* Complete the Look Section */}
          {matchingProducts.length > 0 && (
            <div className="border-t border-neutral-200 pt-6 space-y-4">
              <div className="flex items-center justify-between">
                <h4 className="font-serif-luxury text-base uppercase tracking-wider text-neutral-900">
                  Complete the Look
                </h4>
                <span className="text-[10px] font-mono text-neutral-400">Stylist Recommendations</span>
              </div>

              <div className="grid grid-cols-2 gap-3">
                {matchingProducts.map((match) => (
                  <div
                    key={match.id}
                    onClick={() => onSelectMatchingProduct(match)}
                    className="group cursor-pointer border border-neutral-200 p-2.5 bg-neutral-50 hover:bg-white hover:border-black transition-all flex flex-col"
                  >
                    <div className="aspect-[3/4] w-full overflow-hidden bg-neutral-200 mb-2">
                      <img
                        src={match.image}
                        alt={match.name}
                        className="h-full w-full object-cover object-top group-hover:scale-105 transition-transform duration-500"
                      />
                    </div>
                    <span className="text-[11px] font-medium text-neutral-900 line-clamp-1 group-hover:underline">
                      {match.name}
                    </span>
                    <span className="text-xs font-mono text-neutral-600 mt-0.5">
                      ${match.price.toFixed(2)}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
