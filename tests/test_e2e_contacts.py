from datetime import date, timedelta, datetime
from unittest.mock import Mock, patch, AsyncMock

import pytest

from src.services.auth import auth_service
from src.repository.contacts import adjust_for_weekend

contact = {
    "first_name": "John",
    "last_name": "Snow",
    "email": "email",
    "phone": "123456789",
    "birthday": "2000-04-12",
    "data_add": "",
}


def test_get_contacts(client, get_token, monkeypatch):
    with patch.object(auth_service, "cache") as redis_mock:
        redis_mock.get.return_value = None
        monkeypatch.setattr("fastapi_limiter.FastAPILimiter.redis", AsyncMock())
        monkeypatch.setattr("fastapi_limiter.FastAPILimiter.identifier", AsyncMock())
        monkeypatch.setattr("fastapi_limiter.FastAPILimiter.http_callback", AsyncMock())
        token = get_token
        headers = {"Authorization": f"Bearer {token}"}
        response = client.get("api/contact", headers=headers)
        assert response.status_code == 200, response.text
        data = response.json()
        assert len(data) == 0
        assert data == []


def test_create_contact(client, get_token, monkeypatch):
    with patch.object(auth_service, "cache") as redis_mock:
        redis_mock.get.return_value = None
        monkeypatch.setattr("fastapi_limiter.FastAPILimiter.redis", AsyncMock())
        monkeypatch.setattr("fastapi_limiter.FastAPILimiter.identifier", AsyncMock())
        monkeypatch.setattr("fastapi_limiter.FastAPILimiter.http_callback", AsyncMock())
        token = get_token
        headers = {"Authorization": f"Bearer {token}"}
        response = client.post("api/contact", headers=headers, json=contact)
        assert response.status_code == 201, response.text
        data = response.json()
        assert "id" in data
        assert data["first_name"] == contact["first_name"]
        assert data["last_name"] == contact["last_name"]
        assert data["email"] == contact["email"]
        assert data["phone"] == contact["phone"]
        assert data["birthday"] == contact["birthday"]
        assert data["data_add"] == contact["data_add"]


def test_get_contact_success(client, get_token, monkeypatch):
    with patch.object(auth_service, "cache") as redis_mock:
        redis_mock.get.return_value = None
        monkeypatch.setattr("fastapi_limiter.FastAPILimiter.redis", AsyncMock())
        monkeypatch.setattr("fastapi_limiter.FastAPILimiter.identifier", AsyncMock())
        monkeypatch.setattr("fastapi_limiter.FastAPILimiter.http_callback", AsyncMock())
        token = get_token
        headers = {"Authorization": f"Bearer {token}"}
        response = client.get("api/contact/1", headers=headers)
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["id"] == 1
        assert data["first_name"] == contact["first_name"]
        assert data["last_name"] == contact["last_name"]
        assert data["email"] == contact["email"]


def test_get_contact_not_found(client, get_token, monkeypatch):
    with patch.object(auth_service, "cache") as redis_mock:
        redis_mock.get.return_value = None
        monkeypatch.setattr("fastapi_limiter.FastAPILimiter.redis", AsyncMock())
        monkeypatch.setattr("fastapi_limiter.FastAPILimiter.identifier", AsyncMock())
        monkeypatch.setattr("fastapi_limiter.FastAPILimiter.http_callback", AsyncMock())
        token = get_token
        headers = {"Authorization": f"Bearer {token}"}
        response = client.get("api/contact/2", headers=headers)
        assert response.status_code == 404
        assert response.json() == {"detail": "NOT FOUND"}


def test_update_contact(client, get_token, monkeypatch):
    with patch.object(auth_service, "cache") as redis_mock:
        redis_mock.get.return_value = None
        monkeypatch.setattr("fastapi_limiter.FastAPILimiter.redis", AsyncMock())
        monkeypatch.setattr("fastapi_limiter.FastAPILimiter.identifier", AsyncMock())
        monkeypatch.setattr("fastapi_limiter.FastAPILimiter.http_callback", AsyncMock())
        token = get_token
        headers = {"Authorization": f"Bearer {token}"}
        contact["first_name"] = "Jane"
        contact["birthday"] = (date.today() + timedelta(days=4)).strftime("%Y-%m-%d")
        response = client.put("api/contact/1", headers=headers, json=contact)
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["id"] == 1
        assert data["first_name"] == contact["first_name"]


def test_update_contact_not_found(client, get_token, monkeypatch):
    with patch.object(auth_service, "cache") as redis_mock:
        redis_mock.get.return_value = None
        monkeypatch.setattr("fastapi_limiter.FastAPILimiter.redis", AsyncMock())
        monkeypatch.setattr("fastapi_limiter.FastAPILimiter.identifier", AsyncMock())
        monkeypatch.setattr("fastapi_limiter.FastAPILimiter.http_callback", AsyncMock())
        token = get_token
        headers = {"Authorization": f"Bearer {token}"}
        response = client.put("api/contact/2", headers=headers, json=contact)
        assert response.status_code == 404
        assert response.json() == {"detail": "NOT FOUND"}


