from datetime import datetime

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from libgravatar import Gravatar
from passlib.context import CryptContext

from src.database.db import get_db
from src.database.models import User
from src.schemas.user import UserSchema


async def get_user_by_email(email: str, db: AsyncSession = Depends(get_db)):
    """
    This function retrieves a user from the database based on their email address.

    Args:
        email (str): The email address of the user to retrieve.
        db (AsyncSession): The database session to use for the query.
        Defaults to Depends(get_db).

    Returns:
        User: The user object retrieved from the database, or None if no user
        with the given email address was found.
    """
    stmt = select(User).filter_by(email=email)
    user = await db.execute(stmt)
    user = user.scalar_one_or_none()
    return user


async def create_user(body: UserSchema, db: AsyncSession = Depends(get_db)):
    """
    Create a new user in the database.

    This function takes a UserSchema object containing user data, attempts to retrieve an avatar
    from Gravatar using the user's email, and then creates a new User object in the database
    using the provided data and the retrieved avatar.

    Args:
        body (UserSchema): The user data to be added to the database.
        db (AsyncSession): The database session to use for the query.
        Defaults to Depends(get_db).

    Returns:
        User: The newly created User object.
    """
    avatar = None
    try:
        g = Gravatar(body.email)
        avatar = g.get_image()
    except Exception as err:
        print(err)

    new_user = User(**body.model_dump(), avatar=avatar)
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user


async def update_token(user: User, token: str | None, db: AsyncSession):
    """
    Update a user's refresh token.

    This function updates the 'refresh_token' field of the given user with the provided token.

    Args:
        user (User): The user object to update.
        token (str | None): The new refresh token to set for the user. If set to None,
        the user's refresh token will be cleared.
        db (AsyncSession): The database session to use for the update operation.

    Returns:
        None: The function does not return a value. The user's 'refresh_token' field is updated directly in the database.
    """
    user.refresh_token = token
    await db.commit()


async def confirmed_email(email: str, db: AsyncSession) -> None:
    """
    Mark a user's email as confirmed.

    This function updates the 'confirmed' field of the user with the given email address to True, indicating that
    the email address has been confirmed.

    Args:
        email (str): The email address of the user to mark as confirmed.
        db (AsyncSession): The database session to use for the update operation.

    Returns:
        None: The function does not return a value. The user's 'confirmed' field is updated directly in the database.
    """
    user = await get_user_by_email(email, db)
    user.confirmed = True
    await db.commit()


async def update_avatar_url(email: str, url: str | None, db: AsyncSession) -> User:
    """
    Update the avatar URL for a user.

    This function updates the avatar URL associated with the given user email address.

    Args:
        email (str): The email address of the user to update.
        url (str | None): The new avatar URL to set for the user. If set to None,
        the user's avatar URL will be cleared.
        db (AsyncSession): The database session to use for the update operation.

    Returns:
        User: The updated User object with the new avatar URL.
    """
    user = await get_user_by_email(email, db)
    user.avatar = url
    await db.commit()
    await db.refresh(user)
    return user


async def update_user_password(email: str, new_password: str, db: AsyncSession) -> User:
    """
    Update the password for a user.

    This function updates the password for the user associated with the given email address.
    The new password is hashed before being stored in the database.

    Args:
        email (str): The email address of the user to update.
        new_password (str): The new password to set for the user.
        db (AsyncSession): The database session to use for the update operation.

    Returns:
        User: The updated User object with the new password.
    """
    hashed_password = CryptContext(schemes=["bcrypt"], deprecated="auto").hash(
        new_password
    )
    user = await get_user_by_email(email, db)
    user.password = hashed_password
    user.updated_at = datetime.now()
    await db.commit()
    await db.refresh(user)
    return user
