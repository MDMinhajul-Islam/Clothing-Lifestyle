import React from 'react';

export const Footer: React.FC = () => {
  return (
    <footer className="border-t border-neutral-200 bg-white pt-12 pb-8 text-neutral-600 text-xs">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8 mb-8">
          <div>
            <span className="font-display tracking-[0.25em] text-lg font-semibold uppercase text-black block mb-3">
              NEXGEN
            </span>
            <p className="text-neutral-500 text-[11px] leading-relaxed">
              Omnichannel AI voice commerce and conversational fashion intelligence platform.
            </p>
          </div>

          <div>
            <h4 className="uppercase tracking-widest text-[10px] font-semibold text-neutral-900 mb-3 font-mono">
              Voice Capabilities
            </h4>
            <ul className="space-y-1.5 text-[11px]">
              <li>Real-time Catalog Search</li>
              <li>Store Boutique Availability</li>
              <li>Order Tracking & Milestones</li>
              <li>Return Authorization & RMAs</li>
            </ul>
          </div>

          <div>
            <h4 className="uppercase tracking-widest text-[10px] font-semibold text-neutral-900 mb-3 font-mono">
              Provenance & Architecture
            </h4>
            <ul className="space-y-1.5 text-[11px]">
              <li>Reference Retail Demo Catalogue</li>
              <li>Deterministic Tool Gateway API</li>
              <li>Zero Direct LLM Database Access</li>
              <li>HMAC Two-Step Write Protocol</li>
            </ul>
          </div>

          <div>
            <h4 className="uppercase tracking-widest text-[10px] font-semibold text-neutral-900 mb-3 font-mono">
              Security & Environment
            </h4>
            <p className="text-[11px] text-neutral-500 leading-relaxed mb-2">
              Protected endpoints enforce X-Tool-Secret authentication. Production requires server-side BFF proxy.
            </p>
            <span className="inline-block px-2 py-0.5 bg-neutral-100 border border-neutral-200 text-[10px] font-mono text-neutral-700">
              Retell Voice-Ready Architecture
            </span>
          </div>
        </div>

        <div className="border-t border-neutral-100 pt-6 flex flex-col sm:flex-row items-center justify-between text-[11px] text-neutral-400 font-mono">
          <p>© 2026 NexGen AI Commerce Inc. All rights reserved.</p>
          <p className="mt-2 sm:mt-0">Zara-style reference process & editorial aesthetic. Prototype demo only.</p>
        </div>
      </div>
    </footer>
  );
};

