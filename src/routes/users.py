import pickle

import cloudinary
import cloudinary.uploader

from fastapi import APIRouter, Depends, UploadFile, File
from fastapi_limiter.depends import RateLimiter

from sqlalchemy.ext.asyncio import AsyncSession

from src.database.db import get_db
from src.database.models import User
from src.schemas.user import UserResponse
from src.services.auth import auth_service
from src.conf.config import config
from src.repository import users as repositories_users

router = APIRouter(prefix="/users", tags=["users"])

cloudinary.config(
    cloud_name=config.CLD_NAME,
    api_key=config.CLD_API_KEY,
    api_secret=config.CLD_API_SECRET,
    secure=True,
)


@router.get(
    "/me",
    response_model=UserResponse,
    dependencies=[Depends(RateLimiter(times=2, seconds=20))],
)
async def get_current_user(user: User = Depends(auth_service.get_current_user)):
    """
    Retrieve the current authenticated user.

    This function retrieves the currently authenticated user from the request's context.
    It uses the `auth_service.get_current_user` function to fetch the user.
    The user is then returned as a response using the `UserResponse` model.

    Parameters:
    user (User): The authenticated user. This parameter is optional and is injected by the FastAPI framework.

    Returns:
    UserResponse: The authenticated user's data, formatted according to the `UserResponse` model.
    """
    return user


@router.patch(
    "/avatar",
    response_model=UserResponse,
    dependencies=[Depends(RateLimiter(times=1, seconds=20))],
)
async def update_avatar_user(
    file: UploadFile = File(),
    user: User = Depends(auth_service.get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Updates the avatar of the current authenticated user.

    This function receives an uploaded file representing the new avatar,
    processes it using Cloudinary, updates the user's avatar URL in the database,
    and caches the updated user object for future requests.

    Parameters:
    file (UploadFile): The uploaded file representing the new avatar. This parameter is optional and is injected by the FastAPI framework.
    user (User): The authenticated user. This parameter is optional and is injected by the FastAPI framework.
    db (AsyncSession): The database session. This parameter is optional and is injected by the FastAPI framework.

    Returns:
    UserResponse: The updated user object, formatted according to the `UserResponse` model.
    """
    public_id = f"Web25/{user.email}"
    res = cloudinary.uploader.upload(file.file, public_id=public_id, owerite=True)
    res_url = cloudinary.CloudinaryImage(public_id).build_url(
        width=250, height=250, crop="fill", version=res.get("version")
    )
    user = await repositories_users.update_avatar_url(user.email, res_url, db)
    auth_service.cache.set(user.email, pickle.dumps(user))
    auth_service.cache.expire(user.email, 300)
    return user
