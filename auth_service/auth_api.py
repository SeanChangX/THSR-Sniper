from fastapi import FastAPI, HTTPException, Depends, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta
from typing import Optional
from pydantic import BaseModel, EmailStr, field_validator
import json
import uvicorn

from database import get_database, User, UserSession, AuditLog, init_database
from security import (
    verify_password, get_password_hash, create_token_pair, verify_token,
    encrypt_sensitive_data, decrypt_sensitive_data, generate_session_token,
    hash_session_token, validate_password_strength, is_account_locked,
    calculate_lockout_time, sanitize_user_input, validate_taiwan_id,
    Token, TokenData
)

# Initialize database
init_database()

# Create FastAPI app
app = FastAPI(
    title="THSR Sniper Auth Service",
    description="Authentication and user management service for THSR Sniper",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000", 
        "http://127.0.0.1:3000",
        "http://localhost:5173",  # Vite dev server
        "http://127.0.0.1:5173"   # Vite dev server
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security scheme
security = HTTPBearer()

# Pydantic models
class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    full_name: Optional[str] = None
    thsr_personal_id: Optional[str] = None
    thsr_use_membership: bool = False
    
    @field_validator('username')
    @classmethod
    def validate_username(cls, v):
        v = sanitize_user_input(v)
        if len(v) < 3 or len(v) > 50:
            raise ValueError("Username must be between 3 and 50 characters")
        if not v.replace('_', '').isalnum():
            raise ValueError("Username can only contain letters, numbers, and underscores")
        return v
    
    @field_validator('password')
    @classmethod
    def validate_password(cls, v):
        is_valid, message = validate_password_strength(v)
        if not is_valid:
            raise ValueError(message)
        return v
    
    @field_validator('thsr_personal_id')
    @classmethod
    def validate_personal_id(cls, v):
        if v and not validate_taiwan_id(v):
            raise ValueError("Invalid Taiwan personal ID format")
        return v


class UserLogin(BaseModel):
    username: str
    password: str
    
    @field_validator('username')
    @classmethod
    def validate_username(cls, v):
        return sanitize_user_input(v)


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    thsr_personal_id: Optional[str] = None
    thsr_use_membership: Optional[bool] = None
    preferences: Optional[dict] = None
    
    @field_validator('thsr_personal_id')
    @classmethod
    def validate_personal_id(cls, v):
        if v and not validate_taiwan_id(v):
            raise ValueError("Invalid Taiwan personal ID format")
        return v


class PasswordChange(BaseModel):
    current_password: str
    new_password: str
    
    @field_validator('new_password')
    @classmethod
    def validate_password(cls, v):
        is_valid, message = validate_password_strength(v)
        if not is_valid:
            raise ValueError(message)
        return v


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    full_name: Optional[str]
    is_active: bool
    is_verified: bool
    created_at: datetime
    thsr_use_membership: bool
    has_thsr_id: bool


class RefreshTokenRequest(BaseModel):
    refresh_token: str


# Dependency to get current user
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_database)
) -> User:
    """Get current authenticated user"""
    token_data = verify_token(credentials.credentials)
    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user = db.query(User).filter(User.id == token_data.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inactive user"
        )
    
    return user


def log_user_action(db: Session, user_id: Optional[int], action: str, 
                   resource: str, details: str, request: Request, 
                   success: bool = True):
    """Log user action for audit purposes"""
    audit_log = AuditLog(
        user_id=user_id,
        action=action,
        resource=resource,
        details=details,
        ip_address=request.client.host,
        user_agent=request.headers.get("user-agent", ""),
        success=success
    )
    db.add(audit_log)
    db.commit()


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Test database connection
        db = next(get_database())
        db.execute("SELECT 1")
        return {"status": "healthy", "service": "thsr-sniper-auth", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "service": "thsr-sniper-auth", "error": str(e)}


