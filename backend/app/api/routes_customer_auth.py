"""Browser-safe Customer Portal authentication endpoints."""
from html import escape
from urllib.parse import quote
from fastapi import APIRouter,Depends,HTTPException,Request,Response
from backend.app.api.deps import get_db
from backend.app.config import settings
from backend.app.notifications.email import EmailMessage,SmtpEmailProvider
from backend.app.schemas.customer_auth import (
    SignupInput,LoginInput,TokenInput,ForgotPasswordInput,ResetPasswordInput,
    StatusResponse,VerificationResponse,SessionResponse,LogoutResponse,
    PasswordResetResponse,PortalProfile,
)
from backend.app.schemas.order import TrackOrderOutput
from backend.app.services.customer_auth_service import CustomerAuthService

router=APIRouter(prefix='/v1/customer/auth',tags=['Customer Portal'])

def _cookie(response,token,expires):
    response.set_cookie(settings.customer_session_cookie,token,httponly=True,
        secure=settings.environment.casefold()=='production',samesite='lax',path='/',
        max_age=max(0,int((expires.timestamp()-__import__('time').time()))))

def _portal_link(name,token):
    return f"{settings.customer_portal_url.rstrip('/')}#{name}={quote(token)}"

def _send(recipient,subject,message,label,url):
    safe_url=escape(url,quote=True)
    SmtpEmailProvider().send(EmailMessage(recipient=recipient,subject=subject,
        text=f"NexGen\n\n{message}\n\n{label}: {url}",
        html=("<!doctype html><html><body><main style='max-width:640px;margin:auto;font-family:Arial,sans-serif'>"
              "<p style='letter-spacing:.25em;font-weight:700'>NEXGEN</p>"
              f"<p>{escape(message)}</p><p><a href='{safe_url}' style='display:inline-block;background:#111;color:#fff;"
              f"padding:14px 22px;text-decoration:none'>{escape(label)}</a></p></main></body></html>")))

@router.post('/signup',status_code=202,response_model=StatusResponse)
def signup(payload:SignupInput,conn=Depends(get_db)):
    service=CustomerAuthService(conn)
    try:_,token=service.signup(payload)
    except ValueError as exc: raise HTTPException(409,str(exc))
    url=_portal_link('verify_token',token)
    try:_send(payload.email,'Verify your NexGen account','Please verify your email to activate your account.','Verify Email',url)
    except Exception: raise HTTPException(503,'Your account was created, but the verification email could not be sent. Please request another email.')
    return {'status':'VERIFICATION_REQUIRED'}

@router.post('/resend-verification',status_code=202,response_model=StatusResponse)
def resend(payload:ForgotPasswordInput,conn=Depends(get_db)):
    service=CustomerAuthService(conn); token=service.verification_token(payload.email)
    if token:
        url=_portal_link('verify_token',token)
        try:_send(payload.email,'Verify your NexGen account','Please verify your email to activate your account.','Verify Email',url)
        except Exception: pass
    return {'status':'IF_ELIGIBLE_EMAIL_SENT'}

@router.post('/verify-email',response_model=VerificationResponse)
def verify_email(payload:TokenInput,conn=Depends(get_db)):
    try:CustomerAuthService(conn).verify_email(payload.token)
    except ValueError as exc: raise HTTPException(400,str(exc))
    return {'verified':True}

@router.post('/session',response_model=SessionResponse)
def login(payload:LoginInput,response:Response,conn=Depends(get_db)):
    try:token,expires=CustomerAuthService(conn).login(payload.email,payload.password)
    except PermissionError as exc: raise HTTPException(401,str(exc))
    _cookie(response,token,expires)
    return {'authenticated':True,'expires_at':expires.isoformat()}

@router.delete('/session',response_model=LogoutResponse)
def logout(request:Request,response:Response,conn=Depends(get_db)):
    token=request.cookies.get(settings.customer_session_cookie)
    if token:CustomerAuthService(conn).logout(token)
    response.delete_cookie(settings.customer_session_cookie,path='/',samesite='lax',
                           secure=settings.environment.casefold()=='production',httponly=True)
    return {'ended':True}

@router.get('/me',response_model=PortalProfile)
def me(request:Request,conn=Depends(get_db)):
    token=request.cookies.get(settings.customer_session_cookie)
    if not token:raise HTTPException(401,'Customer authentication required.')
    try:return CustomerAuthService(conn).profile(token)
    except PermissionError as exc:raise HTTPException(401,str(exc))

@router.get('/orders/{order_number}/tracking',response_model=TrackOrderOutput)
def tracking(order_number:str,request:Request,conn=Depends(get_db)):
    token=request.cookies.get(settings.customer_session_cookie)
    if not token:raise HTTPException(401,'Customer authentication required.')
    try:return CustomerAuthService(conn).track_order(token,order_number)
    except PermissionError as exc:raise HTTPException(403,str(exc))
    except ValueError as exc:raise HTTPException(404,str(exc))

@router.post('/forgot-password',status_code=202,response_model=StatusResponse)
def forgot(payload:ForgotPasswordInput,conn=Depends(get_db)):
    result=CustomerAuthService(conn).forgot_password(payload.email)
    if result:
        token,recipient=result; url=_portal_link('reset_token',token)
        try:_send(recipient,'Reset your NexGen password','Use this secure link to choose a new password.','Reset Password',url)
        except Exception:pass
    return {'status':'IF_ELIGIBLE_EMAIL_SENT'}

@router.post('/reset-password',response_model=PasswordResetResponse)
def reset(payload:ResetPasswordInput,conn=Depends(get_db)):
    try:CustomerAuthService(conn).reset_password(payload.token,payload.password)
    except ValueError as exc:raise HTTPException(400,str(exc))
    return {'password_reset':True}
