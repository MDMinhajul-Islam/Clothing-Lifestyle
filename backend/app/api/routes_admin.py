"""Minimal authenticated, read-only Commerce MVP operations view."""
import hashlib, hmac, secrets, time
from threading import RLock
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from backend.app.api.deps import get_db
from backend.app.config import settings
from backend.app.repositories.capability_repo import CapabilityRepository

router=APIRouter(prefix="/v1/admin",tags=["Admin Operations"])
_sessions:dict[str,float]={}; _lock=RLock()
SESSION_TTL_SECONDS=1800

class Login(BaseModel): email:str=Field(min_length=3,max_length=254); password:str=Field(min_length=8,max_length=200)

def admin_session(authorization:str|None=Header(None)):
    token=authorization.removeprefix("Bearer ") if authorization else ""
    with _lock:
        expires_at=_sessions.get(token,0)
        if not token or expires_at <= time.time():
            _sessions.pop(token,None)
            raise HTTPException(401,"Admin authentication required.")
    return token

@router.post("/session")
def login(payload:Login):
    digest=hashlib.sha256(payload.password.encode()).hexdigest()
    if not settings.admin_email or not settings.admin_password_hash or not (
        hmac.compare_digest(payload.email.casefold(),settings.admin_email.casefold()) and
        hmac.compare_digest(digest,settings.admin_password_hash)):
        raise HTTPException(401,"Invalid administrator credentials.")
    token=secrets.token_urlsafe(32)
    with _lock:_sessions[token]=time.time()+SESSION_TTL_SECONDS
    return {"access_token":token,"token_type":"bearer","expires_in":SESSION_TTL_SECONDS}

@router.delete("/session")
def logout(token=Depends(admin_session)):
    with _lock:_sessions.discard(token)
    return {"ended":True}

@router.get("/orders")
def orders(limit:int=100,_=Depends(admin_session),conn=Depends(get_db)):
    return {"orders":CapabilityRepository(conn).admin_orders(min(max(limit,1),100))}

@router.get("/support-cases")
def cases(limit:int=100,_=Depends(admin_session),conn=Depends(get_db)):
    return {"cases":CapabilityRepository(conn).admin_cases(min(max(limit,1),100))}
