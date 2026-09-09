import hashlib
import unittest
from datetime import datetime,timezone
from types import SimpleNamespace
from argon2 import PasswordHasher
from backend.app.schemas.customer_auth import SignupInput
from backend.app.services.customer_auth_service import CustomerAuthService
from backend.app.api.routes_customer_auth import _cookie,_portal_link,router as customer_auth_router
from backend.app.schemas.customer_auth import PortalProfile
from fastapi import Response
from fastapi.routing import APIRoute

class FakeConn:
    def __init__(self):self.commits=0
    def commit(self):self.commits+=1

class FakeRepo:
    def __init__(self,existing=False,verified=False):
        self.customer={'customer_id':'customer-1','first_name':'Jess','last_name':'Carter','email':'jess@example.test','phone':None} if existing else None
        self.credential=None;self.tokens={};self.sessions={};self.created_customers=0;self.address_rows=[];self.order_rows=[]
        if existing and verified:self.credential={**self.customer,'account_status':'ACTIVE','password_hash':PasswordHasher().hash('NexGen@12345'),'email_verified_at':datetime.now(timezone.utc),'failed_login_count':0,'locked_until':None}
    def customer_by_email(self,email):return self.customer if self.customer and self.customer['email']==email else None
    def credentials_by_email(self,email):return self.credential if self.credential and self.credential['email']==email else None
    def create_customer(self,customer_id,data):
        self.created_customers+=1;self.customer={'customer_id':customer_id,'first_name':data.first_name,'last_name':data.last_name,'email':data.email,'phone':data.phone}
    def create_credentials(self,customer_id,password_hash):
        self.credential={**self.customer,'account_status':'ACTIVE','password_hash':password_hash,'email_verified_at':None,'failed_login_count':0,'locked_until':None}
    def replace_token(self,customer_id,purpose,token_hash,expires_at):self.tokens[(token_hash,purpose)]={'customer_id':customer_id,'expires_at':expires_at}
    def consume_token(self,token_hash,purpose):return self.tokens.pop((token_hash,purpose),None)
    def mark_verified(self,customer_id):self.credential['email_verified_at']=datetime.now(timezone.utc)
    def login_failed(self,customer_id,locked):self.credential['failed_login_count']+=1
    def login_succeeded(self,customer_id):self.credential['failed_login_count']=0
    def create_session(self,token_hash,customer_id,expires_at):self.sessions[token_hash]={'customer_id':customer_id,'expires_at':expires_at}
    def session_customer(self,token_hash):return self.customer if token_hash in self.sessions else None
    def revoke_session(self,token_hash):self.sessions.pop(token_hash,None)
    def reset_password(self,customer_id,password_hash):self.credential['password_hash']=password_hash;self.sessions.clear()
    def addresses(self,customer_id):return self.address_rows
    def orders(self,customer_id):return self.order_rows
    def owns_order(self,customer_id,order_number):return order_number=='NGR-1'

class CustomerAuthTests(unittest.TestCase):
    def signup_data(self,email='jess@example.test'):return SignupInput(first_name='Jess',last_name='Carter',email=email,password='NexGen@12345')
    def test_signup_reuses_existing_customer_profile(self):
        repo=FakeRepo(existing=True);service=CustomerAuthService(FakeConn(),repo=repo)
        customer_id,token=service.signup(self.signup_data())
        self.assertEqual(customer_id,'customer-1');self.assertEqual(repo.created_customers,0)
        self.assertTrue(token);self.assertTrue(repo.credential['password_hash'].startswith('$argon2id$'))
    def test_signup_creates_one_canonical_customer_when_missing(self):
        repo=FakeRepo();service=CustomerAuthService(FakeConn(),repo=repo)
        service.signup(self.signup_data('new@example.test'))
        self.assertEqual(repo.created_customers,1);self.assertEqual(repo.customer['email'],'new@example.test')
    def test_unverified_customer_cannot_login(self):
        repo=FakeRepo(existing=True);service=CustomerAuthService(FakeConn(),repo=repo);service.signup(self.signup_data())
        with self.assertRaisesRegex(PermissionError,'verify your email'):service.login('jess@example.test','NexGen@12345')
    def test_verify_login_profile_and_logout(self):
        repo=FakeRepo(existing=True);conn=FakeConn();service=CustomerAuthService(conn,repo=repo)
        _,verification=service.signup(self.signup_data());service.verify_email(verification)
        token,_=service.login('jess@example.test','NexGen@12345');profile=service.profile(token)
        self.assertEqual(profile['customer_id'],'customer-1');self.assertIn(hashlib.sha256(token.encode()).hexdigest(),repo.sessions)
        service.logout(token);self.assertEqual(repo.sessions,{})
    def test_reset_token_is_single_use_and_revokes_sessions(self):
        repo=FakeRepo(existing=True,verified=True);service=CustomerAuthService(FakeConn(),repo=repo)
        session,_=service.login('jess@example.test','NexGen@12345');token,_=service.forgot_password('jess@example.test')
        service.reset_password(token,'A-New-Password@123')
        self.assertEqual(repo.sessions,{})
        with self.assertRaisesRegex(ValueError,'invalid or has expired'):service.reset_password(token,'Another-Password@123')
        service.login('jess@example.test','A-New-Password@123')
    def test_wrong_password_is_rejected(self):
        repo=FakeRepo(existing=True,verified=True);service=CustomerAuthService(FakeConn(),repo=repo)
        with self.assertRaisesRegex(PermissionError,'Invalid email or password'):service.login('jess@example.test','wrong')
    def test_portal_tracking_enforces_order_ownership(self):
        repo=FakeRepo(existing=True,verified=True);service=CustomerAuthService(FakeConn(),repo=repo)
        token,_=service.login('jess@example.test','NexGen@12345')
        with self.assertRaisesRegex(PermissionError,'unavailable for this customer'):
            service.track_order(token,'NGR-OTHER')
    def test_portal_session_cookie_is_http_only(self):
        response=Response();_cookie(response,'opaque-token',datetime.now(timezone.utc).replace(year=datetime.now(timezone.utc).year+1))
        header=response.headers['set-cookie'].lower()
        self.assertIn('httponly',header);self.assertIn('samesite=lax',header)

    def test_every_customer_auth_endpoint_has_an_explicit_response_model(self):
        routes=[route for route in customer_auth_router.routes if isinstance(route,APIRoute)]
        self.assertTrue(routes)
        self.assertTrue(all(route.response_model is not None for route in routes))

    def test_portal_profile_response_excludes_authentication_storage_fields(self):
        profile=PortalProfile.model_validate({
            'customer_id':'customer-1','first_name':'Jess','last_name':'Carter','email':'jess@example.test',
            'password_hash':'forbidden','token_hash':'forbidden','reset_token':'forbidden',
            'addresses':[],'orders':[],
        }).model_dump()
        self.assertFalse({'password_hash','token_hash','reset_token'} & profile.keys())

    def test_email_action_tokens_use_fragments_not_query_parameters(self):
        link=_portal_link('reset_token','opaque-token')
        self.assertIn('#reset_token=opaque-token',link)
        self.assertNotIn('?reset_token=',link)

    def test_auth_response_models_do_not_expose_sensitive_fields(self):
        sensitive={'password','password_hash','token','token_hash','reset_token','verify_token'}
        routes=[route for route in customer_auth_router.routes if isinstance(route,APIRoute)]
        for route in routes:
            fields=set(route.response_model.model_fields)
            self.assertFalse(fields & sensitive,f'{route.path} exposes {fields & sensitive}')

if __name__=='__main__':unittest.main()
