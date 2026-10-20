from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.core.db import get_db
from app.core.security import hash_password, verify_password, create_token
from app.deps import get_current_user, audit
from app.models import User
from app.schemas import RegisterIn, LoginIn, TokenOut, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register", response_model=TokenOut, status_code=201)
def register(body: RegisterIn, db: Session = Depends(get_db)):
    if body.role == "admin":
        raise HTTPException(403, "Administrator accounts cannot be self-registered")
    email = body.email.lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(409, "Email already registered")
    u = User(email=email, name=body.name.strip(), role=body.role, password_hash=hash_password(body.password))
    db.add(u); db.flush()
    audit(db, u.id, "register", "user", u.id, body.role)
    db.commit()
    return TokenOut(access_token=create_token(u.id, u.role), user=UserOut.model_validate(u))

@router.post("/login", response_model=TokenOut)
def login(body: LoginIn, db: Session = Depends(get_db)):
    u = db.scalar(select(User).where(User.email == body.email.lower()))
    if not u or not verify_password(body.password, u.password_hash):
        raise HTTPException(401, "Invalid email or password")
    if not u.is_active:
        raise HTTPException(403, "Account is disabled")
    audit(db, u.id, "login", "user", u.id); db.commit()
    return TokenOut(access_token=create_token(u.id, u.role), user=UserOut.model_validate(u))

@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user

@router.post("/logout")
def logout(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Tokens are stateless: the client must discard its token. This records the event.
    audit(db, user.id, "logout", "user", user.id); db.commit()
    return {"message": "Logged out. Discard the token on the client."}
