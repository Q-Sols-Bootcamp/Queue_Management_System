from datetime import datetime, timedelta
from jose import jwt, JWTError
from fastapi import HTTPException
from passlib.context import CryptContext
from dotenv import load_dotenv
from status import StatusCode

load_dotenv()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

SECRET_KEY = "ABC"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


def create_access_token(data: dict):
    """
    Create a new access token.

    This function generates a JSON Web Token (JWT) for the given data,
    including an expiration time.

    Args:
        data (dict): A dictionary containing the user data to encode in the
        token.
                     Must include a 'sub' key representing the username.

    Returns:
        str: The encoded JWT as a string.

    Notes:
        - The token will expire after a predefined time period
          (ACCESS_TOKEN_EXPIRE_MINUTES).
        - The token is signed using a secret key and a specified algorithm.
    """
    to_encode = data.copy()
    expire = datetime.now() + timedelta(minutes= ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({'exp':expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm= ALGORITHM)
    return encoded_jwt


def verify_access_token(token: str):
    """
    Verify the access token and extract the username.

    This function decodes the given JWT access token, validates its
    authenticity, and retrieves the username from its payload.

    Args:
        token (str): The JWT access token to verify.

    Returns:
        str: The username extracted from the token payload.

    Raises:
        HTTPException:
            - If the token is invalid, expired, or does not contain a valid
            username (401).
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get('sub')
        if username is None:
            raise HTTPException(status_code=StatusCode.NOT_FOUND.value, detail=StatusCode.NOT_FOUND.message)
        return username
    except JWTError:
            raise HTTPException(status_code=401, detail="Could not validate credentials")
        
def hash_password(password: str):
    """
    Hash a password using bcrypt.

    This function takes a plaintext password and returns a hashed version of it.

    Args:
        password (str): The plaintext password to hash.

    Returns:
        str: The hashed password.
    """
    return pwd_context.hash(password)

def verify_password(entered_pwd: str, hashed_pwd: str):
    """
    Verify a password against a hashed password.

    This function takes a plaintext password and a hashed password, and returns True if they match, False otherwise.

    Args:
        entered_pwd (str): The plaintext password to verify.
        hashed_pwd (str): The hashed password to compare against.

    Returns:
        bool: True if the passwords match, False otherwise.
    """    
    return pwd_context.verify(entered_pwd, hashed_pwd)