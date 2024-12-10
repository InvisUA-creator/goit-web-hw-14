from io import BytesIO
from unittest.mock import Mock, patch, AsyncMock, MagicMock

import pytest
from fastapi import status
from fastapi_limiter import FastAPILimiter

from src.services.auth import auth_service
from tests.conftest import test_user


def test_get_me(client, get_token, monkeypatch):
    with patch.object(auth_service, "cache") as redis_mock:
        redis_mock.get.return_value = None
        monkeypatch.setattr("fastapi_limiter.FastAPILimiter.redis", AsyncMock())
        monkeypatch.setattr("fastapi_limiter.FastAPILimiter.identifier", AsyncMock())
        monkeypatch.setattr("fastapi_limiter.FastAPILimiter.http_callback", AsyncMock())
        token = get_token
        headers = {"Authorization": f"Bearer {token}"}
        response = client.get("api/users/me", headers=headers)
        assert response.status_code == 200, response.text


@patch("cloudinary.uploader.upload")
@patch("cloudinary.CloudinaryImage.build_url")
def test_update_avatar_success(
    mock_build_url, mock_upload, client, get_token, monkeypatch
):
    with patch.object(auth_service, "cache") as redis_mock:
        redis_mock.get.return_value = None
        monkeypatch.setattr("fastapi_limiter.FastAPILimiter.redis", AsyncMock())
        monkeypatch.setattr("fastapi_limiter.FastAPILimiter.identifier", AsyncMock())
        monkeypatch.setattr("fastapi_limiter.FastAPILimiter.http_callback", AsyncMock())
        new_avatar = "https://res.cloudinary.com/dn8r8x5zv/image/upload/v1687896850/Web25/agent007@gmail.com"
        mock_build_url.return_value = new_avatar
        mock_upload.return_value = {"version": "1234567890"}
        token = get_token
        headers = {"Authorization": f"Bearer {token}"}
        test_file = BytesIO(b"fake image content")
        test_file.name = "avatar.jpg"
        response = client.patch(
            "/api/users/avatar",
            headers=headers,
            files={"file": ("avatar.jpg", test_file, "image/jpeg")},
        )
        assert response.status_code == status.HTTP_200_OK, response.text
        user_data = response.json()
        assert user_data["avatar"] == new_avatar
