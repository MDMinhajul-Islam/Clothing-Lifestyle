import React from 'react';
import { ArrowLeft, Lock, LogOut, UserRound, X } from 'lucide-react';
import { customerLogin, customerLogout, customerSignup, forgotCustomerPassword, resetCustomerPassword, trackCustomerOrder } from '../../lib/customerAuthApi';
import type { CustomerProfile } from '../../types/auth';

interface Props { isOpen:boolean; onClose:()=>void; currentCustomer:CustomerProfile; onUpdateCustomer:(customer:CustomerProfile)=>void; resetToken?:string|null; initialNotice?:string|null }
type View='login'|'register'|'forgot'|'guest'|'reset';
const GUEST:CustomerProfile={id:'',name:'Guest',email:'',type:'GUEST',authLevel:'ANONYMOUS',verified:false};

export const CustomerAuthModal:React.FC<Props>=({isOpen,onClose,currentCustomer,onUpdateCustomer,resetToken,initialNotice})=>{
  const [view,setView]=React.useState<View>(resetToken?'reset':'login');
  const [notice,setNotice]=React.useState(''); const [error,setError]=React.useState(''); const [busy,setBusy]=React.useState(false);
  const [tracking,setTracking]=React.useState('');
  if(!isOpen)return null;
  const submit=async(event:React.FormEvent<HTMLFormElement>)=>{
    event.preventDefault();setBusy(true);setNotice('');setError('');const form=new FormData(event.currentTarget);
    const email=String(form.get('email')||'');const password=String(form.get('password')||'');
    try{
      if(view==='register'){
        const names=String(form.get('name')||'').trim().split(/\s+/);await customerSignup({first_name:names.shift()||'',last_name:names.join(' ')||'Customer',email,password,phone:String(form.get('phone')||'')||undefined});
        setNotice('Check your email to verify your account before signing in.');setView('login');
      }else if(view==='forgot'){await forgotCustomerPassword(email);setNotice('If the account is eligible, a reset link has been sent.');}
      else if(view==='reset'){if(!resetToken)throw new Error('The reset link is unavailable.');await resetCustomerPassword(resetToken,password);setNotice('Your password has been reset. You can now sign in.');setView('login');window.history.replaceState({},'',window.location.pathname);}
      else{const profile=await customerLogin(email,password);onUpdateCustomer(profile);setNotice('Signed in securely.');}
    }catch(reason){setError(reason instanceof Error?reason.message:'The account request could not be completed.');}finally{setBusy(false);}
  };
  const logout=async()=>{await customerLogout().catch(()=>undefined);onUpdateCustomer(GUEST);setView('login');setNotice('Signed out.');};
  const titles:Record<View,string>={login:'Welcome back',register:'Create your account',forgot:'Reset your password',guest:'Continue as a guest',reset:'Choose a new password'};
  return <div className="fixed inset-0 z-50 grid place-items-center bg-black/55 p-4 backdrop-blur-sm" role="dialog" aria-modal="true" aria-label="Customer account"><div className="max-h-[90vh] w-full max-w-lg overflow-y-auto bg-white shadow-2xl">
    <header className="flex items-center justify-between border-b border-neutral-200 px-6 py-5"><div><p className="text-[10px] uppercase tracking-[0.2em] text-neutral-500">NexGen account</p><h2 className="mt-1 font-serif-luxury text-2xl">{titles[view]}</h2></div><button onClick={onClose} aria-label="Close"><X className="h-5 w-5"/></button></header>
    <div className="p-6">
      {currentCustomer.verified?<div className="space-y-5"><div className="border border-emerald-200 bg-emerald-50 p-4 text-sm"><strong>{currentCustomer.name}</strong><p className="mt-1 text-xs text-neutral-600">{currentCustomer.email}</p></div>
        <section><h3 className="text-xs font-semibold uppercase tracking-wider">Saved addresses</h3>{currentCustomer.addresses?.length?<div className="mt-2 space-y-2">{currentCustomer.addresses.map((address,index)=><p key={String(address.address_id||index)} className="border border-neutral-200 p-3 text-xs">{String(address.address_line_1||'')}, {String(address.city||'')}, {String(address.state||'')} {String(address.postal_code||'')}</p>)}</div>:<p className="mt-2 text-xs text-neutral-500">No saved addresses.</p>}</section>
        <section><h3 className="text-xs font-semibold uppercase tracking-wider">Order history</h3>{currentCustomer.orders?.length?<div className="mt-2 space-y-2">{currentCustomer.orders.map((order,index)=><button onClick={()=>void trackCustomerOrder(String(order.order_number)).then(data=>setTracking(`${data.order_number}: ${data.shipment_status||data.order_status}`)).catch(reason=>setError(reason instanceof Error?reason.message:'Tracking is unavailable.'))} key={String(order.order_number||index)} className="flex w-full justify-between border border-neutral-200 p-3 text-left text-xs"><span>{String(order.order_number||'Order')}</span><span>{String(order.order_status||'')}</span></button>)}</div>:<p className="mt-2 text-xs text-neutral-500">No orders yet.</p>}{tracking&&<p className="mt-2 bg-neutral-100 p-3 text-xs">{tracking}</p>}</section>
        <button onClick={()=>void logout()} className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider"><LogOut className="h-4 w-4"/>Sign out</button></div>
      :view==='guest'?<div><p className="text-sm leading-6 text-neutral-600">Browse and add pieces to your bag without an account. Contact and delivery details are collected securely at checkout.</p><button onClick={()=>{onUpdateCustomer(GUEST);onClose();}} className="mt-6 w-full bg-black py-3 text-xs font-semibold uppercase tracking-widest text-white">Continue shopping</button></div>
      :<form onSubmit={submit} className="space-y-4">
        {view==='register'&&<><label className="block text-xs font-medium">Full name<input name="name" required autoComplete="name" className="mt-2 w-full border border-neutral-300 px-4 py-3 outline-none focus:border-black"/></label><label className="block text-xs font-medium">Phone, optional<input name="phone" autoComplete="tel" className="mt-2 w-full border border-neutral-300 px-4 py-3 outline-none focus:border-black"/></label></>}
        {view!=='reset'&&<label className="block text-xs font-medium">Email address<input name="email" required type="email" autoComplete="email" className="mt-2 w-full border border-neutral-300 px-4 py-3 outline-none focus:border-black"/></label>}
        {view!=='forgot'&&<label className="block text-xs font-medium">Password<input name="password" required type="password" minLength={10} autoComplete={view==='login'?'current-password':'new-password'} className="mt-2 w-full border border-neutral-300 px-4 py-3 outline-none focus:border-black"/></label>}
        <button disabled={busy} className="flex w-full items-center justify-center gap-2 bg-black py-3 text-xs font-semibold uppercase tracking-widest text-white disabled:opacity-50"><Lock className="h-3.5 w-3.5"/>{busy?'Please wait':view==='forgot'?'Send reset link':view==='reset'?'Reset password':view==='register'?'Create account':'Sign in'}</button>
        {(notice||initialNotice)&&<p className="text-center text-xs text-emerald-700" role="status">{notice||initialNotice}</p>}{error&&<p className="text-center text-xs text-red-700" role="alert">{error}</p>}
      </form>}
      {!currentCustomer.verified&&<div className="mt-6 flex flex-wrap justify-center gap-x-5 gap-y-2 border-t border-neutral-200 pt-5 text-[10px] font-semibold uppercase tracking-wider text-neutral-600">{view!=='login'&&<button onClick={()=>setView('login')} className="flex items-center gap-1"><ArrowLeft className="h-3 w-3"/>Sign in</button>}{view==='login'&&<><button onClick={()=>setView('register')}><UserRound className="mr-1 inline h-3 w-3"/>Register</button><button onClick={()=>setView('forgot')}>Forgot password</button><button onClick={()=>setView('guest')}>Guest checkout</button></>}</div>}
    </div></div></div>;
};
