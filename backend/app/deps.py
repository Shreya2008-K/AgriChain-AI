from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.core.security import decode_token
from app.models import User, AuditEvent

bearer = HTTPBearer(auto_error=False)

def get_current_user(cred: HTTPAuthorizationCredentials = Depends(bearer), db: Session = Depends(get_db)) -> User:
    payload = decode_token(cred.credentials) if cred else None
    if not payload:
        raise HTTPException(401, "Not authenticated")
    user = db.get(User, int(payload["sub"]))
    if not user or not user.is_active:
        raise HTTPException(401, "Account not found or disabled")
    return user

def require_roles(*roles: str):
    def dep(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(403, "Your role is not permitted to perform this action")
        return user
    return dep

def audit(db: Session, actor_id, action, entity, entity_id=None, detail=""):
    db.add(AuditEvent(actor_id=actor_id, action=action, entity=entity, entity_id=entity_id, detail=detail))
