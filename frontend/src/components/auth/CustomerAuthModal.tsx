import React from 'react';
import {
  ArrowLeft, CheckCircle2, CreditCard, Home, Lock, LogOut, MapPin, Package,
  RefreshCw, RotateCcw, Search, UserRound, X,
} from 'lucide-react';
import {
  customerLogin, customerLogout, customerSignup, forgotCustomerPassword,
  resendCustomerVerification, resetCustomerPassword, trackCustomerOrder,
} from '../../lib/customerAuthApi';
import type { CustomerProfile } from '../../types/auth';

interface Props { isOpen:boolean; onClose:()=>void; currentCustomer:CustomerProfile; onUpdateCustomer:(customer:CustomerProfile)=>void; resetToken?:string|null; initialNotice?:string|null }
type View='login'|'register'|'forgot'|'verify'|'guest'|'reset';
type PortalSection='profile'|'addresses'|'orders'|'tracking'|'exchanges'|'refunds';
const GUEST:CustomerProfile={id:'',name:'Guest',email:'',type:'GUEST',authLevel:'ANONYMOUS',verified:false};
const portalNav=[
  ['profile','My Profile',UserRound],['addresses','Saved Addresses',MapPin],['orders','My Orders',Package],
  ['tracking','Order Tracking',Search],['exchanges','Exchange Requests',RefreshCw],['refunds','Refund Requests',RotateCcw],
] as const;
const text=(value:unknown,fallback='Information unavailable')=>value===null||value===undefined||value===''?fallback:String(value);
const titleCase=(value:unknown)=>text(value).replaceAll('_',' ').toLowerCase().replace(/\b\w/g,letter=>letter.toUpperCase());

