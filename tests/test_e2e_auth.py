from unittest.mock import Mock, AsyncMock, patch, MagicMock

import pytest
from pycparser.ply.yacc import token
from sqlalchemy import select
from fastapi import status

from src.database.models import User
from src.schemas.user import TokenSchema
from src.services.auth import auth_service
from tests.conftest import TestingSessionLocal, test_user, get_token
from src.conf import messages

user_data = {
    "username": "agent007",
    "email": "agent007@gmail.com",
    "password": "12345678",
}


def test_signup(client, monkeypatch):
    mock_send_email = Mock()
    monkeypatch.setattr("src.routes.auth.send_email", mock_send_email)
    response = client.post("api/auth/signup", json=user_data)
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["username"] == user_data["username"]
    assert data["email"] == user_data["email"]
    assert "password" not in data
    assert "avatar" in data


def test_signup_exist_user(client, monkeypatch):
    mock_send_email = Mock()
    monkeypatch.setattr("src.routes.auth.send_email", mock_send_email)
    response = client.post("api/auth/signup", json=user_data)
    assert response.status_code == 409, response.text
    data = response.json()
    assert data["detail"] == messages.ACCOUNT_EXIST


def test_not_confirmed_login(client):
    response = client.post(
        "api/auth/login",
        data={
            "username": user_data.get("email"),
            "password": user_data.get("password"),
        },
    )
    assert response.status_code == 401, response.text
    data = response.json()
    assert data["detail"] == messages.EMAIL_NOT_CONFIRMED


@pytest.mark.asyncio
async def test_login(client):
    async with TestingSessionLocal() as session:
        current_user = await session.execute(
            select(User).where(User.email == user_data.get("email"))
        )
        current_user = current_user.scalar_one_or_none()
        if current_user:
            current_user.confirmed = True
            await session.commit()

    response = client.post(
        "api/auth/login",
        data={
            "username": user_data.get("email"),
            "password": user_data.get("password"),
        },
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert "token_type" in data


def test_wrong_password_login(client):
    response = client.post(
        "api/auth/login",
        data={"username": user_data.get("email"), "password": "password"},
    )
    assert response.status_code == 401, response.text
    data = response.json()
    assert data["detail"] == messages.INVALID_PASSWORD


def test_wrong_email_login(client):
    response = client.post(
        "api/auth/login",
        data={"username": "email", "password": user_data.get("password")},
    )
    assert response.status_code == 401, response.text
    data = response.json()
    assert data["detail"] == messages.INVALID_EMAIL


def test_validation_error_login(client):
    response = client.post(
        "api/auth/login", data={"password": user_data.get("password")}
    )
    assert response.status_code == 422, response.text
    data = response.json()
    assert "detail" in data


@pytest.mark.asyncio
async def test_create_refresh_token_valid_user_data():
    refresh_token = await auth_service.create_refresh_token(
        data={"sub": test_user["email"]}
    )
    assert refresh_token is not None


@pytest.mark.asyncio
async def test_refresh_token_successful(client):
    refresh_token = await auth_service.create_refresh_token(
        data={"sub": test_user["email"]}
    )
    async with TestingSessionLocal() as session:
        result = await session.execute(
            select(User).where(User.email == test_user["email"])
        )
        user = result.scalar_one()
        user.refresh_token = refresh_token
        await session.commit()
    response = client.get(
        "/api/auth/refresh_token", headers={"Authorization": f"Bearer {refresh_token}"}
    )

    assert response.status_code == status.HTTP_200_OK
    tokens = TokenSchema(**response.json())
    assert tokens.token_type == "bearer"
    assert isinstance(tokens.access_token, str)
    assert isinstance(tokens.refresh_token, str)

    async with TestingSessionLocal() as session:
        updated_user = await session.execute(
            select(User).where(User.email == test_user["email"])
        )
        updated_user = updated_user.scalar_one()
        assert updated_user.refresh_token == tokens.refresh_token


@pytest.mark.asyncio
async def test_api_response_with_invalid_refresh_token(client):
    invalid_refresh_token = "invalid_token"
    response = client.get(
        "api/auth/refresh_token",
        headers={"Authorization": f"Bearer {invalid_refresh_token}"},
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_confirm_email_success(client, get_token):
    async with TestingSessionLocal() as session:
        result = await session.execute(
            select(User).where(User.email == test_user["email"])
        )
        user = result.scalar_one()
        user.confirmed = False
        await session.commit()
    token = auth_service.create_email_token(data={"sub": test_user["email"]})
    response = client.get(f"api/auth/confirmed_email/{token}")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"message": "Email confirmed"}
    async with TestingSessionLocal() as session:
        result = await session.execute(
            select(User).where(User.email == test_user["email"])
        )
        user = result.scalar_one()
        assert user.confirmed is True


@pytest.mark.asyncio
async def test_confirm_email_already_confirmed(client, get_token):
    async with TestingSessionLocal() as session:
        result = await session.execute(
            select(User).where(User.email == test_user["email"])
        )
        user = result.scalar_one()
        user.confirmed = True
        await session.commit()
    token = auth_service.create_email_token(data={"sub": test_user["email"]})
    response = client.get(f"api/auth/confirmed_email/{token}")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"message": "Your email is already confirmed"}