def test_search_contacts_not_found(client, get_token, monkeypatch):
    with patch.object(auth_service, "cache") as redis_mock:
        redis_mock.get.return_value = None
        monkeypatch.setattr("fastapi_limiter.FastAPILimiter.redis", AsyncMock())
        monkeypatch.setattr("fastapi_limiter.FastAPILimiter.identifier", AsyncMock())
        monkeypatch.setattr("fastapi_limiter.FastAPILimiter.http_callback", AsyncMock())
        token = get_token
        headers = {"Authorization": f"Bearer {token}"}
        search_params = {"first_name": "John", "last_name": "Snow", "email": "email"}
        response = client.get(
            "api/contact/search", headers=headers, params=search_params
        )
        assert response.status_code == 404, response.text
        assert response.json() == {"detail": "Contacts not found"}


def test_search_contacts_multiple_param_success(client, get_token, monkeypatch):
    with patch.object(auth_service, "cache") as redis_mock:
        redis_mock.get.return_value = None
        monkeypatch.setattr("fastapi_limiter.FastAPILimiter.redis", AsyncMock())
        monkeypatch.setattr("fastapi_limiter.FastAPILimiter.identifier", AsyncMock())
        monkeypatch.setattr("fastapi_limiter.FastAPILimiter.http_callback", AsyncMock())
        token = get_token
        headers = {"Authorization": f"Bearer {token}"}
        search_params = {"first_name": "Jane", "last_name": "Snow", "email": "email"}
        response = client.get(
            "api/contact/search", headers=headers, params=search_params
        )
        assert response.status_code == 200, response.text
        data = response.json()
        assert data[0]["first_name"] == contact["first_name"]
        assert data[0]["last_name"] == contact["last_name"]
        assert data[0]["email"] == contact["email"]


def test_search_contacts_one_param_success(client, get_token, monkeypatch):
    with patch.object(auth_service, "cache") as redis_mock:
        redis_mock.get.return_value = None
        monkeypatch.setattr("fastapi_limiter.FastAPILimiter.redis", AsyncMock())
        monkeypatch.setattr("fastapi_limiter.FastAPILimiter.identifier", AsyncMock())
        monkeypatch.setattr("fastapi_limiter.FastAPILimiter.http_callback", AsyncMock())
        token = get_token
        headers = {"Authorization": f"Bearer {token}"}
        search_params = {"first_name": "Jane"}
        response = client.get(
            "api/contact/search", headers=headers, params=search_params
        )
        assert response.status_code == 200, response.text
        data = response.json()
        assert data[0]["first_name"] == contact["first_name"]


def test_upcoming_birthdays(client, get_token, monkeypatch):
    with patch.object(auth_service, "cache") as redis_mock:
        redis_mock.get.return_value = None
        monkeypatch.setattr("fastapi_limiter.FastAPILimiter.redis", AsyncMock())
        monkeypatch.setattr("fastapi_limiter.FastAPILimiter.identifier", AsyncMock())
        monkeypatch.setattr("fastapi_limiter.FastAPILimiter.http_callback", AsyncMock())
        token = get_token
        headers = {"Authorization": f"Bearer {token}"}
        response = client.get("api/contact/upcoming_birthdays", headers=headers)
        assert response.status_code == 200, response.text
        data = response.json()
        date_object = (
            datetime.strptime(contact["birthday"], "%Y-%m-%d")
            .date()
            .replace(year=date.today().year)
        )
        expected = adjust_for_weekend(date_object).strftime("%d.%m.%Y")
        assert data[0]["congratulation_date"] == expected


def test_upcoming_birthdays_not_found(client, get_token, monkeypatch):
    with patch.object(auth_service, "cache") as redis_mock:
        redis_mock.get.return_value = None
        monkeypatch.setattr("fastapi_limiter.FastAPILimiter.redis", AsyncMock())
        monkeypatch.setattr("fastapi_limiter.FastAPILimiter.identifier", AsyncMock())
        monkeypatch.setattr("fastapi_limiter.FastAPILimiter.http_callback", AsyncMock())
        token = get_token
        headers = {"Authorization": f"Bearer {token}"}
        contact["birthday"] = (date.today() + timedelta(days=-2)).strftime("%Y-%m-%d")
        response = client.put("api/contact/1", headers=headers, json=contact)
        assert response.status_code == 200, response.text
        response = client.get("api/contact/upcoming_birthdays", headers=headers)
        assert response.status_code == 200, response.text
        data = response.json()
        expected = []
        assert data == expected


def test_get_delete_contact_success(client, get_token, monkeypatch):
    with patch.object(auth_service, "cache") as redis_mock:
        redis_mock.get.return_value = None
        monkeypatch.setattr("fastapi_limiter.FastAPILimiter.redis", AsyncMock())
        monkeypatch.setattr("fastapi_limiter.FastAPILimiter.identifier", AsyncMock())
        monkeypatch.setattr("fastapi_limiter.FastAPILimiter.http_callback", AsyncMock())
        token = get_token
        headers = {"Authorization": f"Bearer {token}"}
        response = client.delete("api/contact/1", headers=headers)
        assert response.status_code == 204, response.text
