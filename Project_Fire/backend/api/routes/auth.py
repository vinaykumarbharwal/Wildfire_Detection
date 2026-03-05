from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from datetime import datetime, timedelta
from typing import Optional
import jwt
from passlib.context import CryptContext
import os
from dotenv import load_dotenv

from api.services.firebase_service import db, auth_client

load_dotenv()

router = APIRouter()

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT settings
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")

# Models
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: str
    phone: Optional[str] = None
    user_type: str = "public"  # public, authority, volunteer

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    user_id: str
    name: str
    user_type: str

class TokenData(BaseModel):
    email: Optional[str] = None
    user_id: Optional[str] = None

# Helper functions
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        user_id: str = payload.get("user_id")
        if email is None:
            raise credentials_exception
        token_data = TokenData(email=email, user_id=user_id)
    except jwt.PyJWTError:
        raise credentials_exception
    
    # Get user from Firebase
    user_doc = db.collection('users').document(token_data.user_id).get()
    if not user_doc.exists:
        raise credentials_exception
    
    return user_doc.to_dict()

# Routes
@router.post("/register", response_model=Token)
async def register(user: UserCreate):
    """Register a new user"""
    try:
        # Check if user exists
        users_ref = db.collection('users').where('email', '==', user.email).limit(1).get()
        if len(users_ref) > 0:
            raise HTTPException(status_code=400, detail="Email already registered")
        
        # Create user in Firebase Auth
        try:
            firebase_user = auth_client.create_user(
                email=user.email,
                password=user.password,
                display_name=user.name
            )
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Firebase auth error: {str(e)}")
        
        # Hash password for local storage
        hashed_password = get_password_hash(user.password)
        
        # Store user in Firestore
        user_data = {
            'uid': firebase_user.uid,
            'email': user.email,
            'name': user.name,
            'phone': user.phone,
            'user_type': user.user_type,
            'hashed_password': hashed_password,
            'created_at': datetime.now(),
            'updated_at': datetime.now()
        }
        
        db.collection('users').document(firebase_user.uid).set(user_data)
        
        # Create access token
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.email, "user_id": firebase_user.uid},
            expires_delta=access_token_expires
        )
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user_id": firebase_user.uid,
            "name": user.name,
            "user_type": user.user_type
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/token", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """Login with username (email) and password"""
    try:
        # Find user by email
        users_ref = db.collection('users').where('email', '==', form_data.username).limit(1).get()
        
        if len(users_ref) == 0:
            raise HTTPException(status_code=400, detail="Incorrect email or password")
        
        user_doc = users_ref[0]
        user_data = user_doc.to_dict()
        
        # Verify password
        if not verify_password(form_data.password, user_data['hashed_password']):
            raise HTTPException(status_code=400, detail="Incorrect email or password")
        
        # Create access token
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user_data['email'], "user_id": user_doc.id},
            expires_delta=access_token_expires
        )
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user_id": user_doc.id,
            "name": user_data['name'],
            "user_type": user_data['user_type']
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/me")
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """Get current user information"""
    return {
        "uid": current_user['uid'],
        "email": current_user['email'],
        "name": current_user['name'],
        "user_type": current_user['user_type'],
        "phone": current_user.get('phone')
    }