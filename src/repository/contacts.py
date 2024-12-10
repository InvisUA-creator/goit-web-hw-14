from datetime import date, timedelta
from typing import Optional, List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import Contact, User
from src.schemas.contact import ContactSchema


async def get_contacts(limit: int, offset: int, db: AsyncSession, user: User):
    """
    Retrieves a list of contacts for a given user with the specified pagination options.

    Args:
        limit (int): Maximum number of contacts to return.
        offset (int): Number of contacts to skip.
        db (AsyncSession): Database session.
        user (User): The user for which to retrieve notes.
    Returns:
        List[Contact]: List of contacts for a given user.
    """
    stmt = select(Contact).filter_by(user=user).offset(offset).limit(limit)
    contacts = await db.execute(stmt)
    return contacts.scalars().all()


async def get_contact(contact_id: int, db: AsyncSession, user: User):
    """
    Retrieves a specific contact for a given user by contact ID.

    Args:
        contact_id (int): The ID of the contact to retrieve.
        db (AsyncSession): The database session to use for the query.
        user (User): The user to whom the contact belongs.

    Returns:
        Contact: The contact object if found, otherwise None.
    """
    stmt = select(Contact).filter_by(id=contact_id, user=user)
    contact = await db.execute(stmt)
    return contact.scalar_one_or_none()


async def create_contact(body: ContactSchema, db: AsyncSession, user: User):
    """
    Creates a new contact for a given user.

    Args:
        body (ContactSchema): The schema containing the contact details to be created.
        db (AsyncSession): The database session to use for the operation.
        user (User): The user to whom the new contact will belong.

    Returns:
        Contact: The newly created contact object.
    """
    contact = Contact(**body.model_dump(exclude_unset=True), user=user)
    db.add(contact)
    await db.commit()
    await db.refresh(contact)
    return contact


async def update_contact(
    contact_id: int, body: ContactSchema, db: AsyncSession, user: User
):
    """
    Updates an existing contact for a given user.

    This function attempts to update a contact with the provided ID for the specified user.
    If the contact is found, its details are updated with the information from the provided ContactSchema.

    Args:
        contact_id (int): The ID of the contact to be updated.
        body (ContactSchema): A schema containing the updated contact information.
        db (AsyncSession): The database session to use for the operation.
        user (User): The user to whom the contact belongs.

    Returns:
        Contact: The updated contact object if found and updated successfully, None otherwise.
    """
    stmt = select(Contact).filter_by(id=contact_id, user=user)
    result = await db.execute(stmt)
    contact = result.scalar_one_or_none()
    if contact:
        contact.first_name = body.first_name
        contact.last_name = body.last_name
        contact.email = body.email
        contact.phone = body.phone
        contact.birthday = body.birthday
        contact.data_add = body.data_add
        await db.commit()
        await db.refresh(contact)
    return contact


async def delete_contact(contact_id: int, db: AsyncSession, user: User):
    """
    Deletes a specific contact for a given user by contact ID.

    Args:
        contact_id (int): The ID of the contact to be deleted.
        db (AsyncSession): The database session to use for the operation.
        user (User): The user to whom the contact belongs.

    Returns:
        Contact: The deleted contact object if found and deleted successfully, None otherwise.
    """
    stmt = select(Contact).filter_by(id=contact_id, user=user)
    contact = await db.execute(stmt)
    contact = contact.scalar_one_or_none()
    if contact:
        await db.delete(contact)
        await db.commit()
    return contact


async def search_contacts(
    db: AsyncSession,
    user: User,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    email: Optional[str] = None,
) -> List[Contact]:
    """
    Searches for contacts based on the provided parameters for a given user.

    Args:
        db (AsyncSession): The database session to use for the query.
        user (User): The user for whom to search contacts.
        first_name (Optional[str], optional): The first name to search for. Defaults to None. If provided, returns contacts whose first name contains the specified string.
        last_name (Optional[str], optional): The last name to search for. Defaults to None. If provided, returns contacts whose last name contains the specified string.
        email (Optional[str], optional): The email to search for. Defaults to None. If provided, returns contacts whose email contains the specified string.

    Returns:
        List[Contact]: A list of contacts that match the search parameters for the specified user.
    """
    stmt = select(Contact).filter_by(user=user)
    if first_name:
        stmt = stmt.filter(Contact.first_name.ilike(f"%{first_name}%"))
    if last_name:
        stmt = stmt.filter(Contact.last_name.ilike(f"%{last_name}%"))
    if email:
        stmt = stmt.filter(Contact.email.ilike(f"%{email}%"))
    result = await db.execute(stmt)
    return result.scalars().all()


async def get_upcoming_birthdays(db: AsyncSession, user: User, days: int = 7):
    """
    Retrieves a list of contacts who have a birthday within the specified number of days for a given user.

    Args:
        db (AsyncSession): The database session to use for the query.
        user (User): The user for whom to retrieve upcoming birthdays.
        days (int, optional): Number of days within which to consider a birthday as upcoming. Defaults to 7.

    Returns:
        List[Dict]: A list of dictionaries containing details of contacts with upcoming birthdays.
            Each dictionary includes:
            - contact_id (int): The ID of the contact.
            - first_name (str): The contact's first name.
            - last_name (str): The contact's last name.
            - congratulation_date (str): The date on which to congratulate the contact,
            adjusted to the next weekday if the birthday falls on a weekend.
    """
    today = date.today()
    upcoming_contacts = []

    stmt = select(Contact).filter_by(user=user)
    contacts = await db.execute(stmt)

    contacts = contacts.scalars().all()

    for contact in contacts:
        birthday_real = contact.birthday
        birthday_this_year = birthday_real.replace(year=today.year)
        if birthday_this_year < today:
            birthday_this_year = birthday_real.replace(year=today.year + 1)

        days_until_birthday = (birthday_this_year - today).days
        if 0 <= days_until_birthday <= days:
            congratulation_date = adjust_for_weekend(birthday_this_year)
            congratulation_date_str = date_to_string(congratulation_date)
            upcoming_contacts.append(
                {
                    "contact_id": contact.id,
                    "first_name": contact.first_name,
                    "last_name": contact.last_name,
                    "congratulation_date": congratulation_date_str,
                }
            )

    return upcoming_contacts


def date_to_string(date):
    return date.strftime("%d.%m.%Y")


def adjust_for_weekend(birthday):
    if birthday.weekday() >= 5:
        return find_next_weekday(birthday, 0)
    return birthday


def find_next_weekday(start_date, weekday):
    days_ahead = weekday - start_date.weekday()
    if days_ahead <= 0:
        days_ahead += 7
    return start_date + timedelta(days=days_ahead)
