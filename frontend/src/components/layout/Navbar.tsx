import React from 'react';
import { BarChart3, Search, ShieldCheck, ShoppingBag, Sparkles, UserCheck } from 'lucide-react';
import type { CustomerProfile } from '../../types/auth';
import type { VoiceState } from '../../types/voice';

interface NavbarProps {
  currentView: 'storefront' | 'admin';
  onNavigate: (view: 'storefront' | 'admin') => void;
  customer: CustomerProfile;
  onOpenAuth: () => void;
  voiceState: VoiceState;
  isVoiceActive: boolean;
  onToggleVoice: () => void;
  cartCount: number;
  onSearchClick: () => void;
  onSelectCategory?: (category: string) => void;
}

const voiceLabel: Record<VoiceState, string> = {
  IDLE: 'Start live AI call',
  CONNECTING: 'Connecting',
  LISTENING: 'Caller speaking',
  THINKING: 'Stylist thinking',
  SPEAKING: 'Stylist speaking',
};

export const Navbar: React.FC<NavbarProps> = ({
  currentView,
  onNavigate,
  customer,
  onOpenAuth,
  voiceState,
  isVoiceActive,
  onToggleVoice,
  cartCount,
  onSearchClick,
  onSelectCategory,
}) => {
  const browse = (category?: string) => {
    onNavigate('storefront');
    if (category) onSelectCategory?.(category);
  };

  return (
    <header className="sticky top-0 z-40 border-b border-neutral-200/80 bg-white/95 backdrop-blur-xl">
      <div className="mx-auto flex h-20 max-w-[1600px] items-center justify-between px-4 sm:px-8 lg:px-12 2xl:px-16">
        <div className="flex items-center gap-8 xl:gap-14">
          <button onClick={() => browse('All Items')} className="group inline-flex flex-col justify-center self-center text-left leading-none" aria-label="Open NexGen collection">
            <span className="block font-display text-2xl font-bold tracking-[0.3em] text-black lg:text-3xl">NEXGEN</span>
            <span className="mt-1.5 block text-[9px] uppercase leading-none tracking-[0.24em] text-neutral-500 sm:text-[10px]">
              AI Fashion & Voice Commerce
            </span>
          </button>

          <nav className="hidden items-center gap-6 text-[11px] font-medium uppercase tracking-[0.2em] text-neutral-600 lg:flex">
            <button onClick={() => browse('All Items')} className="transition-colors hover:text-black">Collection</button>
            <button onClick={() => browse('Dresses')} className="transition-colors hover:text-black">Dresses</button>
            <button onClick={() => browse('Blazers & Jackets')} className="transition-colors hover:text-black">Outerwear</button>
            <button onClick={() => browse('Pants & Jeans')} className="transition-colors hover:text-black">Tailoring</button>
            <button
              onClick={() => onNavigate('admin')}
              className={`flex items-center gap-1.5 transition-colors hover:text-black ${currentView === 'admin' ? 'text-black' : ''}`}
            >
              <BarChart3 className="h-3.5 w-3.5" /> Operations
            </button>
          </nav>
        </div>

        <div className="flex items-center gap-2 sm:gap-4">
          <button onClick={onSearchClick} className="p-2 text-neutral-600 transition-colors hover:text-black" aria-label="Search collection">
            <Search className="h-4 w-4" />
          </button>
          <button
            onClick={onToggleVoice}
            className={`flex items-center gap-2 rounded-full border px-3 py-2 text-[10px] font-semibold uppercase tracking-[0.14em] transition-all sm:px-4 ${
              isVoiceActive ? 'border-black bg-black text-white ring-2 ring-emerald-400/30' : 'border-neutral-900 bg-neutral-900 text-white hover:bg-black'
            }`}
          >
            <span className={`h-2 w-2 rounded-full ${isVoiceActive ? 'animate-pulse bg-emerald-400' : 'bg-emerald-500'}`} />
            <span className="hidden sm:inline">{voiceLabel[voiceState]}</span>
            <Sparkles className="h-3.5 w-3.5 text-emerald-400 sm:hidden" />
          </button>
          <button onClick={onOpenAuth} className="flex items-center gap-1.5 rounded-full border border-neutral-200 bg-neutral-100 px-3 py-2 text-[11px] text-neutral-700">
            {customer.verified ? <ShieldCheck className="h-3.5 w-3.5 text-emerald-600" /> : <UserCheck className="h-3.5 w-3.5" />}
            <span className="hidden sm:inline">{customer.authLevel === 'ANONYMOUS' ? 'Guest' : customer.name.split(' ')[0]}</span>
          </button>
          <div className="relative p-2 text-neutral-800" aria-label={`${cartCount} items in bag`}>
            <ShoppingBag className="h-4 w-4" />
            {cartCount > 0 && <span className="absolute right-0 top-0 grid h-4 min-w-4 place-items-center rounded-full bg-black px-1 text-[9px] text-white">{cartCount}</span>}
          </div>
        </div>
      </div>
    </header>
  );
};
