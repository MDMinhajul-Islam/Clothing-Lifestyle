const BASE=(import.meta.env.VITE_BACKEND_API_URL||'').replace(/\/$/,'');
export type AdminOrder={order_number:string;customer:string;product:string;variant_id:string;size?:string;quantity:number;order_status:string;payment_status:string;created_at:string};
export type AdminCase={case_id:string;customer:string;order_number?:string;category:string;summary:string;status:string;created_at:string};
const call=async(path:string,token:string,init?:RequestInit)=>{const response=await fetch(`${BASE}${path}`,{...init,headers:{'Content-Type':'application/json',Authorization:`Bearer ${token}`,...init?.headers}});if(!response.ok)throw new Error('Admin request failed');return response.json();};
export const adminLogin=async(email:string,password:string)=>(await call('/v1/admin/session','',{method:'POST',body:JSON.stringify({email,password})})).access_token as string;
export const adminData=async(token:string)=>Promise.all([call('/v1/admin/orders',token),call('/v1/admin/support-cases',token)]);
