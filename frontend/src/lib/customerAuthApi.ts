import type { CustomerProfile } from '../types/auth';

const BASE=(import.meta.env.VITE_BACKEND_API_URL||'').replace(/\/$/,'');
const call=async(path:string,init?:RequestInit)=>{
  const response=await fetch(`${BASE}/v1/customer/auth${path}`,{...init,credentials:'include',headers:{'Content-Type':'application/json',...init?.headers}});
  const body=await response.json().catch(()=>({}));
  if(!response.ok)throw new Error(body.detail||'Customer account request failed.');
  return body;
};
export type PortalAccount=CustomerProfile&{addresses:Array<Record<string,unknown>>;orders:Array<Record<string,unknown>>};
export const customerAuthTokensFromFragment=(fragment:string)=>{
  if(!fragment.startsWith('#'))return {verify:null,reset:null};
  const params=new URLSearchParams(fragment.replace(/^#/,''));
  return {verify:params.get('verify_token'),reset:params.get('reset_token')};
};
const mapProfile=(data:Record<string,unknown>):PortalAccount=>({
  id:String(data.customer_id||''),name:`${data.first_name||''} ${data.last_name||''}`.trim(),
  email:String(data.email||''),phone:data.phone?String(data.phone):undefined,type:'REGISTERED',
  authLevel:'LOGGED_IN',verified:true,addresses:(data.addresses||[]) as Array<Record<string,unknown>>,
  orders:(data.orders||[]) as Array<Record<string,unknown>>,
});
export const customerSignup=(data:{first_name:string;last_name:string;email:string;password:string;phone?:string})=>call('/signup',{method:'POST',body:JSON.stringify(data)});
export const customerLogin=async(email:string,password:string)=>{await call('/session',{method:'POST',body:JSON.stringify({email,password})});return customerMe();};
export const customerMe=async()=>mapProfile(await call('/me'));
export const customerLogout=()=>call('/session',{method:'DELETE'});
export const verifyCustomerEmail=(token:string)=>call('/verify-email',{method:'POST',body:JSON.stringify({token})});
export const forgotCustomerPassword=(email:string)=>call('/forgot-password',{method:'POST',body:JSON.stringify({email})});
export const resetCustomerPassword=(token:string,password:string)=>call('/reset-password',{method:'POST',body:JSON.stringify({token,password})});
export const trackCustomerOrder=(orderNumber:string)=>call(`/orders/${encodeURIComponent(orderNumber)}/tracking`);
