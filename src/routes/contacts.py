from typing import Optional, List

from fastapi import APIRouter, HTTPException, Depends, status, Path, Query
from fastapi_limiter.depends import RateLimiter

from sqlalchemy.ext.asyncio import AsyncSession

from src.database.db import get_db
from src.database.models import User
from src.repository import contacts as repositories_contact
from src.schemas.contact import ContactSchema, ContactResponse
from src.services.auth import auth_service

router = APIRouter(prefix="/contact", tags=["contact"])


@router.get(
    "/search",
    response_model=list[ContactResponse],
    dependencies=[Depends(RateLimiter(times=1, seconds=20))],
)
async def search_contacts(
    first_name: Optional[str] = Query(None, min_length=1),
    last_name: Optional[str] = Query(None, min_length=1),
    email: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(auth_service.get_current_user),
):
    """
    Searches for contacts based on the provided query parameters.

    Args:
        first_name (Optional[str]): The first name to search for (optional, minimum length: 1).
        last_name (Optional[str]): The last name to search for (optional, minimum length: 1).
        email (Optional[str]): The email address to search for (optional).
        db (AsyncSession): The database session to use for the operation. Defaults to a dependency-injected session.
        user (User): The currently authenticated user, used to filter contacts.

    Raises:
        HTTPException: If no contacts matching the query parameters are found.

    Returns:
        list[ContactResponse]: A list of contact objects matching the search criteria.
    """
    contacts = await repositories_contact.search_contacts(
        db=db, user=user, first_name=first_name, last_name=last_name, email=email
    )
    if not contacts:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Contacts not found"
        )
    return contacts


@router.get(
    "/upcoming_birthdays",
    response_model=List[dict],
    dependencies=[Depends(RateLimiter(times=1, seconds=20))],
)
async def upcoming_birthdays(
    days: int = 7,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(auth_service.get_current_user),
):
    """
    Retrieves upcoming birthdays for the authenticated user.

    Args:
        days (int): The number of days in the future to consider for upcoming birthdays. Defaults to 7.
        db (AsyncSession): The database session to use for the operation. Defaults to a dependency-injected session.
        user (User): The currently authenticated user, used to filter contacts.

    Returns:
        List[dict]: A list of dictionaries, each representing a contact with an upcoming birthday.
    """
    contacts = await repositories_contact.get_upcoming_birthdays(db, user, days)
    return contacts


@router.get(
    "/{contact_id}",
    response_model=ContactResponse,
    dependencies=[Depends(RateLimiter(times=1, seconds=20))],
)
async def get_contact(
    contact_id: int = Path(ge=1),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(auth_service.get_current_user),
):
    """
    Retrieves a specific contact by its ID.

    Args:
        contact_id (int): The ID of the contact to retrieve (must be greater than or equal to 1).
        db (AsyncSession): The database session to use for the operation. Defaults to a dependency-injected session.
        user (User): The currently authenticated user, used to ensure the contact belongs to them.

    Raises:
        HTTPException: If no contact is found with the provided ID for the current user.

    Returns:
        ContactResponse: The contact object corresponding to the provided ID.
    """
    contact = await repositories_contact.get_contact(contact_id, db, user)
    if contact is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="NOT FOUND")
    return contact


@router.get(
    "/",
    response_model=list[ContactResponse],
    dependencies=[Depends(RateLimiter(times=1, seconds=20))],
)
async def get_contacts(
    limit: int = Query(10, ge=10, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(auth_service.get_current_user),
):
    """
    Retrieves a list of contacts for the authenticated user.

    Args:
        limit (int): The maximum number of contacts to retrieve. Defaults to 10, must be between 10 and 500.
        offset (int): The number of contacts to skip before starting to retrieve. Defaults to 0, must be non-negative.
        db (AsyncSession): The database session to use for the operation. Defaults to a dependency-injected session.
        user (User): The currently authenticated user, used to filter contacts.

    Returns:
        list[ContactResponse]: A list of contact objects matching the provided parameters.
    """
    contacts = await repositories_contact.get_contacts(limit, offset, db, user)
    return contacts


@router.post(
    "/",
    response_model=ContactResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(RateLimiter(times=1, seconds=20))],
)
async def create_contact(
    body: ContactSchema,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(auth_service.get_current_user),
):
    """
    Creates a new contact in the database.

    Args:
        body (ContactSchema): The contact data to be created.
        db (AsyncSession): The database session to use for the operation. Defaults to a dependency-injected session.
        user (User): The currently authenticated user, used to associate the contact with the user.

    Returns:
        ContactResponse: The newly created contact object.
    """
    contact = await repositories_contact.create_contact(body, db, user)
    return contact


@router.put("/{contact_id}", dependencies=[Depends(RateLimiter(times=1, seconds=20))])
async def update_contact(
    body: ContactSchema,
    contact_id: int = Path(ge=1),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(auth_service.get_current_user),
):
    """
    Updates an existing contact in the database.

    Args:
        body (ContactSchema): The updated contact data.
        contact_id (int): The ID of the contact to update (must be greater than or equal to 1).
        db (AsyncSession): The database session to use for the operation. Defaults to a dependency-injected session.
        user (User): The currently authenticated user, used to ensure the contact belongs to them.

    Returns:
        ContactResponse: The updated contact object.

    Raises:
        HTTPException: If no contact is found with the provided ID for the current user.
    """
    contact = await repositories_contact.update_contact(contact_id, body, db, user)
    if contact is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="NOT FOUND")
    return contact


@router.delete(
    "/{contact_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(RateLimiter(times=1, seconds=20))],
)
async def delete_contact(
    contact_id: int = Path(ge=1),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(auth_service.get_current_user),
):
    """
    Deletes a contact from the database based on the provided contact ID.

    Args:
        contact_id (int): The ID of the contact to delete. Must be greater than or equal to 1.
        db (AsyncSession): The database session to use for the operation. Defaults to a dependency-injected session.
        user (User): The currently authenticated user, used to ensure the contact belongs to them.

    Returns:
        None: This function does not return any value. It deletes the contact from the database.

    Raises:
        HTTPException: If no contact is found with the provided ID for the current user.
    """
    contact = await repositories_contact.delete_contact(contact_id, db, user)
    return contact
