import { afterEach, describe, expect, it, vi } from 'vitest';
import { customerAuthTokensFromFragment, customerLogin, customerMe } from './customerAuthApi';

describe('customer portal API',()=>{
  afterEach(()=>vi.unstubAllGlobals());
  it('uses HTTP-only cookie credentials for login and profile',async()=>{
    const fetchMock=vi.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify({authenticated:true}),{status:200,headers:{'Content-Type':'application/json'}}))
      .mockResolvedValueOnce(new Response(JSON.stringify({customer_id:'customer-1',first_name:'Jess',last_name:'Carter',email:'jess@example.test',addresses:[],orders:[]}),{status:200,headers:{'Content-Type':'application/json'}}));
    vi.stubGlobal('fetch',fetchMock);
    const profile=await customerLogin('jess@example.test','NexGen@12345');
    expect(profile.id).toBe('customer-1');expect(profile.verified).toBe(true);
    expect(fetchMock.mock.calls.every((call)=>call[1].credentials==='include')).toBe(true);
  });
  it('rejects an expired portal session',async()=>{
    vi.stubGlobal('fetch',vi.fn().mockResolvedValue(new Response(JSON.stringify({detail:'Customer authentication required.'}),{status:401,headers:{'Content-Type':'application/json'}})));
    await expect(customerMe()).rejects.toThrow('Customer authentication required.');
  });
  it('accepts auth tokens only from the URL fragment',()=>{
    expect(customerAuthTokensFromFragment('#reset_token=opaque-reset')).toEqual({verify:null,reset:'opaque-reset'});
    expect(customerAuthTokensFromFragment('?reset_token=query-token')).toEqual({verify:null,reset:null});
  });
});