export const CustomerAuthModal:React.FC<Props>=({isOpen,onClose,currentCustomer,onUpdateCustomer,resetToken,initialNotice})=>{
  const [view,setView]=React.useState<View>(resetToken?'reset':'login');
  const [portalSection,setPortalSection]=React.useState<PortalSection>('profile');
  const [notice,setNotice]=React.useState('');
  const [error,setError]=React.useState('');
  const [busy,setBusy]=React.useState(false);
  const [verificationEmail,setVerificationEmail]=React.useState('');
  const [tracking,setTracking]=React.useState<Record<string,unknown>|null>(null);
  if(!isOpen)return null;

  const submit=async(event:React.FormEvent<HTMLFormElement>)=>{
    event.preventDefault();setBusy(true);setNotice('');setError('');const form=new FormData(event.currentTarget);
    const email=String(form.get('email')||'');const password=String(form.get('password')||'');
    try{
      if(view==='register'){
        const names=String(form.get('name')||'').trim().split(/\s+/);setVerificationEmail(email);
        await customerSignup({first_name:names.shift()||'',last_name:names.join(' ')||'Customer',email,password,phone:String(form.get('phone')||'')||undefined});
        setNotice('Check your inbox for your verification link.');setView('verify');
      }else if(view==='verify'){
        await resendCustomerVerification(email);setVerificationEmail(email);setNotice('If the account is eligible, a verification email has been sent.');
      }else if(view==='forgot'){
        await forgotCustomerPassword(email);setNotice('If the account is eligible, a reset link has been sent.');
      }else if(view==='reset'){
        if(!resetToken)throw new Error('The reset link is unavailable.');
        await resetCustomerPassword(resetToken,password);setNotice('Your password has been reset. You can now sign in.');setView('login');window.history.replaceState({},'',window.location.pathname);
      }else{
        const profile=await customerLogin(email,password);onUpdateCustomer(profile);setPortalSection('profile');setNotice('Signed in securely.');
      }
    }catch(reason){
      const message=reason instanceof Error?reason.message:'The account request could not be completed.';
      if(view==='register'&&message.toLowerCase().includes('account was created'))setView('verify');
      setError(message);
    }finally{setBusy(false);}
  };
  const logout=async()=>{await customerLogout().catch(()=>undefined);onUpdateCustomer(GUEST);setView('login');setPortalSection('profile');setNotice('Signed out.');};
  const track=async(event:React.FormEvent<HTMLFormElement>)=>{event.preventDefault();setBusy(true);setError('');const number=String(new FormData(event.currentTarget).get('order_number')||'');try{setTracking(await trackCustomerOrder(number));}catch(reason){setError(reason instanceof Error?reason.message:'Tracking is unavailable.');}finally{setBusy(false);}};
  const titles:Record<View,string>={login:'Welcome back',register:'Create your account',forgot:'Reset your password',verify:'Verify your email',guest:'Continue as a guest',reset:'Choose a new password'};

  if(currentCustomer.verified){
    const orders=currentCustomer.orders||[];const addresses=currentCustomer.addresses||[];
    return <main className="min-h-screen bg-[#f2f1ed] text-neutral-950" aria-label="Customer account">
      <div className="flex min-h-screen w-full flex-col overflow-hidden bg-[#f7f7f5] md:flex-row">
        <aside className="bg-[#151719] p-5 text-white md:sticky md:top-0 md:h-screen md:w-72 md:shrink-0 md:p-7">
          <div className="flex items-center justify-between"><div><p className="font-display text-xl font-bold tracking-[0.24em]">NEXGEN</p><p className="mt-1 text-[8px] uppercase tracking-[0.18em] text-neutral-500">Customer account</p></div><button onClick={onClose} className="rounded-full p-2 hover:bg-white/10 md:hidden" aria-label="Return to store"><X className="h-4 w-4"/></button></div>
          <div className="mt-7 flex items-center gap-3 rounded-2xl bg-white/5 p-3"><div className="grid h-10 w-10 place-items-center rounded-full bg-white text-sm font-semibold text-black">{currentCustomer.name.charAt(0).toUpperCase()}</div><div className="min-w-0"><p className="truncate text-sm font-medium">{currentCustomer.name}</p><p className="truncate text-[10px] text-neutral-400">{currentCustomer.email}</p></div></div>
          <nav className="mt-5 flex gap-1 overflow-x-auto pb-1 md:block md:space-y-1 md:overflow-visible">{portalNav.map(([id,label,Icon])=><button key={id} onClick={()=>setPortalSection(id)} className={'flex shrink-0 items-center gap-3 rounded-xl px-3 py-2.5 text-left text-xs transition md:w-full '+(portalSection===id?'bg-white text-black':'text-neutral-400 hover:bg-white/5 hover:text-white')}><Icon className="h-4 w-4"/>{label}</button>)}</nav>
          <div className="mt-5 space-y-1 md:absolute md:bottom-7 md:left-7 md:right-7"><button onClick={onClose} className="flex items-center gap-3 rounded-xl px-3 py-2.5 text-xs text-neutral-400 hover:bg-white/5 hover:text-white md:w-full"><ArrowLeft className="h-4 w-4"/>Return to store</button><button onClick={()=>void logout()} className="flex items-center gap-3 rounded-xl px-3 py-2.5 text-xs text-neutral-400 hover:bg-white/5 hover:text-white md:w-full"><LogOut className="h-4 w-4"/>Logout</button></div>
        </aside>
        <section className="min-w-0 flex-1">
          <header className="sticky top-0 z-10 flex items-center justify-between border-b border-neutral-200 bg-white/95 px-5 py-5 backdrop-blur sm:px-10 lg:px-14"><div><p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-neutral-400">NexGen account</p><h2 className="mt-1 text-3xl font-semibold">{portalNav.find(([id])=>id===portalSection)?.[1]}</h2></div><button onClick={onClose} className="hidden items-center gap-2 rounded-full border border-neutral-200 px-4 py-2.5 text-[10px] font-semibold uppercase tracking-wider hover:bg-neutral-50 md:flex" aria-label="Return to store"><ArrowLeft className="h-3.5 w-3.5"/>Store</button></header>
          <div className="mx-auto max-w-[1500px] p-5 sm:p-10 lg:p-14">
            {portalSection==='profile'&&<div className="grid gap-4 sm:grid-cols-2"><article className="rounded-2xl border border-neutral-200 bg-white p-5 shadow-sm"><p className="text-[10px] uppercase tracking-wider text-neutral-400">Customer</p><h3 className="mt-3 text-lg font-semibold">{currentCustomer.name}</h3><p className="mt-1 text-sm text-neutral-500">{currentCustomer.email}</p>{currentCustomer.phone&&<p className="mt-1 text-sm text-neutral-500">{currentCustomer.phone}</p>}</article><article className="rounded-2xl border border-emerald-100 bg-emerald-50/60 p-5"><div className="flex items-center gap-2 text-emerald-700"><CheckCircle2 className="h-5 w-5"/><span className="text-xs font-semibold uppercase tracking-wider">Verified account</span></div><p className="mt-3 text-sm leading-6 text-neutral-600">Your secure customer session is active.</p></article></div>}
            {portalSection==='addresses'&&(addresses.length?<div className="grid gap-4 sm:grid-cols-2">{addresses.map((address,index)=><article key={text(address.address_id,String(index))} className="rounded-2xl border border-neutral-200 bg-white p-5 shadow-sm"><div className="flex items-start justify-between"><MapPin className="h-5 w-5 text-neutral-400"/>{Boolean(address.is_default_shipping)&&<span className="rounded-full bg-neutral-100 px-2 py-1 text-[9px] font-semibold uppercase tracking-wider">Default</span>}</div><h3 className="mt-4 font-semibold">{text(address.recipient_name,currentCustomer.name)}</h3><p className="mt-2 text-sm leading-6 text-neutral-500">{text(address.address_line_1)}{address.address_line_2?', '+text(address.address_line_2):''}<br/>{text(address.city)}, {text(address.state)} {text(address.postal_code)}<br/>{text(address.country_code)}</p></article>)}</div>:<EmptyPortal icon={<MapPin className="h-6 w-6"/>} title="No saved addresses" body="Saved shipping addresses will appear here." />)}
            {portalSection==='orders'&&(orders.length?<div className="space-y-4">{orders.map((order,index)=>{const number=text(order.order_number,'Order '+(index+1));const payment=text(order.payment_status,'PENDING_PAYMENT');return <article key={number} className="rounded-2xl border border-neutral-200 bg-white p-5 shadow-sm"><div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-start"><div><p className="text-[10px] font-semibold uppercase tracking-wider text-neutral-400">Order number</p><h3 className="mt-1 font-semibold">{number}</h3><p className="mt-3 text-sm text-neutral-500">Product: {text(order.product)}</p><p className="mt-1 text-xs text-neutral-400">{order.placed_at?new Date(String(order.placed_at)).toLocaleString():'Date unavailable'}</p></div><div className="flex flex-wrap gap-2"><span className="rounded-full bg-neutral-100 px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wider">{titleCase(order.order_status)}</span><span className="rounded-full bg-amber-50 px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wider text-amber-800">{titleCase(payment)}</span></div></div><div className="mt-5 flex flex-wrap items-center justify-between gap-3 border-t border-neutral-100 pt-4"><p className="text-sm font-semibold">{text(order.currency,'USD')} {Number(order.grand_total||0).toFixed(2)}</p><div className="flex gap-2"><button onClick={()=>{setPortalSection('tracking');setTracking(null);}} className="rounded-xl border border-neutral-200 px-4 py-2 text-xs font-semibold">Track order</button>{payment==='PENDING_PAYMENT'&&<button onClick={()=>window.location.assign('/payment?order='+encodeURIComponent(number))} className="flex items-center gap-2 rounded-xl bg-black px-4 py-2 text-xs font-semibold text-white"><CreditCard className="h-3.5 w-3.5"/>Complete Payment</button>}</div></div></article>;})}</div>:<EmptyPortal icon={<Package className="h-6 w-6"/>} title="No orders yet" body="Your orders will appear here after they are received." />)}
            {portalSection==='tracking'&&<div className="max-w-xl"><form onSubmit={track} className="rounded-2xl border border-neutral-200 bg-white p-5 shadow-sm"><label className="block text-xs font-semibold">Order number<input name="order_number" required className="mt-2 w-full rounded-xl border border-neutral-200 bg-neutral-50 px-4 py-3 outline-none focus:border-black"/></label><button disabled={busy} className="mt-4 flex w-full items-center justify-center gap-2 rounded-xl bg-black py-3 text-xs font-semibold uppercase tracking-wider text-white disabled:opacity-50"><Search className="h-4 w-4"/>{busy?'Checking...':'Track order'}</button></form>{tracking&&<article className="mt-4 rounded-2xl border border-emerald-100 bg-emerald-50/70 p-5"><p className="text-[10px] font-semibold uppercase tracking-wider text-emerald-700">{text(tracking.order_number)}</p><h3 className="mt-2 text-lg font-semibold">{titleCase(tracking.shipment_status||tracking.order_status)}</h3><p className="mt-2 text-sm text-neutral-600">{tracking.carrier?'Carrier: '+text(tracking.carrier):'Carrier information unavailable'}</p>{Boolean(tracking.tracking_number)&&<p className="mt-1 text-sm text-neutral-600">Tracking: {text(tracking.tracking_number)}</p>}</article>}{error&&<p className="mt-4 rounded-xl bg-red-50 p-3 text-xs text-red-700">{error}</p>}</div>}
            {portalSection==='exchanges'&&<EmptyPortal icon={<RefreshCw className="h-6 w-6"/>} title="No exchange requests available" body="Existing exchange request history is not provided by the current customer portal API." />}
            {portalSection==='refunds'&&<EmptyPortal icon={<RotateCcw className="h-6 w-6"/>} title="No refund requests available" body="Existing refund request history is not provided by the current customer portal API." />}
          </div>
        </section>
      </div>
    </main>;
  }

  return <div className="fixed inset-0 z-50 grid place-items-center bg-black/60 p-4 backdrop-blur-sm" role="dialog" aria-modal="true" aria-label="Customer account">
    <div className="max-h-[92vh] w-full max-w-lg overflow-y-auto rounded-3xl bg-white shadow-[0_30px_100px_rgba(0,0,0,0.35)]">
      <header className="flex items-center justify-between border-b border-neutral-100 px-6 py-6 sm:px-8"><div><p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-neutral-400">NexGen account</p><h2 className="mt-1 font-serif-luxury text-3xl">{titles[view]}</h2></div><button onClick={onClose} className="rounded-full border border-neutral-200 p-2.5 hover:bg-neutral-50" aria-label="Close"><X className="h-4 w-4"/></button></header>
      <div className="p-6 sm:p-8">
        {view==='guest'?<div><div className="grid h-12 w-12 place-items-center rounded-2xl bg-neutral-100"><Home className="h-5 w-5"/></div><p className="mt-5 text-sm leading-6 text-neutral-600">Browse and add pieces to your bag without an account. Contact and delivery details are collected securely at checkout.</p><button onClick={()=>{onUpdateCustomer(GUEST);onClose();}} className="mt-6 w-full rounded-xl bg-black py-3.5 text-xs font-semibold uppercase tracking-widest text-white">Continue shopping</button></div>
        :<form onSubmit={submit} className="space-y-5">
          {view==='register'&&<><label className="block text-xs font-semibold text-neutral-700">Full name<input name="name" required autoComplete="name" className="mt-2 w-full rounded-xl border border-neutral-200 bg-neutral-50 px-4 py-3.5 outline-none focus:border-black focus:bg-white"/></label><label className="block text-xs font-semibold text-neutral-700">Phone, optional<input name="phone" autoComplete="tel" className="mt-2 w-full rounded-xl border border-neutral-200 bg-neutral-50 px-4 py-3.5 outline-none focus:border-black focus:bg-white"/></label></>}
          {view!=='reset'&&<label className="block text-xs font-semibold text-neutral-700">Email address<input name="email" required type="email" defaultValue={view==='verify'?verificationEmail:''} autoComplete="email" className="mt-2 w-full rounded-xl border border-neutral-200 bg-neutral-50 px-4 py-3.5 outline-none focus:border-black focus:bg-white"/></label>}
          {view!=='forgot'&&view!=='verify'&&<label className="block text-xs font-semibold text-neutral-700">Password<input name="password" required type="password" minLength={10} autoComplete={view==='login'?'current-password':'new-password'} className="mt-2 w-full rounded-xl border border-neutral-200 bg-neutral-50 px-4 py-3.5 outline-none focus:border-black focus:bg-white"/></label>}
          <button disabled={busy} className="flex w-full items-center justify-center gap-2 rounded-xl bg-black py-3.5 text-xs font-semibold uppercase tracking-widest text-white disabled:opacity-50"><Lock className="h-3.5 w-3.5"/>{busy?'Please wait':view==='forgot'?'Send reset link':view==='verify'?'Resend verification email':view==='reset'?'Reset password':view==='register'?'Create account':'Sign in'}</button>
          {(notice||initialNotice)&&<p className="rounded-xl bg-emerald-50 p-3 text-center text-xs text-emerald-700" role="status">{notice||initialNotice}</p>}{error&&<p className="rounded-xl bg-red-50 p-3 text-center text-xs text-red-700" role="alert">{error}</p>}
        </form>}
        <div className="mt-7 flex flex-wrap justify-center gap-x-5 gap-y-3 border-t border-neutral-100 pt-6 text-[10px] font-semibold uppercase tracking-wider text-neutral-500">{view!=='login'&&<button onClick={()=>setView('login')} className="flex items-center gap-1"><ArrowLeft className="h-3 w-3"/>Sign in</button>}{view==='login'&&<><button onClick={()=>setView('register')}><UserRound className="mr-1 inline h-3 w-3"/>Create account</button><button onClick={()=>setView('verify')}>Verify email</button><button onClick={()=>setView('forgot')}>Forgot password</button><button onClick={()=>setView('guest')}>Guest checkout</button></>}</div>
      </div>
    </div>
  </div>;
};

const EmptyPortal:React.FC<{icon:React.ReactNode;title:string;body:string}>=({icon,title,body})=><div className="grid min-h-64 place-items-center rounded-2xl border border-dashed border-neutral-200 bg-white text-center"><div className="max-w-sm p-6"><div className="mx-auto grid h-12 w-12 place-items-center rounded-2xl bg-neutral-100 text-neutral-500">{icon}</div><h3 className="mt-4 font-semibold">{title}</h3><p className="mt-2 text-sm leading-6 text-neutral-500">{body}</p></div></div>;
