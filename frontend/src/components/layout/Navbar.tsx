import React from 'react';
import { Mic, MicOff, ShoppingBag, UserCheck, ShieldCheck, BarChart3, Search } from 'lucide-react';
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
}

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
}) => {
  return (
    <header className="sticky top-0 z-40 w-full border-b border-neutral-200/80 bg-white/95 backdrop-blur-md transition-all">
      <div className="mx-auto flex h-20 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
        {/* Left: Brand Identity */}
        <div className="flex items-center space-x-8">
          <button
            onClick={() => onNavigate('storefront')}
            className="group flex flex-col text-left focus:outline-none"
          >
            <span className="font-display tracking-[0.28em] text-2xl font-semibold uppercase text-black transition-opacity group-hover:opacity-80">
              NEXGEN
            </span>
            <span className="text-[10px] tracking-[0.22em] uppercase text-neutral-500 font-sans">
              AI Fashion & Voice Commerce
            </span>
          </button>

          <nav className="hidden md:flex items-center space-x-6 text-xs uppercase tracking-[0.18em] font-medium text-neutral-600">
            <button 
              onClick={() => onNavigate('storefront')} 
              className={`hover:text-black transition-colors ${currentView === 'storefront' ? 'text-black font-semibold' : ''}`}
            >
              Collection
            </button>
            <span className="text-neutral-300">/</span>
            <button 
              onClick={() => onNavigate('storefront')} 
              className="hover:text-black transition-colors"
            >
              Editorial
            </button>
            <span className="text-neutral-300">/</span>
            <button
              onClick={() => onNavigate('admin')}
              className={`flex items-center space-x-1.5 hover:text-black transition-colors ${
                currentView === 'admin' ? 'text-black font-semibold' : ''
              }`}
            >
              <BarChart3 className="w-3.5 h-3.5" />
              <span>Ops Console</span>
            </button>
          </nav>
        </div>

        {/* Right: Actions (Voice, Auth, Cart) */}
        <div className="flex items-center space-x-3 sm:space-x-4">
          {/* Quick Search */}
          <button
            onClick={onSearchClick}
            className="p-2 text-neutral-600 hover:text-black transition-colors"
            title="Filter collection"
          >
            <Search className="w-4 h-4" />
          </button>

          {/* Voice Commerce Action Trigger */}
          <button
            onClick={onToggleVoice}
            className={`flex items-center space-x-2 px-3.5 py-1.5 rounded-full text-xs font-medium tracking-wider uppercase transition-all duration-300 border ${
              isVoiceActive
                ? 'bg-black text-white border-black shadow-lg shadow-black/10'
                : 'bg-neutral-50 text-neutral-800 border-neutral-200 hover:border-black hover:bg-white'
            }`}
          >
            {isVoiceActive ? (
              <>
                <span className="relative flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
                </span>
                <span>{voiceState === 'LISTENING' ? 'Listening…' : voiceState === 'SPEAKING' ? 'Speaking…' : 'Live Call'}</span>
                <Mic className="w-3.5 h-3.5 text-emerald-400" />
              </>
            ) : (
              <>
                <MicOff className="w-3.5 h-3.5 text-neutral-500" />
                <span>Talk with NexGen</span>
              </>
            )}
          </button>

          {/* Customer Verification Badge / Auth Trigger */}
          <button
            onClick={onOpenAuth}
            className="flex items-center space-x-1.5 px-3 py-1.5 text-xs text-neutral-700 bg-neutral-100/80 hover:bg-neutral-200/80 rounded-full transition-colors"
            title="Customer Verification Status"
          >
            {customer.verified ? (
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
            ) : (
              <UserCheck className="w-3.5 h-3.5 text-neutral-500" />
            )}
            <span className="hidden sm:inline font-mono text-[11px]">
              {customer.authLevel === 'ANONYMOUS' ? 'Guest' : customer.name.split(' ')[0]}
            </span>
          </button>

          {/* Shopping Bag */}
          <div className="relative p-2 text-neutral-800 hover:text-black cursor-pointer">
            <ShoppingBag className="w-4 h-4" />
            {cartCount > 0 && (
              <span className="absolute top-1 right-1 flex h-4 w-4 items-center justify-center rounded-full bg-black text-[10px] font-semibold text-white">
                {cartCount}
              </span>
            )}
          </div>
        </div>
      </div>
    </header>
  );
};

