"""Public Customer Portal authentication contracts."""
import re
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field, field_validator

class SignupInput(BaseModel):
    first_name:str=Field(min_length=1,max_length=100)
    last_name:str=Field(min_length=1,max_length=100)
    email:str=Field(min_length=3,max_length=254)
    password:str=Field(min_length=10,max_length=200)
    phone:str|None=Field(None,max_length=40)
    @field_validator('email')
    @classmethod
    def normalize_email(cls,value):
        value=str(value).strip().casefold()
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+",value): raise ValueError('Enter a valid email address.')
        return value

class LoginInput(BaseModel):
    email:str=Field(min_length=3,max_length=254); password:str=Field(min_length=1,max_length=200)
    @field_validator('email')
    @classmethod
    def normalize_email(cls,value): return SignupInput.normalize_email(value)

class TokenInput(BaseModel): token:str=Field(min_length=32,max_length=300)
class ForgotPasswordInput(BaseModel):
    email:str=Field(min_length=3,max_length=254)
    @field_validator('email')
    @classmethod
    def normalize_email(cls,value): return SignupInput.normalize_email(value)
class ResetPasswordInput(TokenInput): password:str=Field(min_length=10,max_length=200)

class StatusResponse(BaseModel):
    status:Literal['VERIFICATION_REQUIRED','IF_ELIGIBLE_EMAIL_SENT']

class VerificationResponse(BaseModel): verified:bool
class SessionResponse(BaseModel): authenticated:bool; expires_at:datetime
class LogoutResponse(BaseModel): ended:bool
class PasswordResetResponse(BaseModel): password_reset:bool

class PortalAddress(BaseModel):
    address_id:str; recipient_name:str; address_line_1:str; address_line_2:str|None=None
    city:str; state:str; postal_code:str; country_code:str; is_default_shipping:bool

class PortalOrder(BaseModel):
    order_number:str; order_status:str; payment_status:str|None=None
    grand_total:float; currency:str; placed_at:datetime|None=None

class PortalProfile(BaseModel):
    customer_id:str; first_name:str; last_name:str; email:str; phone:str|None=None
    city:str|None=None; state:str|None=None; customer_type:str='REGISTERED'
    addresses:list[PortalAddress]=Field(default_factory=list)
    orders:list[PortalOrder]=Field(default_factory=list)
