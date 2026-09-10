import React from 'react';
import {
  ArrowLeft, Boxes, CircleDollarSign, ClipboardList, Headphones, LayoutDashboard,
  LogOut, PackageCheck, RefreshCw, RotateCcw, Settings, ShieldCheck, UsersRound,
} from 'lucide-react';
import { adminData, adminLogin, adminLogout, type AdminCase, type AdminOrder } from '../../lib/adminApi';

interface Props { onBackToStorefront: () => void }
type Section = 'dashboard' | 'orders' | 'handoff' | 'inventory' | 'exchanges' | 'refunds' | 'customers' | 'settings';
const navigation = [
  ['dashboard', 'Dashboard', LayoutDashboard], ['orders', 'Recent Orders', ClipboardList],
  ['handoff', 'Human Handoff', Headphones], ['inventory', 'Inventory', Boxes],
  ['exchanges', 'Exchange Requests', RefreshCw], ['refunds', 'Refund Requests', RotateCcw],
  ['customers', 'Customers', UsersRound], ['settings', 'Settings', Settings],
] as const;
const titleCase = (value: string) => value.replaceAll('_', ' ').toLowerCase().replace(/\b\w/g, letter => letter.toUpperCase());
const ADMIN_SESSION_KEY = 'nexgen-admin-session';
const Empty: React.FC<{ text: string }> = ({ text }) => <div className="grid min-h-52 place-items-center rounded-2xl border border-dashed border-neutral-200 bg-neutral-50 text-center"><div><PackageCheck className="mx-auto h-7 w-7 text-neutral-400" /><p className="mt-3 text-sm text-neutral-500">{text}</p></div></div>;

const Orders: React.FC<{ items: AdminOrder[] }> = ({ items }) => items.length ? <div className="overflow-x-auto"><table className="w-full min-w-[900px] text-left text-sm">
  <thead className="border-b border-neutral-200 text-[10px] uppercase tracking-[0.14em] text-neutral-500"><tr>{['Order','Customer','Product','Variant','Size','Qty','Status','Payment','Created'].map(x => <th className="px-4 py-3 font-semibold" key={x}>{x}</th>)}</tr></thead>
  <tbody>{items.map(x => <tr className="border-b border-neutral-100 last:border-0" key={x.order_number+x.variant_id}><td className="px-4 py-4 font-semibold">{x.order_number}</td><td className="px-4 py-4">{x.customer || 'Unavailable'}</td><td className="max-w-xs px-4 py-4">{x.product || 'Information unavailable'}</td><td className="px-4 py-4 font-mono text-[11px] text-neutral-500">{x.variant_id || '-'}</td><td className="px-4 py-4">{x.size || '-'}</td><td className="px-4 py-4">{x.quantity}</td><td className="px-4 py-4">{titleCase(x.order_status)}</td><td className="px-4 py-4"><span className="rounded-full bg-amber-50 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wider text-amber-800">{titleCase(x.payment_status || 'PENDING_PAYMENT')}</span></td><td className="px-4 py-4 text-neutral-500">{new Date(x.created_at).toLocaleString()}</td></tr>)}</tbody>
</table></div> : <Empty text="No orders are available." />;

const Cases: React.FC<{ items: AdminCase[]; empty: string }> = ({ items, empty }) => items.length ? <div className="overflow-x-auto"><table className="w-full min-w-[760px] text-left text-sm">
  <thead className="border-b border-neutral-200 text-[10px] uppercase tracking-[0.14em] text-neutral-500"><tr>{['Case','Customer','Order','Category','Summary','Status','Created'].map(x => <th className="px-4 py-3 font-semibold" key={x}>{x}</th>)}</tr></thead>
  <tbody>{items.map(x => <tr className="border-b border-neutral-100 last:border-0" key={x.case_id}><td className="px-4 py-4 font-medium">{x.case_id}</td><td className="px-4 py-4">{x.customer || 'Unavailable'}</td><td className="px-4 py-4">{x.order_number || '-'}</td><td className="px-4 py-4">{titleCase(x.category)}</td><td className="max-w-xs px-4 py-4 text-neutral-600">{x.summary || 'Information unavailable'}</td><td className="px-4 py-4"><span className="rounded-full bg-neutral-100 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wider">{titleCase(x.status)}</span></td><td className="px-4 py-4 text-neutral-500">{new Date(x.created_at).toLocaleString()}</td></tr>)}</tbody>
