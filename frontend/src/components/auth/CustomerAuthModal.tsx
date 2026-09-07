import React from 'react';
import { X, ShieldCheck, Lock } from 'lucide-react';
import type { CustomerProfile } from '../../types/auth';

interface CustomerAuthModalProps {
  isOpen: boolean;
  onClose: () => void;
  currentCustomer: CustomerProfile;
  onUpdateCustomer: (profile: CustomerProfile) => void;
}

export const CustomerAuthModal: React.FC<CustomerAuthModalProps> = ({
  isOpen,
  onClose,
  currentCustomer,
  onUpdateCustomer,
}) => {
  const [activeTab, setActiveTab] = React.useState<'status' | 'guest_order' | 'demo_login'>('status');
  const [orderNumber, setOrderNumber] = React.useState(currentCustomer.activeOrderNumber || 'ZUS-2025-00001');
  const [emailOrPhone, setEmailOrPhone] = React.useState('elena.vance@example.com');

  if (!isOpen) return null;

  const handleVerifyGuestOrder = (e: React.FormEvent) => {
    e.preventDefault();
    onUpdateCustomer({
      id: 'cust_guest_9921',
      name: 'Elena (Guest)',
      email: emailOrPhone,
      type: 'GUEST',
      authLevel: 'GUEST_ORDER_VERIFIED',
      verified: true,
      activeOrderNumber: orderNumber,
    });
    onClose();
  };

  const handleDemoLogin = (tier: 'REGISTERED' | 'VIP_LOYALTY') => {
    if (tier === 'VIP_LOYALTY') {
      onUpdateCustomer({
        id: 'ae7cdeee-b0a3-5c13-9f18-6a57187fea1e',
        name: 'Elena Vance',
        email: 'elena.vance@nexgen-vip.com',
        phone: '+1 (212) 555-0182',
        type: 'VIP_LOYALTY',
        authLevel: 'VIP_VERIFIED',
        verified: true,
        activeOrderNumber: 'ZUS-2025-00001',
        defaultAddress: '666 5th Ave, Fl 3, New York, NY 10103',
      });
    } else {
      onUpdateCustomer({
        id: 'cust_reg_48102',
        name: 'Marcus Miller',
        email: 'marcus.m@example.com',
        type: 'REGISTERED',
        authLevel: 'LOGGED_IN',
        verified: true,
        activeOrderNumber: 'ZUS-2025-00042',
      });
    }
    onClose();
  };

  const handleResetToAnonymous = () => {
    onUpdateCustomer({
      id: 'anon_shopper',
      name: 'Guest Shopper',
      email: '',
      type: 'GUEST',
      authLevel: 'ANONYMOUS',
      verified: false,
    });
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="relative w-full max-w-lg bg-white border border-neutral-300 shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-neutral-200 px-6 py-4 bg-neutral-50">
          <div className="flex items-center space-x-2">
            <ShieldCheck className="w-4 h-4 text-neutral-800" />
            <h3 className="font-serif-luxury text-base uppercase tracking-wider text-neutral-900">
              Customer Identity & Verification
            </h3>
          </div>
          <button onClick={onClose} className="p-1 text-neutral-400 hover:text-black transition-colors">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Tab Selector */}
        <div className="flex border-b border-neutral-200 text-xs font-mono uppercase tracking-wider">
          <button
            onClick={() => setActiveTab('status')}
            className={`flex-1 py-3 text-center border-b-2 transition-colors ${
              activeTab === 'status' ? 'border-black text-black font-semibold bg-white' : 'border-transparent text-neutral-500 bg-neutral-50 hover:text-black'
            }`}
          >
            Current State
          </button>
          <button
            onClick={() => setActiveTab('guest_order')}
            className={`flex-1 py-3 text-center border-b-2 transition-colors ${
              activeTab === 'guest_order' ? 'border-black text-black font-semibold bg-white' : 'border-transparent text-neutral-500 bg-neutral-50 hover:text-black'
            }`}
          >
            Verify Order
          </button>
          <button
            onClick={() => setActiveTab('demo_login')}
            className={`flex-1 py-3 text-center border-b-2 transition-colors ${
              activeTab === 'demo_login' ? 'border-black text-black font-semibold bg-white' : 'border-transparent text-neutral-500 bg-neutral-50 hover:text-black'
            }`}
          >
            Demo Profiles
          </button>
        </div>

        {/* Tab 1: Current State */}
        {activeTab === 'status' && (
          <div className="p-6 space-y-4 text-xs">
            <div className="p-4 bg-neutral-50 border border-neutral-200 space-y-2">
              <div className="flex items-center justify-between">
                <span className="font-mono text-[10px] uppercase text-neutral-400">Current Auth Level:</span>
                <span className="font-mono font-semibold text-neutral-900 bg-neutral-200/80 px-2 py-0.5">
                  {currentCustomer.authLevel}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="font-mono text-[10px] uppercase text-neutral-400">Name:</span>
                <span className="font-medium text-neutral-900">{currentCustomer.name}</span>
              </div>
              {currentCustomer.email && (
                <div className="flex items-center justify-between">
                  <span className="font-mono text-[10px] uppercase text-neutral-400">Email:</span>
                  <span className="font-mono text-neutral-700">{currentCustomer.email}</span>
                </div>
              )}
              {currentCustomer.activeOrderNumber && (
                <div className="flex items-center justify-between">
                  <span className="font-mono text-[10px] uppercase text-neutral-400">Active Order:</span>
                  <span className="font-mono text-emerald-700 font-medium">{currentCustomer.activeOrderNumber}</span>
                </div>
              )}
              <div className="flex items-center justify-between pt-1">
                <span className="font-mono text-[10px] uppercase text-neutral-400">Verification Badge:</span>
                {currentCustomer.verified ? (
                  <span className="inline-flex items-center text-emerald-700 bg-emerald-50 px-2 py-0.5 font-mono text-[10px]">
                    <ShieldCheck className="w-3 h-3 mr-1" />
                    Verified Customer
                  </span>
                ) : (
                  <span className="text-neutral-400 font-mono text-[10px]">Unverified / Anonymous</span>
                )}
              </div>
            </div>

            <div className="pt-2 flex justify-between">
              <button
                onClick={handleResetToAnonymous}
                className="px-4 py-2 border border-neutral-300 text-neutral-700 text-xs uppercase tracking-wider hover:border-black transition-colors"
              >
                Reset to Anonymous Shopper
              </button>
              <button
                onClick={() => setActiveTab('guest_order')}
                className="px-4 py-2 bg-black text-white text-xs uppercase tracking-wider hover:bg-neutral-800 transition-colors"
              >
                Verify an Order
              </button>
            </div>
          </div>
        )}

        {/* Tab 2: Guest Order Verification */}
        {activeTab === 'guest_order' && (
          <form onSubmit={handleVerifyGuestOrder} className="p-6 space-y-4 text-xs">
            <p className="text-neutral-600 leading-relaxed">
              Verify an existing retail order to test order tracking, return eligibility, or cancellation flows via the voice assistant.
            </p>

            <div>
              <label className="block text-[10px] uppercase tracking-wider font-mono text-neutral-500 mb-1">
                Order Number
              </label>
              <input
                type="text"
                required
                value={orderNumber}
                onChange={(e) => setOrderNumber(e.target.value)}
                placeholder="e.g. ZUS-2025-00001"
                className="w-full px-3 py-2 border border-neutral-300 font-mono focus:border-black focus:outline-none"
              />
              <span className="text-[10px] text-neutral-400 font-mono block mt-1">
                Sample orders: ZUS-2025-00001 (Delivered), ZUS-2025-00042 (Shipped)
              </span>
            </div>

            <div>
              <label className="block text-[10px] uppercase tracking-wider font-mono text-neutral-500 mb-1">
                Email Address or Phone Number
              </label>
              <input
                type="text"
                required
                value={emailOrPhone}
                onChange={(e) => setEmailOrPhone(e.target.value)}
                placeholder="elena.vance@example.com"
                className="w-full px-3 py-2 border border-neutral-300 font-mono focus:border-black focus:outline-none"
              />
            </div>

            <div className="pt-2 flex items-center justify-end space-x-3">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 border border-neutral-300 text-neutral-700 uppercase tracking-wider hover:border-black transition-colors"
              >
                Cancel
              </button>
              <button
                type="submit"
                className="px-5 py-2 bg-black text-white uppercase tracking-wider font-medium hover:bg-neutral-800 transition-colors"
              >
                Verify & Continue
              </button>
            </div>
          </form>
        )}

        {/* Tab 3: Demo Profiles */}
        {activeTab === 'demo_login' && (
          <div className="p-6 space-y-4 text-xs">
            <p className="text-neutral-600 leading-relaxed">
              Select a pre-configured synthetic profile to test varied customer tiers and permissions:
            </p>

            <div className="space-y-2">
              <div
                onClick={() => handleDemoLogin('VIP_LOYALTY')}
                className="p-3 border border-neutral-200 hover:border-black cursor-pointer bg-neutral-50 hover:bg-white transition-all flex items-center justify-between"
              >
                <div>
                  <div className="flex items-center space-x-2">
                    <span className="font-semibold text-neutral-900">Elena Vance</span>
                    <span className="px-1.5 py-0.5 bg-neutral-900 text-white font-mono text-[9px] uppercase">
                      VIP Loyalty Member
                    </span>
                  </div>
                  <span className="text-[11px] text-neutral-500 font-mono block mt-0.5">
                    Tier: Gold • Active Order: ZUS-2025-00001
                  </span>
                </div>
                <button className="text-xs uppercase tracking-wider text-black font-semibold underline">
                  Activate
                </button>
              </div>

              <div
                onClick={() => handleDemoLogin('REGISTERED')}
                className="p-3 border border-neutral-200 hover:border-black cursor-pointer bg-neutral-50 hover:bg-white transition-all flex items-center justify-between"
              >
                <div>
                  <div className="flex items-center space-x-2">
                    <span className="font-semibold text-neutral-900">Marcus Miller</span>
                    <span className="px-1.5 py-0.5 bg-neutral-200 text-neutral-800 font-mono text-[9px] uppercase">
                      Registered Shopper
                    </span>
                  </div>
                  <span className="text-[11px] text-neutral-500 font-mono block mt-0.5">
                    Standard Customer • Active Order: ZUS-2025-00042
                  </span>
                </div>
                <button className="text-xs uppercase tracking-wider text-black font-semibold underline">
                  Activate
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Security Footer */}
        <div className="border-t border-neutral-200 px-6 py-3 bg-neutral-50 text-[10px] text-neutral-400 font-mono flex items-center space-x-1.5">
          <Lock className="w-3 h-3 text-neutral-400" />
          <span>UI Mock Placeholder — Real biometric/SSO voice authentication will be integrated in Phase 3.</span>
        </div>
      </div>
    </div>
  );
};

