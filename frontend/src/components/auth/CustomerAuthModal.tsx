import React from 'react';
import { ArrowLeft, Lock, UserRound, X } from 'lucide-react';
import type { CustomerProfile } from '../../types/auth';

interface Props { isOpen: boolean; onClose: () => void; currentCustomer: CustomerProfile; onUpdateCustomer: (customer: CustomerProfile) => void }
type View = 'login' | 'register' | 'forgot' | 'guest';

export const CustomerAuthModal: React.FC<Props> = ({ isOpen, onClose, currentCustomer, onUpdateCustomer }) => {
  const [view, setView] = React.useState<View>('login');
  const [email, setEmail] = React.useState('');
  const [name, setName] = React.useState('');
  const [notice, setNotice] = React.useState('');
  if (!isOpen) return null;
  const submit = (event: React.FormEvent) => { event.preventDefault(); setNotice('Please check your email to continue securely.'); };
  const continueGuest = () => { onUpdateCustomer({ id: '', name: 'Guest', email: '', type: 'GUEST', authLevel: 'ANONYMOUS', verified: false }); onClose(); };
  const titles: Record<View, string> = { login: 'Welcome back', register: 'Create your account', forgot: 'Reset your password', guest: 'Continue as a guest' };
  return <div className="fixed inset-0 z-50 grid place-items-center bg-black/55 p-4 backdrop-blur-sm" role="dialog" aria-modal="true" aria-label="Customer account">
    <div className="w-full max-w-md bg-white shadow-2xl">
      <header className="flex items-center justify-between border-b border-neutral-200 px-6 py-5"><div><p className="text-[10px] uppercase tracking-[0.2em] text-neutral-500">NexGen account</p><h2 className="mt-1 font-serif-luxury text-2xl">{titles[view]}</h2></div><button onClick={onClose} aria-label="Close"><X className="h-5 w-5" /></button></header>
      <div className="p-6">
        {currentCustomer.authLevel !== 'ANONYMOUS' && <div className="mb-5 border border-emerald-200 bg-emerald-50 p-4 text-sm"><strong>{currentCustomer.name}</strong><p className="mt-1 text-xs text-neutral-600">Signed in as {currentCustomer.email}</p></div>}
        {view === 'guest' ? <div><p className="text-sm leading-6 text-neutral-600">Browse and add pieces to your bag without an account. Contact and delivery details are collected securely at checkout.</p><button onClick={continueGuest} className="mt-6 w-full bg-black py-3 text-xs font-semibold uppercase tracking-widest text-white">Continue shopping</button></div> : <form onSubmit={submit} className="space-y-4">
          {view === 'register' && <label className="block text-xs font-medium">Full name<input required value={name} onChange={(event) => setName(event.target.value)} autoComplete="name" className="mt-2 w-full border border-neutral-300 px-4 py-3 outline-none focus:border-black" /></label>}
          <label className="block text-xs font-medium">Email address<input required type="email" value={email} onChange={(event) => setEmail(event.target.value)} autoComplete="email" className="mt-2 w-full border border-neutral-300 px-4 py-3 outline-none focus:border-black" /></label>
          {view !== 'forgot' && <label className="block text-xs font-medium">Password<input required type="password" minLength={8} autoComplete={view === 'register' ? 'new-password' : 'current-password'} className="mt-2 w-full border border-neutral-300 px-4 py-3 outline-none focus:border-black" /></label>}
          <button className="flex w-full items-center justify-center gap-2 bg-black py-3 text-xs font-semibold uppercase tracking-widest text-white"><Lock className="h-3.5 w-3.5" />{view === 'forgot' ? 'Send reset link' : view === 'register' ? 'Create account' : 'Sign in'}</button>
          {notice && <p className="text-center text-xs text-emerald-700" role="status">{notice}</p>}
        </form>}
        <div className="mt-6 flex flex-wrap justify-center gap-x-5 gap-y-2 border-t border-neutral-200 pt-5 text-[10px] font-semibold uppercase tracking-wider text-neutral-600">
          {view !== 'login' && <button onClick={() => setView('login')} className="flex items-center gap-1"><ArrowLeft className="h-3 w-3" />Sign in</button>}
          {view === 'login' && <><button onClick={() => setView('register')}><UserRound className="mr-1 inline h-3 w-3" />Register</button><button onClick={() => setView('forgot')}>Forgot password</button><button onClick={() => setView('guest')}>Guest checkout</button></>}
        </div>
      </div>
    </div>
  </div>;
};