</table></div> : <Empty text={empty} />;

export const AdminAccess: React.FC<Props> = ({ onBackToStorefront }) => {
  const [token, setToken] = React.useState(() => window.sessionStorage.getItem(ADMIN_SESSION_KEY) || '');
  const [orders, setOrders] = React.useState<AdminOrder[]>([]);
  const [cases, setCases] = React.useState<AdminCase[]>([]);
  const [section, setSection] = React.useState<Section>('dashboard');
  const [notice, setNotice] = React.useState('');
  const [busy, setBusy] = React.useState(() => Boolean(window.sessionStorage.getItem(ADMIN_SESSION_KEY)));
  const load = React.useCallback(async (next: string) => { const [a,b] = await adminData(next); setOrders(a.orders); setCases(b.cases); }, []);
  // oxlint-disable-next-line react/set-state-in-effect -- validate and restore the existing server-issued session after a hard refresh.
  React.useEffect(() => { if (!token) return; void load(token).catch(() => { window.sessionStorage.removeItem(ADMIN_SESSION_KEY); setToken(''); setNotice('Your secure session has expired. Please sign in again.'); }).finally(() => setBusy(false)); }, [load, token]);
  const submit = async (event: React.FormEvent<HTMLFormElement>) => { event.preventDefault(); setBusy(true); setNotice(''); const form = new FormData(event.currentTarget); try { const next = await adminLogin(String(form.get('email')), String(form.get('password'))); window.sessionStorage.setItem(ADMIN_SESSION_KEY,next); setToken(next); } catch { setNotice('Administrator credentials could not be verified.'); setBusy(false); } };
  const logout = async () => { if (token) await adminLogout(token).catch(() => undefined); window.sessionStorage.removeItem(ADMIN_SESSION_KEY); setToken(''); setOrders([]); setCases([]); setSection('dashboard'); };

  if (!token) return <main className="relative min-h-screen overflow-hidden bg-[#f1efe9] text-neutral-950 lg:grid lg:grid-cols-[1.08fr_0.92fr]">
    <section className="relative hidden min-h-screen overflow-hidden border-r border-black/10 bg-[#d9d4ca] p-12 lg:flex lg:flex-col lg:justify-between xl:p-16">
      <div className="absolute -left-24 top-1/4 h-96 w-96 rounded-full bg-[#b7c5b6]/70 blur-3xl"/><div className="absolute bottom-0 right-0 h-[62%] w-[58%] skew-x-[-8deg] bg-[#b7aa9b]/55"/>
      <button onClick={onBackToStorefront} className="relative z-10 flex w-fit items-center gap-2 rounded-full border border-black/15 bg-white/45 px-4 py-2 text-[10px] font-semibold uppercase tracking-[0.16em] backdrop-blur hover:bg-white/70"><ArrowLeft className="h-3.5 w-3.5" />Return to store</button>
      <div className="relative z-10 max-w-xl"><p className="text-[10px] font-semibold uppercase tracking-[0.28em] text-neutral-600">NexGen commerce operations</p><h1 className="mt-5 font-serif-luxury text-6xl leading-[0.98] xl:text-7xl">Clarity for every customer moment.</h1><p className="mt-7 max-w-md text-sm leading-7 text-neutral-600">A focused workspace for orders, support requests, customer activity, and retail operations.</p></div>
      <div className="relative z-10 grid max-w-xl grid-cols-3 gap-3 text-[10px] font-semibold uppercase tracking-[0.12em] text-neutral-600"><span className="border-t border-black/20 pt-3">Orders</span><span className="border-t border-black/20 pt-3">Support</span><span className="border-t border-black/20 pt-3">Customers</span></div>
    </section>
    <section className="relative flex min-h-screen items-center justify-center p-5 sm:p-10">
      <button onClick={onBackToStorefront} className="absolute left-5 top-5 flex items-center gap-2 rounded-full border border-black/10 bg-white/60 px-4 py-2 text-[10px] uppercase tracking-[0.16em] hover:bg-white lg:hidden"><ArrowLeft className="h-3.5 w-3.5" />Return to store</button>
      <div className="absolute right-[-8rem] top-[-8rem] h-80 w-80 rounded-full bg-white/70 blur-3xl"/>
    <section className="relative w-full max-w-md rounded-3xl border border-black/10 bg-white/90 p-8 text-neutral-950 shadow-[0_30px_100px_rgba(40,35,28,0.14)] backdrop-blur sm:p-10">
      <div className="flex items-center justify-between"><div><p className="font-display text-xl font-bold tracking-[0.25em]">NEXGEN</p><p className="mt-1 text-[9px] uppercase tracking-[0.18em] text-neutral-500">Commerce operations</p></div><div className="grid h-11 w-11 place-items-center rounded-2xl bg-neutral-950 text-white"><ShieldCheck className="h-5 w-5" /></div></div>
      <div className="mt-10"><p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-emerald-700">Secure workspace</p><h1 className="mt-2 font-serif-luxury text-4xl">Welcome back</h1><p className="mt-3 text-sm leading-6 text-neutral-500">Sign in to manage commerce operations and customer support.</p></div>
      <form onSubmit={submit} className="mt-8 space-y-5"><label className="block text-xs font-semibold text-neutral-700">Work email<input name="email" required type="email" autoComplete="username" className="mt-2 w-full rounded-xl border border-neutral-200 bg-neutral-50 px-4 py-3.5 outline-none focus:border-neutral-500 focus:bg-white focus:ring-4 focus:ring-neutral-100" /></label><label className="block text-xs font-semibold text-neutral-700">Password<input name="password" required type="password" autoComplete="current-password" className="mt-2 w-full rounded-xl border border-neutral-200 bg-neutral-50 px-4 py-3.5 outline-none focus:border-neutral-500 focus:bg-white focus:ring-4 focus:ring-neutral-100" /></label><button disabled={busy} className="flex w-full items-center justify-center gap-2 rounded-xl bg-neutral-950 py-3.5 text-xs font-semibold uppercase tracking-[0.14em] text-white disabled:cursor-wait disabled:opacity-60"><ShieldCheck className="h-4 w-4" />{busy ? 'Signing in...' : 'Continue securely'}</button></form>
      {notice && <p className="mt-4 rounded-xl border border-red-100 bg-red-50 p-3 text-center text-xs text-red-700" role="alert">{notice}</p>}<p className="mt-8 text-center text-[10px] text-neutral-400">Authorized NexGen team members only</p>
    </section></section>
  </main>;

  const exchange = cases.filter(x => x.category.toLowerCase().includes('exchange'));
  const refunds = cases.filter(x => x.category.toLowerCase().includes('refund'));
  const handoffs = cases.filter(x => /handoff|human|support/i.test(x.category));
  const customers = Array.from(new Set([...orders.map(x => x.customer), ...cases.map(x => x.customer)].filter(Boolean)));
  const heading = navigation.find(x => x[0] === section)?.[1] || 'Dashboard';
  const metric = (name: string, value: number, icon: React.ReactNode) => <div className="rounded-2xl border border-neutral-200 bg-white p-5 shadow-sm"><div className="flex items-center justify-between"><p className="text-[10px] font-semibold uppercase tracking-[0.15em] text-neutral-500">{name}</p><span className="text-neutral-400">{icon}</span></div><p className="mt-4 text-3xl font-semibold tracking-tight">{value}</p></div>;

  return <main className="min-h-screen bg-[#f5f6f7] text-neutral-950 lg:flex">
    <aside className="border-b border-neutral-800 bg-[#111316] text-white lg:fixed lg:inset-y-0 lg:w-64 lg:border-b-0 lg:border-r"><div className="flex h-20 items-center justify-between px-5 lg:px-6"><button onClick={onBackToStorefront} className="text-left"><span className="font-display text-lg font-bold tracking-[0.23em]">NEXGEN</span><span className="mt-1 block text-[8px] uppercase tracking-[0.18em] text-neutral-500">Operations</span></button><ShieldCheck className="h-5 w-5 text-emerald-400" /></div><nav className="flex gap-1 overflow-x-auto px-3 pb-3 lg:block lg:space-y-1 lg:overflow-visible lg:px-3 lg:pb-0">{navigation.map(([id,name,Icon]) => <button key={id} onClick={() => setSection(id)} className={'flex shrink-0 items-center gap-3 rounded-xl px-3 py-2.5 text-left text-xs transition lg:w-full ' + (section === id ? 'bg-white text-neutral-950 shadow-sm' : 'text-neutral-400 hover:bg-white/5 hover:text-white')}><Icon className="h-4 w-4" /><span>{name}</span></button>)}</nav><div className="hidden border-t border-white/10 p-3 lg:absolute lg:bottom-0 lg:block lg:w-full"><button onClick={() => void logout()} className="flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-xs text-neutral-400 hover:bg-white/5 hover:text-white"><LogOut className="h-4 w-4" />Logout</button></div></aside>
    <section className="min-w-0 flex-1 lg:ml-64"><header className="flex items-center justify-between border-b border-neutral-200 bg-white px-5 py-5 sm:px-8"><div><p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-neutral-400">Commerce workspace</p><h1 className="mt-1 text-2xl font-semibold tracking-tight">{heading}</h1></div><div className="flex items-center gap-2"><button onClick={() => void load(token)} className="rounded-xl border border-neutral-200 p-2.5 text-neutral-600 hover:bg-neutral-50" aria-label="Refresh data"><RefreshCw className="h-4 w-4" /></button><button onClick={() => void logout()} className="rounded-xl border border-neutral-200 p-2.5 text-neutral-600 hover:bg-neutral-50 lg:hidden" aria-label="Logout"><LogOut className="h-4 w-4" /></button></div></header>
      <div className="mx-auto max-w-[1500px] p-5 sm:p-8">
        {section === 'dashboard' && <div className="space-y-7"><div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">{metric('Total orders',orders.length,<ClipboardList className="h-5 w-5" />)}{metric('Pending payment',orders.filter(x => x.payment_status === 'PENDING_PAYMENT').length,<CircleDollarSign className="h-5 w-5" />)}{metric('Open support cases',cases.filter(x => !['RESOLVED','CLOSED'].includes(x.status)).length,<Headphones className="h-5 w-5" />)}{metric('Customers in activity',customers.length,<UsersRound className="h-5 w-5" />)}</div><section className="rounded-2xl border border-neutral-200 bg-white p-5 shadow-sm sm:p-6"><div className="mb-5 flex items-center justify-between"><div><h2 className="text-lg font-semibold">Recent activity</h2><p className="mt-1 text-xs text-neutral-500">Latest order requests from current commerce data.</p></div><button onClick={() => setSection('orders')} className="text-xs font-semibold">View all</button></div><Orders items={orders.slice(0,6)} /></section></div>}
        {section === 'orders' && <section className="rounded-2xl border border-neutral-200 bg-white p-5 shadow-sm"><Orders items={orders} /></section>}
        {section === 'handoff' && <section className="rounded-2xl border border-neutral-200 bg-white p-5 shadow-sm"><Cases items={handoffs} empty="No human handoff requests are available." /></section>}
        {section === 'inventory' && <Empty text="No inventory records are exposed by the current admin API." />}
        {section === 'exchanges' && <section className="rounded-2xl border border-neutral-200 bg-white p-5 shadow-sm"><Cases items={exchange} empty="No exchange requests are available." /></section>}
        {section === 'refunds' && <section className="rounded-2xl border border-neutral-200 bg-white p-5 shadow-sm"><Cases items={refunds} empty="No refund requests are available." /></section>}
        {section === 'customers' && (customers.length ? <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">{customers.map(customer => <article key={customer} className="rounded-2xl border border-neutral-200 bg-white p-5 shadow-sm"><div className="grid h-10 w-10 place-items-center rounded-full bg-neutral-100"><UsersRound className="h-4 w-4" /></div><h2 className="mt-4 font-semibold">{customer}</h2><p className="mt-1 text-xs text-neutral-500">Present in current commerce activity</p></article>)}</div> : <Empty text="No customer activity is available." />)}
        {section === 'settings' && <Empty text="Settings will be available in a future release." />}
      </div>
    </section>
  </main>;
};
