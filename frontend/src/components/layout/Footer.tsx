import React from 'react';

interface FooterProps {
  onShop: () => void;
  onNewArrivals: () => void;
  onSelectCategory: (category: string) => void;
  onStartVoice: () => void;
  onAskVoice: (prompt: string) => void;
  onOpenAccount: () => void;
}

const FooterLink = ({ children, onClick }: { children: React.ReactNode; onClick: () => void }) => <button onClick={onClick} className="transition-colors hover:text-black hover:underline">{children}</button>;

export const Footer: React.FC<FooterProps> = ({ onShop, onNewArrivals, onSelectCategory, onStartVoice, onAskVoice, onOpenAccount }) => (
  <footer className="border-t border-neutral-200 bg-white py-12 text-xs text-neutral-600">
    <div className="mx-auto max-w-[1600px] px-4 sm:px-8 lg:px-12 2xl:px-16">
      <div className="mb-10 grid grid-cols-1 gap-8 md:grid-cols-4">
        <div>
          <span className="mb-3 block text-xl font-bold tracking-[0.28em] text-black">NEXGEN</span>
          <p className="max-w-xs text-[11px] leading-relaxed text-neutral-500">AI fashion commerce with personal styling, catalogue discovery, and customer support by voice.</p>
        </div>
        <div><button onClick={onShop} className="mb-3 text-[10px] font-semibold uppercase tracking-[0.2em] text-neutral-900 hover:underline">Shop</button><ul className="space-y-2 text-[11px]"><li><FooterLink onClick={onNewArrivals}>New arrivals</FooterLink></li><li><FooterLink onClick={() => onSelectCategory('Dresses')}>Dresses</FooterLink></li><li><FooterLink onClick={() => onSelectCategory('Pants & Jeans')}>Tailoring</FooterLink></li><li><FooterLink onClick={() => onSelectCategory('Accessories')}>Accessories</FooterLink></li></ul></div>
        <div><button onClick={onStartVoice} className="mb-3 text-[10px] font-semibold uppercase tracking-[0.2em] text-neutral-900 hover:underline">Voice commerce</button><ul className="space-y-2 text-[11px]"><li><FooterLink onClick={onStartVoice}>Personal styling</FooterLink></li><li><FooterLink onClick={() => onAskVoice('Check availability')}>Check availability</FooterLink></li><li><FooterLink onClick={() => onAskVoice('Track my order')}>Track orders</FooterLink></li><li><FooterLink onClick={() => onAskVoice('Help me with a return')}>Return assistance</FooterLink></li></ul></div>
        <div><button onClick={onOpenAccount} className="mb-3 text-[10px] font-semibold uppercase tracking-[0.2em] text-neutral-900 hover:underline">Client services</button><ul className="space-y-2 text-[11px]"><li><FooterLink onClick={onOpenAccount}>Account</FooterLink></li><li><FooterLink onClick={() => onAskVoice('Tell me about delivery')}>Delivery</FooterLink></li><li><FooterLink onClick={() => onAskVoice('Help me choose a size')}>Size guidance</FooterLink></li><li><FooterLink onClick={() => onAskVoice('I would like a human stylist')}>Human stylist</FooterLink></li></ul></div>
      </div>
      <div className="flex flex-col gap-3 border-t border-neutral-100 pt-6 text-[10px] text-neutral-400 md:flex-row md:items-center md:justify-between">
        <p>© 2026 NexGen AI Commerce. All rights reserved.</p>
        <p className="max-w-2xl md:text-right">NexGen is an independent AI retail commerce system. Brand assets, catalogue data, and policies should be replaced or licensed for production deployment.</p>
      </div>
    </div>
  </footer>
);
