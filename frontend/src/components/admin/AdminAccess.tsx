import React from 'react';
import { ArrowLeft, LockKeyhole, ShieldCheck } from 'lucide-react';
import { adminData, adminLogin, type AdminCase, type AdminOrder } from '../../lib/adminApi';

interface Props { onBackToStorefront: () => void }

export const AdminAccess: React.FC<Props> = ({ onBackToStorefront }) => {
  const [notice, setNotice] = React.useState('');
  const [token,setToken]=React.useState(''); const [orders,setOrders]=React.useState<AdminOrder[]>([]); const [cases,setCases]=React.useState<AdminCase[]>([]);
  const submit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form=new FormData(event.currentTarget);
    try {const next=await adminLogin(String(form.get('email')),String(form.get('password')));setToken(next);const [orderData,caseData]=await adminData(next);setOrders(orderData.orders);setCases(caseData.cases);setNotice('');}
    catch {setNotice('Administrator credentials could not be verified.');}
  };
  if(token)return <main className="min-h-screen bg-neutral-100 p-6 text-neutral-950"><button onClick={onBackToStorefront} className="mb-6 flex items-center gap-2 text-xs"><ArrowLeft className="h-4 w-4"/>Return to store</button><h1 className="font-serif-luxury text-3xl">Operations</h1><section className="mt-8 overflow-x-auto bg-white p-5"><h2 className="mb-4 text-lg">Orders</h2><table className="w-full text-left text-xs"><thead><tr>{['Order','Customer','Product','Variant','Size','Qty','Order status','Payment','Created'].map(x=><th className="p-2" key={x}>{x}</th>)}</tr></thead><tbody>{orders.map(x=><tr className="border-t" key={x.order_number}><td className="p-2">{x.order_number}</td><td>{x.customer}</td><td>{x.product}</td><td>{x.variant_id}</td><td>{x.size||'—'}</td><td>{x.quantity}</td><td>{x.order_status}</td><td>{x.payment_status}</td><td>{new Date(x.created_at).toLocaleString()}</td></tr>)}</tbody></table></section><section className="mt-6 overflow-x-auto bg-white p-5"><h2 className="mb-4 text-lg">Support cases</h2><table className="w-full text-left text-xs"><thead><tr>{['Case','Customer','Order','Category','Summary','Status','Created'].map(x=><th className="p-2" key={x}>{x}</th>)}</tr></thead><tbody>{cases.map(x=><tr className="border-t" key={x.case_id}><td className="p-2">{x.case_id}</td><td>{x.customer}</td><td>{x.order_number||'—'}</td><td>{x.category}</td><td>{x.summary}</td><td>{x.status}</td><td>{new Date(x.created_at).toLocaleString()}</td></tr>)}</tbody></table></section></main>;
  return <main className="grid min-h-screen place-items-center bg-neutral-950 p-5 text-white">
    <section className="w-full max-w-md border border-white/15 bg-white p-8 text-neutral-950 shadow-2xl">
      <button onClick={onBackToStorefront} className="mb-8 flex items-center gap-2 text-[10px] uppercase tracking-widest text-neutral-500"><ArrowLeft className="h-3.5 w-3.5" />Return to store</button>
      <ShieldCheck className="h-8 w-8" />
      <p className="mt-6 text-[10px] uppercase tracking-[0.2em] text-neutral-500">Restricted access</p>
      <h1 className="mt-2 font-serif-luxury text-3xl">Administrator sign in</h1>
      <p className="mt-3 text-sm leading-6 text-neutral-600">Operations, customer records, audit logs, and catalogue management are available only to authorized team members.</p>
      <form onSubmit={submit} className="mt-7 space-y-4">
        <label className="block text-xs font-medium">Work email<input name="email" required type="email" autoComplete="username" className="mt-2 w-full border border-neutral-300 px-4 py-3 outline-none focus:border-black" /></label>
        <label className="block text-xs font-medium">Password<input name="password" required type="password" autoComplete="current-password" className="mt-2 w-full border border-neutral-300 px-4 py-3 outline-none focus:border-black" /></label>
        <button className="flex w-full items-center justify-center gap-2 bg-black py-3 text-xs font-semibold uppercase tracking-widest text-white"><LockKeyhole className="h-3.5 w-3.5" />Continue securely</button>
      </form>
      {notice && <p className="mt-4 border border-amber-200 bg-amber-50 p-3 text-xs text-amber-900" role="alert">{notice}</p>}
    </section>
  </main>;
};