@pytest.mark.asyncio
async def test_confirm_email_user_not_found(client, get_token):
    non_existing_email = "nonexistinguser@example.com"
    token = auth_service.create_email_token(data={"sub": non_existing_email})
    response = client.get(f"api/auth/confirmed_email/{token}")
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["detail"] == messages.VERIFICATION_ERROR


@pytest.mark.asyncio
async def test_request_email_success(client):
    async with TestingSessionLocal() as session:
        result = await session.execute(
            select(User).where(User.email == test_user["email"])
        )
        user = result.scalar_one()
        user.confirmed = False
        await session.commit()

    with patch("src.routes.auth.send_email", new_callable=AsyncMock) as mock_send_email:
        response = client.post(
            "api/auth/request_email", json={"email": test_user["email"]}
        )
        mock_send_email.assert_awaited_once_with(
            test_user["email"], test_user["username"], "http://testserver/"
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"message": "Check your email for confirmation."}

    async with TestingSessionLocal() as session:
        result = await session.execute(
            select(User).where(User.email == test_user["email"])
        )
        user = result.scalar_one()
        assert user.confirmed is False


@pytest.mark.asyncio
async def test_request_email_already_confirmed(client):
    async with TestingSessionLocal() as session:
        result = await session.execute(
            select(User).where(User.email == test_user["email"])
        )
        user = result.scalar_one()
        user.confirmed = True
        await session.commit()

    with patch("src.routes.auth.send_email", new_callable=AsyncMock) as mock_send_email:
        response = client.post(
            "api/auth/request_email", json={"email": test_user["email"]}
        )
        mock_send_email.assert_not_called()
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"message": "Your email is already confirmed"}


@pytest.mark.asyncio
async def test_password_reset_request_success(client):
    async with TestingSessionLocal() as session:
        current_user = await session.execute(
            select(User).where(User.email == user_data.get("email"))
        )
        current_user = current_user.scalar_one_or_none()
        if current_user:
            current_user.confirmed = True
            await session.commit()
    with patch.object(auth_service, "cache", new_callable=AsyncMock) as mock_redis:
        mock_redis.get.return_value = user_data.get("email")
        response = client.post(
            "api/auth/password-reset-request", params={"email": user_data.get("email")}
        )
        assert response.status_code == 200, response.text
        assert response.json() == {
            "message": "Password reset link has been sent to your email"
        }


@pytest.mark.asyncio
async def test_password_reset_request_user_not_found(client):
    async with TestingSessionLocal() as session:
        current_user = await session.execute(
            select(User).where(User.email == user_data.get("email"))
        )
        current_user = current_user.scalar_one_or_none()
        if current_user:
            current_user.confirmed = True
            await session.commit()
    response = client.post(
        "api/auth/password-reset-request", params={"email": "no_correct@email.com"}
    )
    assert response.status_code == 404, response.text
    assert response.json() == {"detail": messages.USER_NOT_FOUND}


@pytest.mark.asyncio
async def test_reset_password_success(client):
    async with TestingSessionLocal() as session:
        current_user = await session.execute(
            select(User).where(User.email == user_data.get("email"))
        )
        current_user = current_user.scalar_one_or_none()
        if current_user:
            current_user.confirmed = True
            await session.commit()
    token = "mocked-token"
    email = user_data.get("email")
    with patch.object(auth_service, "cache", new_callable=AsyncMock) as mock_redis:
        with patch(
            "src.services.auth.auth_service.verify_email_token_from_redis"
        ) as mock_verify_token:
            mock_redis.get.return_value = email
            mock_verify_token.return_value = email
            response = client.post(
                "api/auth/password-reset",
                params={"token": token, "new_password": "87654321"},
            )
            assert response.status_code == status.HTTP_200_OK, response.text
            assert response.json() == {
                "message": f"Password updated successfully for user {user_data['username']}"
            }


@pytest.mark.asyncio
async def test_reset_password_not_found(client):
    async with TestingSessionLocal() as session:
        current_user = await session.execute(
            select(User).where(User.email == user_data.get("email"))
        )
        current_user = current_user.scalar_one_or_none()
        if current_user:
            current_user.confirmed = True
            await session.commit()
    token = "mocked-token"
    email = user_data.get("email")
    with patch.object(auth_service, "cache", new_callable=AsyncMock) as mock_redis:
        with patch(
            "src.services.auth.auth_service.verify_email_token_from_redis"
        ) as mock_verify_token:
            mock_redis.get.return_value = email
            mock_verify_token.return_value = None
            response = client.post(
                "api/auth/password-reset",
                params={"token": token, "new_password": "87654321"},
            )
            assert response.status_code == 404, response.text
            assert response.json() == {"detail": messages.USER_NOT_FOUND}
