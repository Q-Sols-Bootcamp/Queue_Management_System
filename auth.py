from datetime import datetime, timedelta
from jose import jwt, JWTError
from fastapi import HTTPException
from passlib.context import CryptContext
import os
from dotenv import load_dotenv

load_dotenv()

pwd_context = CryptContext(schemes=[os.getenv("PASSWORD_SCHEME")], deprecated="auto")

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES"))

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now() + timedelta(minutes= ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({'exp':expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm= ALGORITHM)
    return encoded_jwt

def verify_access_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms= [ALGORITHM])
        username: str = payload('sub')
        if username is None:
            raise HTTPException(status_code=401, detail="Username can not be empty")
        return username
    except JWTError:
            raise HTTPException(status_code=401, detail="Could not validate credentials")
        
def hash_password(password: str):
    return pwd_context.hash(password)

def verify_password(entered_pwd: str, hashed_pwd: str):
    return pwd_context.verify(entered_pwd, hashed_pwd)