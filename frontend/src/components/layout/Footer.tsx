import React from 'react';

export const Footer: React.FC = () => (
  <footer className="border-t border-neutral-200 bg-white py-12 text-xs text-neutral-600">
    <div className="mx-auto max-w-[1600px] px-4 sm:px-8 lg:px-12 2xl:px-16">
      <div className="mb-10 grid grid-cols-1 gap-8 md:grid-cols-4">
        <div>
          <span className="mb-3 block text-xl font-bold tracking-[0.28em] text-black">NEXGEN</span>
          <p className="max-w-xs text-[11px] leading-relaxed text-neutral-500">AI fashion commerce with personal styling, catalogue discovery, and customer support by voice.</p>
        </div>
        <div><h4 className="mb-3 text-[10px] font-semibold uppercase tracking-[0.2em] text-neutral-900">Shop</h4><ul className="space-y-2 text-[11px]"><li>New arrivals</li><li>Dresses</li><li>Tailoring</li><li>Accessories</li></ul></div>
        <div><h4 className="mb-3 text-[10px] font-semibold uppercase tracking-[0.2em] text-neutral-900">Voice commerce</h4><ul className="space-y-2 text-[11px]"><li>Personal styling</li><li>Check availability</li><li>Track orders</li><li>Return assistance</li></ul></div>
        <div><h4 className="mb-3 text-[10px] font-semibold uppercase tracking-[0.2em] text-neutral-900">Client services</h4><ul className="space-y-2 text-[11px]"><li>Account</li><li>Delivery</li><li>Size guidance</li><li>Human stylist</li></ul></div>
      </div>
      <div className="flex flex-col gap-3 border-t border-neutral-100 pt-6 text-[10px] text-neutral-400 md:flex-row md:items-center md:justify-between">
        <p>© 2026 NexGen AI Commerce. All rights reserved.</p>
        <p className="max-w-2xl md:text-right">NexGen is an independent AI retail commerce system. Brand assets, catalogue data, and policies should be replaced or licensed for production deployment.</p>
      </div>
    </div>
  </footer>
);
