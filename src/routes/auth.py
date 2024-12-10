from datetime import datetime, timedelta

from fastapi import (
    APIRouter,
    HTTPException,
    Depends,
    status,
    Security,
    BackgroundTasks,
    Request,
)
from fastapi.security import (
    OAuth2PasswordRequestForm,
    HTTPAuthorizationCredentials,
    HTTPBearer,
)
from pydantic import EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.db import get_db
from src.repository import users as repositories_users
from src.schemas.user import UserSchema, TokenSchema, UserResponse, RequestEmail
from src.services.auth import auth_service
from src.services.email import send_email, send_email_password
from src.conf import messages

router = APIRouter(prefix="/auth", tags=["auth"])
get_refresh_token = HTTPBearer()


@router.post(
    "/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED
)
async def signup(
    body: UserSchema,
    bt: BackgroundTasks,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Registers a new user account.

    Args:
        body (UserSchema): The schema containing the user details for registration.
        bt (BackgroundTasks): Background task manager for executing tasks asynchronously.
        request (Request): The HTTP request object, used to retrieve base URL details.
        db (AsyncSession): The database session to use for the operation. Defaults to a dependency-injected session.

    Raises:
        HTTPException: If an account with the provided email already exists.

    Returns:
        UserResponse: The newly created user object, formatted as a response model.
    """
    exist_user = await repositories_users.get_user_by_email(body.email, db)
    if exist_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=messages.ACCOUNT_EXIST
        )
    body.password = auth_service.get_password_hash(body.password)
    new_user = await repositories_users.create_user(body, db)
    bt.add_task(send_email, new_user.email, new_user.username, str(request.base_url))
    return new_user


@router.post("/login", response_model=TokenSchema)
async def login(
    body: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)
):
    """
    Authenticates a user and provides access and refresh tokens.

    Args:
        body (OAuth2PasswordRequestForm): The form data containing the username (email) and password.
        db (AsyncSession): The database session to use for the operation. Defaults to a dependency-injected session.

    Raises:
        HTTPException: If the provided email is invalid or does not exist.
        HTTPException: If the user's email is not confirmed.
        HTTPException: If the provided password is incorrect.

    Returns:
        dict: A dictionary containing the following keys:
            - "access_token" (str): The JWT access token for the authenticated user.
            - "refresh_token" (str): The JWT refresh token for the authenticated user.
            - "token_type" (str): The type of the token, typically "bearer".
    """
    user = await repositories_users.get_user_by_email(body.username, db)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=messages.INVALID_EMAIL
        )
    if not user.confirmed:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=messages.EMAIL_NOT_CONFIRMED,
        )
    if not auth_service.verify_password(body.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=messages.INVALID_PASSWORD
        )
    # Generate JWT
    access_token = await auth_service.create_access_token(data={"sub": user.email})
    refresh_token = await auth_service.create_refresh_token(data={"sub": user.email})
    await repositories_users.update_token(user, refresh_token, db)
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


@router.get("/refresh_token", response_model=TokenSchema)
async def refresh_token(
    credentials: HTTPAuthorizationCredentials = Security(get_refresh_token),
    db: AsyncSession = Depends(get_db),
):
    """
    Generates new access and refresh tokens using a valid refresh token.

    Args:
        credentials (HTTPAuthorizationCredentials): The HTTP authorization credentials containing the refresh token.
        db (AsyncSession): The database session to use for the operation. Defaults to a dependency-injected session.

    Raises:
        HTTPException: If the refresh token is invalid or does not match the stored token for the user.

    Returns:
        dict: A dictionary containing the following keys:
            - "access_token" (str): The newly generated JWT access token.
            - "refresh_token" (str): The newly generated JWT refresh token.
            - "token_type" (str): The type of the token, typically "bearer".
    """
    token = credentials.credentials
    email = await auth_service.decode_refresh_token(token)
    user = await repositories_users.get_user_by_email(email, db)
    if user.refresh_token != token:
        await repositories_users.update_token(user, None, db)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=messages.INVALID_TOKEN
        )

    access_token = await auth_service.create_access_token(data={"sub": email})
    refresh_token = await auth_service.create_refresh_token(data={"sub": email})
    await repositories_users.update_token(user, refresh_token, db)
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


@router.get("/confirmed_email/{token}")
async def confirmed_email(
    token: str, db: AsyncSession = Depends(get_db)
) -> dict[str, str]:
    """
    Confirms a user's email address using a verification token.

    Args:
        token (str): The email verification token provided to the user.
        db (AsyncSession): The database session to use for the operation. Defaults to a dependency-injected session.

    Raises:
        HTTPException: If the token is invalid or no user is associated with the email retrieved from the token.

    Returns:
        dict[str, str]: A dictionary containing a confirmation message. Possible keys and values:
            - "message": "Your email is already confirmed" if the email was previously confirmed.
            - "message": "Email confirmed" if the email is successfully confirmed.
    """
    email = await auth_service.get_email_from_token(token)
    user = await repositories_users.get_user_by_email(email, db)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=messages.VERIFICATION_ERROR
        )
    if user.confirmed:
        return {"message": "Your email is already confirmed"}
    await repositories_users.confirmed_email(email, db)
    return {"message": "Email confirmed"}


@router.post("/request_email")
async def request_email(
    body: RequestEmail,
    background_tasks: BackgroundTasks,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """
    Send a request to confirm a user's email address.

    Args:
        body (RequestEmail): The request body containing the user's email address.
        background_tasks (BackgroundTasks): The background task manager for executing tasks asynchronously.
        request (Request): The HTTP request object, used to retrieve base URL details.
        db (AsyncSession, optional): The database session to use. Defaults to a dependency-injected session.

    Returns:
        dict[str, str]: A dictionary containing a confirmation message. Possible keys and values:
            - "message": "Your email is already confirmed" if the email was previously confirmed.
            - "message": "Check your email for confirmation" if the request is sent successfully.
    """
    user = await repositories_users.get_user_by_email(body.email, db)

    if user.confirmed:
        return {"message": "Your email is already confirmed"}
    if user:
        background_tasks.add_task(
            send_email, user.email, user.username, str(request.base_url)
        )
    return {"message": "Check your email for confirmation."}


@router.post("/password-reset-request", status_code=status.HTTP_200_OK)
async def request_password_reset(
    email: EmailStr, request: Request, db: AsyncSession = Depends(get_db)
):
    """
    Sends a password reset link to the user's email address.

    Args:
        email (EmailStr): The email address of the user requesting a password reset.
        request (Request): The HTTP request object, used to retrieve the base URL for generating the reset link.
        db (AsyncSession): The database session to use for the operation. Defaults to a dependency-injected session.

    Raises:
        HTTPException: If no user is found with the provided email address.

    Returns:
        dict[str, str]: A dictionary containing a success message:
            - "message": "Password reset link has been sent to your email".
    """
    user = await repositories_users.get_user_by_email(email, db)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=messages.USER_NOT_FOUND
        )
    host = str(request.base_url)
    token = auth_service.create_email_token_with_redis(email)
    reset_link = str(token)
    await send_email_password(email, user.username, reset_link, host)
    return {"message": "Password reset link has been sent to your email"}


@router.post("/password-reset", status_code=status.HTTP_200_OK)
async def reset_password(
    token: str, new_password: str, db: AsyncSession = Depends(get_db)
):
    """
    Resets a user's password using a password reset token.

    Args:
        token (str): The password reset token provided to the user.
        new_password (str): The new password to be set for the user.
        db (AsyncSession, optional): The database session to use for the operation. Defaults to a dependency-injected session.

    Raises:
        HTTPException: If no user is found with the email associated with the provided token.

    Returns:
        dict[str, str]: A dictionary containing a success message:
            - "message": "Password updated successfully for user <username>"
    """
    email = await auth_service.verify_email_token_from_redis(token)
    user = await repositories_users.get_user_by_email(email, db)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=messages.USER_NOT_FOUND
        )
    updated_user = await repositories_users.update_user_password(
        email, new_password, db
    )
    await auth_service.cache.delete(email)
    return {
        "message": f"Password updated successfully for user {updated_user.username}"
    }


@router.get("/password-reset/{token}", status_code=status.HTTP_200_OK)
async def password_reset_form(token: str):
    # TODO - Entering a new password
    new_password = "new_password"
    return {"new_password": new_password, "token": token}
