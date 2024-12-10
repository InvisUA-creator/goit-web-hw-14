import unittest
from datetime import date, timedelta
from unittest.mock import MagicMock, AsyncMock, Mock

from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import Contact, User
from src.schemas.contact import ContactSchema
from src.repository.contacts import (
    get_contacts,
    get_contact,
    create_contact,
    update_contact,
    delete_contact,
    search_contacts,
    get_upcoming_birthdays,
    adjust_for_weekend,
    date_to_string,
)


class TestAsyncContact(unittest.IsolatedAsyncioTestCase):

    def setUp(self) -> None:
        self.user = User(id=1, username="test_user", password="qwerty", confirmed=True)
        self.session = AsyncMock(spec=AsyncSession)

    async def test_get_contacts(self):
        limit = 10
        offset = 0
        contacts = [
            Contact(id=1, first_name="contact_1", email="email_1", user=self.user),
            Contact(id=2, first_name="contact_2", email="email_2", user=self.user),
        ]
        mocked_contacts = MagicMock()
        mocked_contacts.scalars.return_value.all.return_value = contacts
        self.session.execute.return_value = mocked_contacts
        result = await get_contacts(limit, offset, self.session, self.user)
        self.assertEqual(result, contacts)

    async def test_get_contact_found(self):
        contact = Contact(id=1, first_name="contact", email="email", user=self.user)
        mocked_contact = Mock()
        mocked_contact.scalar_one_or_none.return_value = contact
        self.session.execute.return_value = mocked_contact
        result = await get_contact(1, self.session, self.user)
        self.assertEqual(result, contact)

    async def test_get_contact_not_found(self):
        mocked_contact = Mock()
        mocked_contact.scalar_one_or_none.return_value = None
        self.session.execute.return_value = mocked_contact
        result = await get_contact(1, self.session, self.user)
        self.assertIsNone(result)

    async def test_create_contact(self):
        body = ContactSchema(
            first_name="John",
            last_name="Snow",
            email="email",
            phone="123456789",
            birthday=date.today(),
            data_add="data",
        )
        result = await create_contact(body, self.session, self.user)
        self.assertIsInstance(result, Contact)
        self.assertEqual(result.first_name, body.first_name)
        self.assertEqual(result.last_name, body.last_name)
        self.assertEqual(result.email, body.email)
        self.assertEqual(result.phone, body.phone)
        self.assertEqual(result.birthday, body.birthday)
        self.assertEqual(result.data_add, body.data_add)

    async def test_update_contact(self):
        body = ContactSchema(
            first_name="John",
            last_name="Snow",
            email="email",
            phone="123456789",
            birthday=date.today(),
            data_add="data",
        )
        mocked_contact = MagicMock()
        mocked_contact.scalar_one_or_none.return_value = Contact(
            id=1, first_name="John", email="email", user=self.user
        )
        self.session.execute.return_value = mocked_contact
        result = await update_contact(1, body, self.session, self.user)
        self.assertIsInstance(result, Contact)
        self.assertEqual(result.first_name, body.first_name)
        self.assertEqual(result.email, body.email)

    async def test_delete_contact_found(self):
        mocked_contact = MagicMock()
        mocked_contact.scalar_one_or_none.return_value = Contact(
            id=1, first_name="John", email="email", user=self.user
        )
        self.session.execute.return_value = mocked_contact
        result = await delete_contact(1, self.session, self.user)
        self.session.delete.assert_called_once()
        self.session.commit.assert_called_once()
        self.assertIsInstance(result, Contact)

    async def test_delete_contact_not_found(self):
        mocked_contact = MagicMock()
        mocked_contact.scalar_one_or_none.return_value = None
        self.session.execute.return_value = mocked_contact
        result = await delete_contact(1, self.session, self.user)
        self.assertIsNone(result)

    async def test_search_contacts_not_found(self):
        mocked_contacts = MagicMock()
        mocked_contacts.scalars.return_value.all.return_value = []
        self.session.execute.return_value = mocked_contacts
        result = await search_contacts(
            self.session, self.user, first_name="John", last_name="Doe", email="email"
        )
        self.assertEqual(result, [])

    async def test_search_contacts_no_params(self):
        contacts = [
            Contact(
                id=1,
                first_name="John",
                last_name="Doe",
                email="email_1",
                user=self.user,
            ),
            Contact(
                id=2,
                first_name="Jane",
                last_name="Smith",
                email="email_2",
                user=self.user,
            ),
        ]
        mocked_contacts = MagicMock()
        mocked_contacts.scalars.return_value.all.return_value = contacts
        self.session.execute.return_value = mocked_contacts
        result = await search_contacts(self.session, self.user)
        self.assertEqual(result, contacts)

    async def test_search_contacts_exact_first_name(self):
        first_name = "John"
        contacts = [
            Contact(
                id=1,
                first_name=first_name,
                last_name="Doe",
                email="email_1",
                user=self.user,
            ),
            Contact(
                id=2,
                first_name="Jane",
                last_name="Doe",
                email="email_2",
                user=self.user,
            ),
            Contact(
                id=3,
                first_name=first_name,
                last_name="Smith",
                email="email_3",
                user=self.user,
            ),
        ]
        filtered_contacts = [
            contact
            for contact in contacts
            if first_name.lower() in contact.first_name.lower()
        ]
        mocked_contacts = MagicMock()
        mocked_contacts.scalars.return_value.all.return_value = filtered_contacts
        self.session.execute.return_value = mocked_contacts
        result = await search_contacts(self.session, self.user, first_name=first_name)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].first_name, first_name)
        self.assertEqual(result[1].first_name, first_name)

    async def test_search_contacts_exact_last_name(self):
        last_name = "Doe"
        contacts = [
            Contact(
                id=1,
                first_name="John",
                last_name=last_name,
                email="email_1",
                user=self.user,
            ),
            Contact(
                id=2,
                first_name="Jane",
                last_name=last_name,
                email="email_2",
                user=self.user,
            ),
            Contact(
                id=3,
                first_name="John",
                last_name="Smith",
                email="email_3",
                user=self.user,
            ),
        ]
        filtered_contacts = [
            contact
            for contact in contacts
            if last_name.lower() in contact.last_name.lower()
        ]
        mocked_contacts = MagicMock()
        mocked_contacts.scalars.return_value.all.return_value = filtered_contacts
        self.session.execute.return_value = mocked_contacts
        result = await search_contacts(self.session, self.user, last_name=last_name)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].last_name, last_name)
        self.assertEqual(result[1].last_name, last_name)

    async def test_search_contacts_exact_email(self):
        email = "email_2"
        contacts = [
            Contact(
                id=1,
                first_name="John",
                last_name="Doe",
                email="email_1",
                user=self.user,
            ),
            Contact(
                id=2,
                first_name="Jane",
                last_name="Doe",
                email="email_2",
                user=self.user,
            ),
            Contact(
                id=3,
                first_name="John",
                last_name="Smith",
                email="email_3",
                user=self.user,
            ),
        ]
        filtered_contacts = [contact for contact in contacts if email in contact.email]
        mocked_contacts = MagicMock()
        mocked_contacts.scalars.return_value.all.return_value = filtered_contacts
        self.session.execute.return_value = mocked_contacts
        result = await search_contacts(self.session, self.user, email=email)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].email, email)

    async def test_search_contacts_multiple_params(self):
        first_name = "John"
        last_name = "Doe"
        # email = 'email_1'
        contacts = [
            Contact(
                id=1,
                first_name="John",
                last_name="Doe",
                email="email_1",
                user=self.user,
            ),
            Contact(
                id=2,
                first_name="Jane",
                last_name="Doe",
                email="email_2",
                user=self.user,
            ),
            Contact(
                id=3,
                first_name="John",
                last_name="Smith",
                email="email_3",
                user=self.user,
            ),
        ]
        filtered_contacts = [
            contact for contact in contacts if first_name in contact.first_name
        ]
        filtered_contacts = [
            contact for contact in filtered_contacts if last_name in contact.last_name
        ]
        # filtered_contacts = [contact for contact in filtered_contacts if email in contact.email]
        mocked_contacts = MagicMock()
        mocked_contacts.scalars.return_value.all.return_value = filtered_contacts
        self.session.execute.return_value = mocked_contacts
        result = await search_contacts(
            self.session, self.user, first_name=first_name, last_name=last_name
        )
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].first_name, first_name)

    async def test_get_upcoming_birthdays_no_contacts(self):
        user = User(id=1, username="test_user", password="qwerty", confirmed=True)
        mocked_contacts = MagicMock()
        mocked_contacts.scalars.return_value.all.return_value = []
        self.session.execute.return_value = mocked_contacts
        result = await get_upcoming_birthdays(self.session, user, days=7)
        self.assertEqual(result, [])

    async def test_get_upcoming_birthdays_one_contact(self):
        today = date.today()
        contact = Contact(
            id=1,
            first_name="John",
            last_name="Doe",
            birthday=today + timedelta(days=3),
            user=self.user,
        )
        mocked_contacts = MagicMock()
        mocked_contacts.scalars.return_value.all.return_value = [contact]
        self.session.execute.return_value = mocked_contacts
        result = await get_upcoming_birthdays(self.session, self.user, days=7)

        expected_result = [
            {
                "contact_id": 1,
                "first_name": "John",
                "last_name": "Doe",
                "congratulation_date": date_to_string(
                    adjust_for_weekend(contact.birthday.replace(year=today.year))
                ),
            }
        ]
        self.assertEqual(result, expected_result)

    async def test_get_upcoming_birthdays_multiple_contacts(self):
        today = date.today()
        contacts = [
            Contact(
                id=1,
                first_name="John",
                last_name="Doe",
                birthday=today + timedelta(days=1),
                user=self.user,
            ),
            Contact(
                id=2,
                first_name="Jane",
                last_name="Smith",
                birthday=today + timedelta(days=6),
                user=self.user,
            ),
            Contact(
                id=3,
                first_name="Mike",
                last_name="Johnson",
                birthday=today + timedelta(days=3),
                user=self.user,
            ),
        ]
        mocked_contacts = MagicMock()
        mocked_contacts.scalars.return_value.all.return_value = contacts
        self.session.execute.return_value = mocked_contacts
        result = await get_upcoming_birthdays(self.session, self.user, days=10)
        expected_result = [
            {
                "contact_id": contact.id,
                "first_name": contact.first_name,
                "last_name": contact.last_name,
                "congratulation_date": date_to_string(
                    adjust_for_weekend(contact.birthday.replace(year=today.year))
                ),
            }
            for contact in contacts
        ]
        self.assertEqual(result, expected_result)

    def test_adjust_for_weekend(self):
        today = date.today()
        self.assertEqual(adjust_for_weekend(today), today)
        self.assertEqual(
            adjust_for_weekend(today - timedelta(days=1)), today - timedelta(days=1)
        )
        self.assertEqual(
            adjust_for_weekend(today + timedelta(days=1)), today + timedelta(days=1)
        )
