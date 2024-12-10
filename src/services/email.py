from pathlib import Path

from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
from fastapi_mail.errors import ConnectionErrors
from pydantic import EmailStr

from src.conf.config import config
from src.services.auth import auth_service

conf = ConnectionConfig(
    MAIL_USERNAME=config.MAIL_USERNAME,
    MAIL_PASSWORD=config.MAIL_PASSWORD,
    MAIL_FROM=config.MAIL_FROM,
    MAIL_PORT=config.MAIL_PORT,
    MAIL_SERVER=config.MAIL_SERVER,
    MAIL_FROM_NAME="ADDRESSBOOK Systems",
    MAIL_STARTTLS=False,
    MAIL_SSL_TLS=True,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True,
    TEMPLATE_FOLDER=Path(__file__).parent / "templates",
)


async def send_email(email: EmailStr, username: str, host: str):
    """
    Sends an email to the user for email verification.

    Args:
        email (EmailStr): The recipient's email address.
        username (str): The username of the recipient.
        host (str): The base URL of the application, used in the verification link.

    Raises:
        ConnectionErrors: If there is a connection issue while sending the email.

    Side Effects:
        Sends an email with a verification token to the provided email address.

    Returns:
        None
    """
    try:
        token_verification = auth_service.create_email_token({"sub": email})
        message = MessageSchema(
            subject="Confirm your email ",
            recipients=[email],
            template_body={
                "host": host,
                "username": username,
                "token": token_verification,
            },
            subtype=MessageType.html,
        )
        fm = FastMail(conf)
        await fm.send_message(message, template_name="verify_email.html")
    except ConnectionErrors as err:
        print(err)


async def send_email_password(email: EmailStr, username: str, reset_link, host: str):
    """
    Sends an email to the user with a password reset link.

    Args:
        email (EmailStr): The recipient's email address.
        username (str): The username of the recipient.
        reset_link (str): The password reset link to include in the email.
        host (str): The base URL of the application, used for generating the reset link.

    Raises:
        ConnectionErrors: If there is an issue with the connection while attempting to send the email.

    Side Effects:
        Sends an email to the provided email address with a password reset link. The email includes a
        link that allows the user to reset their password.

    Returns:
        None: This function does not return a value.
    """
    try:
        token_verification = (
            reset_link  # auth_service.create_email_token_with_redis({"sub": email})
        )
        message = MessageSchema(
            subject="Confirm reset of password ",
            recipients=[email],
            template_body={
                "host": host,
                "username": username,
                "token": token_verification,
            },
            subtype=MessageType.html,
        )
        fm = FastMail(conf)
        await fm.send_message(message, template_name="reset_password.html")
    except ConnectionErrors as err:
        print(err)
