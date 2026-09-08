import React from 'react';
import { ArrowLeft, LockKeyhole, ShieldCheck } from 'lucide-react';

interface Props { onBackToStorefront: () => void }

export const AdminAccess: React.FC<Props> = ({ onBackToStorefront }) => {
  const [notice, setNotice] = React.useState('');
  const submit = (event: React.FormEvent) => {
    event.preventDefault();
    setNotice('Administrator access requires a verified organization account.');
  };
  return <main className="grid min-h-screen place-items-center bg-neutral-950 p-5 text-white">
    <section className="w-full max-w-md border border-white/15 bg-white p-8 text-neutral-950 shadow-2xl">
      <button onClick={onBackToStorefront} className="mb-8 flex items-center gap-2 text-[10px] uppercase tracking-widest text-neutral-500"><ArrowLeft className="h-3.5 w-3.5" />Return to store</button>
      <ShieldCheck className="h-8 w-8" />
      <p className="mt-6 text-[10px] uppercase tracking-[0.2em] text-neutral-500">Restricted access</p>
      <h1 className="mt-2 font-serif-luxury text-3xl">Administrator sign in</h1>
      <p className="mt-3 text-sm leading-6 text-neutral-600">Operations, customer records, audit logs, and catalogue management are available only to authorized team members.</p>
      <form onSubmit={submit} className="mt-7 space-y-4">
        <label className="block text-xs font-medium">Work email<input required type="email" autoComplete="username" className="mt-2 w-full border border-neutral-300 px-4 py-3 outline-none focus:border-black" /></label>
        <label className="block text-xs font-medium">Password<input required type="password" autoComplete="current-password" className="mt-2 w-full border border-neutral-300 px-4 py-3 outline-none focus:border-black" /></label>
        <button className="flex w-full items-center justify-center gap-2 bg-black py-3 text-xs font-semibold uppercase tracking-widest text-white"><LockKeyhole className="h-3.5 w-3.5" />Continue securely</button>
      </form>
      {notice && <p className="mt-4 border border-amber-200 bg-amber-50 p-3 text-xs text-amber-900" role="alert">{notice}</p>}
    </section>
  </main>;
};
