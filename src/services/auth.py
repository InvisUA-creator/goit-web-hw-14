import pickle
from datetime import datetime, timedelta
from typing import Optional

import redis
from fastapi import Depends, HTTPException, status
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from jose import JWTError, jwt, ExpiredSignatureError

from src.conf.config import config
from src.database.db import get_db
from src.repository import users as repository_users


class Auth:
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    SECRET_KEY = config.SECRET_KEY_JWT
    ALGORITHM = config.ALGORITHM
    cache = redis.Redis(
        host=config.REDIS_DOMAIN,
        port=config.REDIS_PORT,
        db=0,
        password=config.REDIS_PASSWORD,
    )

    def verify_password(self, plain_password, hashed_password):
        """
        Verify a plain password against a hashed password.

        Args:
            plain_password (str): The plain password to verify.
            hashed_password (str): The hashed password to compare against.

        Returns:
            bool: True if the plain password matches the hashed password, False otherwise.
        """
        return self.pwd_context.verify(plain_password, hashed_password)

    def get_password_hash(self, password: str):
        """
        Hash a plain password using the configured password context.

        Args:
            password (str): The plain password to hash.

        Returns:
            str: The hashed password.
        """
        return self.pwd_context.hash(password)

    oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")

    # define a function to generate a new access token
    async def create_access_token(
        self, data: dict, expires_delta: Optional[float] = None
    ):
        """
        Generate a new access token using JWT.

        Args:
            data (dict): The data to encode into the JWT.
            expires_delta (float, optional): The expiration time in seconds. Defaults to 15 minutes.

        Returns:
            str: The encoded access token.
        """
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.now() + timedelta(seconds=expires_delta)
        else:
            expire = datetime.now() + timedelta(minutes=15)
        to_encode.update(
            {"iat": datetime.now(), "exp": expire, "scope": "access_token"}
        )
        encoded_access_token = jwt.encode(
            to_encode, self.SECRET_KEY, algorithm=self.ALGORITHM
        )
        return encoded_access_token

    # define a function to generate a new refresh token
    async def create_refresh_token(
        self, data: dict, expires_delta: Optional[float] = None
    ):
        """
        Generate a new refresh token using JWT.

        Args:
            data (dict): The data to encode into the JWT.
            expires_delta (float, optional): The expiration time in seconds. Defaults to 7 days.

        Returns:
            str: The encoded refresh token.
        """
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.now() + timedelta(seconds=expires_delta)
        else:
            expire = datetime.now() + timedelta(days=7)
        to_encode.update(
            {"iat": datetime.now(), "exp": expire, "scope": "refresh_token"}
        )
        encoded_refresh_token = jwt.encode(
            to_encode, self.SECRET_KEY, algorithm=self.ALGORITHM
        )
        return encoded_refresh_token

    async def decode_refresh_token(self, refresh_token: str):
        """
        Decode a refresh token and extract the email.

        Args:
            refresh_token (str): The refresh token to decode.

        Raises:
            HTTPException: If the token is invalid or the scope is not 'refresh_token'.

        Returns:
            str: The email extracted from the token.
        """
        try:
            payload = jwt.decode(
                refresh_token, self.SECRET_KEY, algorithms=[self.ALGORITHM]
            )
            if payload["scope"] == "refresh_token":
                email = payload["sub"]
                return email
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid scope for token",
            )
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
            )

    async def get_current_user(
        self, token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)
    ):
        """
        Get the current user based on the provided access token.

        Args:
            token (str, optional): The access token. Defaults to the token provided by the OAuth2PasswordBearer.
            db (AsyncSession, optional): The database session. Defaults to the session provided by the get_db dependency.

        Raises:
            HTTPException: If the token is invalid or the user is not found.

        Returns:
            User: The current user.
        """
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

        try:
            # Decode JWT
            payload = jwt.decode(token, self.SECRET_KEY, algorithms=[self.ALGORITHM])
            if payload["scope"] == "access_token":
                email = payload["sub"]
                if email is None:
                    raise credentials_exception
            else:
                raise credentials_exception
        except JWTError as e:
            raise credentials_exception

        user_hash = str(email)
        user = self.cache.get(user_hash)

        if user is None:
            #  User from database
            user = await repository_users.get_user_by_email(email, db)
            if user is None:
                raise credentials_exception
            self.cache.set(user_hash, pickle.dumps(user))
            self.cache.expire(user_hash, 300)
        else:
            #  User from cache
            user = pickle.loads(user)
        return user

    def create_email_token(self, data: dict):
        """
        Create a new email token using JWT.

        Args:
            data (dict): The data to encode into the JWT.

        Returns:
            str: The encoded email token.
        """
        to_encode = data.copy()
        expire = datetime.now() + timedelta(days=1)
        to_encode.update({"iat": datetime.now(), "exp": expire})
        token = jwt.encode(to_encode, self.SECRET_KEY, algorithm=self.ALGORITHM)
        return token

    async def get_email_from_token(self, token: str):
        """
        Decode an email token and extract the email.

        Args:
            token (str): The email token to decode.

        Raises:
            HTTPException: If the token is invalid.

        Returns:
            str: The email extracted from the token.
        """
        try:
            payload = jwt.decode(token, self.SECRET_KEY, algorithms=[self.ALGORITHM])
            email = payload["sub"]
            return email
        except JWTError as e:
            print(e)
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Invalid token for email verification",
            )

    def create_email_token_with_redis(self, email: str, expiration: int = 3600):
        """
        Create a new email token using JWT and store it in Redis.

        Args:
            email (str): The email to encode into the JWT.
            expiration (int, optional): The expiration time in seconds. Defaults to 3600 (1 hour).

        Returns:
            str: The encoded email token.
        """
        token = self.create_email_token({"sub": email})
        self.cache.set(email, token, ex=expiration)
        return token

    async def verify_email_token_from_redis(self, token: str):
        """
        Decode an email token, extract the email, and verify it against the stored token in Redis.

        Args:
            token (str): The email token to decode.

        Raises:
            HTTPException: If the token is invalid or expired.

        Returns:
            str: The email extracted from the token.
        """
        try:
            payload = jwt.decode(token, self.SECRET_KEY, algorithms=[self.ALGORITHM])
            email = payload.get("sub")
            if email is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid token"
                )

            redis_token = self.cache.get(email)
            if redis_token is None or redis_token.decode() != token:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid or expired token",
                )
            return email

        except ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Token has expired"
            )
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid token"
            )


auth_service = Auth()