@app.post("/register", response_model=UserResponse)
async def register_user(
    user_data: UserCreate,
    request: Request,
    db: Session = Depends(get_database)
):
    """Register a new user"""
    # Check if username already exists
    if db.query(User).filter(User.username == user_data.username).first():
        log_user_action(db, None, "REGISTER_FAILED", "user", 
                       f"Username already exists: {user_data.username}", 
                       request, False)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    # Check if email already exists
    if db.query(User).filter(User.email == user_data.email).first():
        log_user_action(db, None, "REGISTER_FAILED", "user", 
                       f"Email already exists: {user_data.email}", 
                       request, False)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user
    user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=get_password_hash(user_data.password),
        full_name=user_data.full_name,
        thsr_personal_id=encrypt_sensitive_data(user_data.thsr_personal_id) if user_data.thsr_personal_id else None,
        thsr_use_membership=user_data.thsr_use_membership,
        is_verified=True  # Auto-verify for simplicity
    )
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    log_user_action(db, user.id, "USER_REGISTERED", "user", 
                   f"New user registered: {user.username}", request)
    
    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        is_verified=user.is_verified,
        created_at=user.created_at,
        thsr_use_membership=user.thsr_use_membership,
        has_thsr_id=bool(user.thsr_personal_id)
    )


@app.post("/login", response_model=Token)
async def login_user(
    login_data: UserLogin,
    request: Request,
    db: Session = Depends(get_database)
):
    """Authenticate user and return tokens"""
    user = db.query(User).filter(User.username == login_data.username).first()
    
    if not user:
        log_user_action(db, None, "LOGIN_FAILED", "auth", 
                       f"User not found: {login_data.username}", request, False)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )
    
    # Check if account is locked
    if is_account_locked(user.failed_login_attempts, user.locked_until):
        log_user_action(db, user.id, "LOGIN_BLOCKED", "auth", 
                       "Account locked due to failed attempts", request, False)
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail="Account temporarily locked due to failed login attempts"
        )
    
    # Verify password
    if not verify_password(login_data.password, user.hashed_password):
        # Increment failed attempts
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= 5:
            user.locked_until = calculate_lockout_time()
        db.commit()
        
        log_user_action(db, user.id, "LOGIN_FAILED", "auth", 
                       "Invalid password", request, False)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )
    
    if not user.is_active:
        log_user_action(db, user.id, "LOGIN_FAILED", "auth", 
                       "Inactive user", request, False)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is deactivated"
        )
    
    # Reset failed attempts and update last login
    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_login = datetime.now(timezone.utc)
    db.commit()
    
    # Create token pair
    tokens = create_token_pair(user.id, user.username)
    
    # Store session
    session_token = generate_session_token()
    session = UserSession(
        user_id=user.id,
        session_token=hash_session_token(session_token),
        refresh_token=hash_session_token(tokens.refresh_token),
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        user_agent=request.headers.get("user-agent", ""),
        ip_address=request.client.host
    )
    db.add(session)
    db.commit()
    
    log_user_action(db, user.id, "USER_LOGIN", "auth", 
                   "Successful login", request)
    
    return tokens


@app.post("/refresh", response_model=Token)
async def refresh_token(
    refresh_data: RefreshTokenRequest,
    request: Request,
    db: Session = Depends(get_database)
):
    """Refresh access token using refresh token"""
    token_data = verify_token(refresh_data.refresh_token, "refresh")
    if not token_data:
        log_user_action(db, None, "REFRESH_FAILED", "auth", 
                       "Invalid refresh token", request, False)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    # Verify session exists and is active
    session = db.query(UserSession).filter(
        UserSession.user_id == token_data.user_id,
        UserSession.refresh_token == hash_session_token(refresh_data.refresh_token),
        UserSession.is_active == True,
        UserSession.expires_at > datetime.now(timezone.utc)
    ).first()
    
    if not session:
        log_user_action(db, token_data.user_id, "REFRESH_FAILED", "auth", 
                       "Session not found or expired", request, False)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session"
        )
    
    user = db.query(User).filter(User.id == token_data.user_id).first()
    if not user or not user.is_active:
        log_user_action(db, token_data.user_id, "REFRESH_FAILED", "auth", 
                       "User not found or inactive", request, False)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )
    
    # Create new token pair
    new_tokens = create_token_pair(user.id, user.username)
    
    # Update session with new refresh token
    session.refresh_token = hash_session_token(new_tokens.refresh_token)
    session.expires_at = datetime.now(timezone.utc) + timedelta(days=7)
    db.commit()
    
    log_user_action(db, user.id, "TOKEN_REFRESHED", "auth", 
                   "Token refreshed successfully", request)
    
    return new_tokens


