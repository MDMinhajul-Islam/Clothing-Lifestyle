"""Customer Portal authentication without altering voice verification."""
import hashlib,secrets
from datetime import datetime,timedelta,timezone
from uuid import uuid4
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError,VerificationError
from backend.app.config import settings
from backend.app.repositories.customer_auth_repo import CustomerAuthRepository
from backend.app.schemas.order import TrackOrderInput
from backend.app.services.shipment_service import ShipmentService

class CustomerAuthService:
    def __init__(self,conn,repo=None,hasher=None):
        self.conn=conn; self.repo=repo or CustomerAuthRepository(conn); self.hasher=hasher or PasswordHasher()
    @staticmethod
    def _hash(token): return hashlib.sha256(token.encode()).hexdigest()
    def signup(self,data):
        customer=self.repo.customer_by_email(data.email)
        if self.repo.credentials_by_email(data.email): raise ValueError('An account already exists for this email address.')
        customer_id=customer['customer_id'] if customer else str(uuid4())
        if not customer:self.repo.create_customer(customer_id,data)
        self.repo.create_credentials(customer_id,self.hasher.hash(data.password))
        token=secrets.token_urlsafe(48); expires=datetime.now(timezone.utc)+timedelta(hours=24)
        self.repo.replace_token(customer_id,'VERIFY_EMAIL',self._hash(token),expires); self.conn.commit()
        return customer_id,token
    def verification_token(self,email):
        row=self.repo.credentials_by_email(email)
        if not row or row.get('email_verified_at'): return None
        token=secrets.token_urlsafe(48); expires=datetime.now(timezone.utc)+timedelta(hours=24)
        self.repo.replace_token(row['customer_id'],'VERIFY_EMAIL',self._hash(token),expires); self.conn.commit(); return token
    def verify_email(self,token):
        row=self.repo.consume_token(self._hash(token),'VERIFY_EMAIL')
        if not row: raise ValueError('The verification link is invalid or has expired.')
        self.repo.mark_verified(row['customer_id']); self.conn.commit()
    def login(self,email,password):
        row=self.repo.credentials_by_email(email)
        now=datetime.now(timezone.utc)
        if not row: raise PermissionError('Invalid email or password.')
        locked=row.get('locked_until')
        if locked and locked>now: raise PermissionError('Sign in is temporarily locked. Please try again later.')
        try:self.hasher.verify(row['password_hash'],password)
        except (VerifyMismatchError,VerificationError):
            self.repo.login_failed(row['customer_id'],row.get('failed_login_count',0)>=4); self.conn.commit()
            raise PermissionError('Invalid email or password.')
        if not row.get('email_verified_at'): raise PermissionError('Please verify your email before signing in.')
        if row.get('account_status')!='ACTIVE': raise PermissionError('This account is unavailable.')
        self.repo.login_succeeded(row['customer_id'])
        token=secrets.token_urlsafe(48); expires=now+timedelta(days=settings.customer_session_days)
        self.repo.create_session(self._hash(token),row['customer_id'],expires); self.conn.commit()
        return token,expires
    def forgot_password(self,email):
        row=self.repo.credentials_by_email(str(email).strip().casefold())
        if not row or not row.get('email_verified_at'): return None
        token=secrets.token_urlsafe(48); expires=datetime.now(timezone.utc)+timedelta(minutes=30)
        self.repo.replace_token(row['customer_id'],'RESET_PASSWORD',self._hash(token),expires); self.conn.commit()
        return token,row['email']
    def reset_password(self,token,password):
        row=self.repo.consume_token(self._hash(token),'RESET_PASSWORD')
        if not row: raise ValueError('The reset link is invalid or has expired.')
        self.repo.reset_password(row['customer_id'],self.hasher.hash(password)); self.conn.commit()
    def profile(self,token):
        row=self.repo.session_customer(self._hash(token))
        if not row: raise PermissionError('Customer session is invalid or expired.')
        row['addresses']=self.repo.addresses(row['customer_id']); row['orders']=self.repo.orders(row['customer_id'])
        self.conn.commit(); return row
    def track_order(self,token,order_number):
        row=self.repo.session_customer(self._hash(token))
        if not row or not self.repo.owns_order(row['customer_id'],order_number):
            raise PermissionError('That order is unavailable for this customer session.')
        self.conn.commit()
        return ShipmentService(self.conn).track_order(TrackOrderInput(order_number=order_number))
    def logout(self,token): self.repo.revoke_session(self._hash(token)); self.conn.commit()
