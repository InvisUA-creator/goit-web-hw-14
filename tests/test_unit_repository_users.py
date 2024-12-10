import unittest
from datetime import date, timedelta, datetime
from unittest.mock import MagicMock, AsyncMock, Mock, patch

from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import Contact, User
from src.schemas.user import UserSchema, UserResponse, RequestEmail
from src.repository.users import (
    get_user_by_email,
    create_user,
    confirmed_email,
    update_avatar_url,
    update_user_password,
)


class TestAsyncUser(unittest.IsolatedAsyncioTestCase):

    def setUp(self) -> None:
        # self.user = User(id=1, username='test_user', email='email', password="qwerty", confirmed=True)
        self.session = AsyncMock(spec=AsyncSession)

    async def test_get_user_by_email_not_found(self):
        email = "non_existent_email@example.com"
        mocked_user = MagicMock()
        mocked_user.scalar_one_or_none.return_value = None
        self.session.execute.return_value = mocked_user
        result = await get_user_by_email(email, self.session)
        self.assertIsNone(result)

    async def test_get_user_by_email_found(self):
        email = "email@example.com"
        mocked_user = MagicMock()
        mocked_user.scalar_one_or_none.return_value = email
        self.session.execute.return_value = mocked_user
        result = await get_user_by_email(email, self.session)
        self.assertEqual(result, email)

    async def test_create_user(self):
        body = UserSchema(
            username="test_user", email="email@example.com", password="qwerty"
        )
        result = await create_user(body, self.session)
        self.assertIsInstance(result, User)
        self.assertEqual(result.username, body.username)
        self.assertEqual(result.email, body.email)
        self.assertEqual(result.password, body.password)

    @patch("src.repository.users.Gravatar")
    async def test_create_user_with_gravatar(self, mock_gravatar):
        body = UserSchema(
            username="test_user", email="email@example.com", password="qwerty"
        )
        mock_gravatar_instance = MagicMock()
        mock_gravatar_instance.get_image.return_value = "http://example.com/avatar.png"
        mock_gravatar.return_value = mock_gravatar_instance
        result = await create_user(body, self.session)

        mock_gravatar.assert_called_once_with(body.email)
        mock_gravatar_instance.get_image.assert_called_once()

        self.session.add.assert_called_once()
        self.session.commit.assert_awaited_once()
        self.session.refresh.assert_awaited_once()

        self.assertIsInstance(result, User)
        self.assertEqual(result.email, body.email)
        self.assertEqual(result.username, body.username)
        self.assertEqual(result.avatar, "http://example.com/avatar.png")

    @patch("src.repository.users.Gravatar")
    async def test_create_user_without_gravatar(self, mock_gravatar):
        body = UserSchema(
            username="test_user", email="email@example.com", password="qwerty"
        )
        mock_gravatar_instance = MagicMock()
        mock_gravatar_instance.get_image.side_effect = Exception("Gravatar error")
        mock_gravatar.return_value = mock_gravatar_instance
        result = await create_user(body, self.session)

        mock_gravatar.assert_called_once_with(body.email)
        mock_gravatar_instance.get_image.assert_called_once()

        self.session.add.assert_called_once()
        self.session.commit.assert_awaited_once()
        self.session.refresh.assert_awaited_once()

        self.assertIsInstance(result, User)
        self.assertEqual(result.email, body.email)
        self.assertEqual(result.username, body.username)
        self.assertIsNone(result.avatar)

    @patch("src.repository.users.get_user_by_email")
    async def test_confirmed_email(self, mock_get_user_by_email):
        email = "email@example.com"
        mock_user = AsyncMock()
        mock_user.confirmed = False
        mock_get_user_by_email.return_value = mock_user
        await confirmed_email(email, self.session)
        mock_get_user_by_email.assert_awaited_once_with(email, self.session)
        self.assertTrue(mock_user.confirmed)
        self.session.commit.assert_awaited_once()

    @patch("src.repository.users.get_user_by_email")
    async def test_update_avatar_url(self, mock_get_user_by_email):
        email = "email@example.com"
        avatar = "http://example.com/avatar.png"
        mock_user = AsyncMock()
        mock_user.avatar = None
        mock_get_user_by_email.return_value = mock_user
        result = await update_avatar_url(email, avatar, self.session)
        mock_get_user_by_email.assert_awaited_once_with(email, self.session)
        self.assertEqual(result.avatar, avatar)
        self.session.commit.assert_awaited_once()
        self.session.refresh.assert_awaited_once_with(mock_user)

    @patch("src.repository.users.get_user_by_email")
    async def test_update_user_password(self, mock_get_user_by_email):
        user = User(
            id=1,
            username="test_user",
            email="email@example.com",
            password="qwerty",
            confirmed=True,
        )
        new_password = "new_pass"
        hashed_password = CryptContext(schemes=["bcrypt"], deprecated="auto").hash(
            new_password
        )
        mock_user = AsyncMock()
        mock_user.password = user.password
        mock_get_user_by_email.return_value = mock_user
        result = await update_user_password(user.email, new_password, self.session)
        mock_get_user_by_email.assert_awaited_once_with(user.email, self.session)

        bcrypt_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        self.assertTrue(bcrypt_context.verify(new_password, result.password))

        self.assertIsNotNone(result.updated_at)
        self.assertTrue(isinstance(result.updated_at, datetime))
        self.session.commit.assert_awaited_once()
        self.session.refresh.assert_awaited_once_with(mock_user)