@app.post("/logout")
async def logout_user(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_database)
):
    """Logout user and invalidate session"""
    # Invalidate all active sessions for the user
    db.query(UserSession).filter(
        UserSession.user_id == current_user.id,
        UserSession.is_active == True
    ).update({"is_active": False})
    db.commit()
    
    log_user_action(db, current_user.id, "USER_LOGOUT", "auth", 
                   "User logged out", request)
    
    return {"message": "Successfully logged out"}


@app.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information"""
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        full_name=current_user.full_name,
        is_active=current_user.is_active,
        is_verified=current_user.is_verified,
        created_at=current_user.created_at,
        thsr_use_membership=current_user.thsr_use_membership,
        has_thsr_id=bool(current_user.thsr_personal_id)
    )


@app.put("/me", response_model=UserResponse)
async def update_user_profile(
    user_update: UserUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_database)
):
    """Update current user profile"""
    update_data = user_update.dict(exclude_unset=True)
    
    # Handle sensitive data encryption
    if 'thsr_personal_id' in update_data:
        update_data['thsr_personal_id'] = encrypt_sensitive_data(update_data['thsr_personal_id'])
    
    # Handle preferences JSON conversion
    if 'preferences' in update_data:
        update_data['preferences'] = json.dumps(update_data['preferences'])
    
    # Update user fields
    for field, value in update_data.items():
        setattr(current_user, field, value)
    
    current_user.updated_at = datetime.now(timezone.utc)
    db.commit()
    
    log_user_action(db, current_user.id, "PROFILE_UPDATED", "user", 
                   f"Profile updated: {list(update_data.keys())}", request)
    
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        full_name=current_user.full_name,
        is_active=current_user.is_active,
        is_verified=current_user.is_verified,
        created_at=current_user.created_at,
        thsr_use_membership=current_user.thsr_use_membership,
        has_thsr_id=bool(current_user.thsr_personal_id)
    )


@app.post("/change-password")
async def change_password(
    password_data: PasswordChange,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_database)
):
    """Change user password"""
    if not verify_password(password_data.current_password, current_user.hashed_password):
        log_user_action(db, current_user.id, "PASSWORD_CHANGE_FAILED", "auth", 
                       "Invalid current password", request, False)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid current password"
        )
    
    current_user.hashed_password = get_password_hash(password_data.new_password)
    current_user.updated_at = datetime.now(timezone.utc)
    db.commit()
    
    # Invalidate all sessions to force re-login
    db.query(UserSession).filter(
        UserSession.user_id == current_user.id,
        UserSession.is_active == True
    ).update({"is_active": False})
    db.commit()
    
    log_user_action(db, current_user.id, "PASSWORD_CHANGED", "auth", 
                   "Password changed successfully", request)
    
    return {"message": "Password changed successfully. Please login again."}


@app.get("/thsr-info")
async def get_thsr_info(current_user: User = Depends(get_current_user)):
    """Get decrypted THSR information for current user"""
    return {
        "personal_id": decrypt_sensitive_data(current_user.thsr_personal_id) if current_user.thsr_personal_id else None,
        "use_membership": current_user.thsr_use_membership
    }


def run_auth_server(host: str = "0.0.0.0", port: int = 8001):
    """Run the authentication server"""
    uvicorn.run(
        "auth_api:app",
        host=host,
        port=port,
        log_level="info",
        reload=False
    )


if __name__ == "__main__":
    run_auth_server()
