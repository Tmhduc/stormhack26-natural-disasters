"""Optional outbound alerts for responder handoffs."""

import re

import requests

from app.config import (
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID,
    TWILIO_ACCOUNT_SID,
    TWILIO_AUTH_TOKEN,
    TWILIO_FROM_NUMBER,
)


def send_sms(to: str, body: str) -> str:
    """Send one SMS through Twilio and return its message SID."""
    if not all((TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM_NUMBER)):
        raise RuntimeError("SMS alerts are not configured on the backend.")
    if not re.fullmatch(r"\+[1-9]\d{7,14}", to):
        raise ValueError("Use an international phone number, for example +14165551234.")
    if not body.strip() or len(body) > 1600:
        raise ValueError("SMS message must contain 1 to 1600 characters.")
    response = requests.post(
        f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_ACCOUNT_SID}/Messages.json",
        auth=(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN),
        data={"To": to, "From": TWILIO_FROM_NUMBER, "Body": body},
        timeout=15,
    )
    if not response.ok:
        try:
            details = response.json()
            message = details.get("message", "Unknown Twilio error")
            code = details.get("code")
            suffix = f" [{code}]" if code else ""
            raise RuntimeError(f"Twilio rejected the message{suffix}: {message}")
        except ValueError:
            raise RuntimeError(f"Twilio rejected the message ({response.status_code}).")
    return response.json().get("sid", "")


def send_telegram(body: str) -> str:
    """Send one responder brief to the configured Telegram chat."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        raise RuntimeError("Telegram alerts are not configured on the backend.")
    if not body.strip() or len(body) > 4096:
        raise ValueError("Telegram message must contain 1 to 4096 characters.")
    response = requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
        json={"chat_id": TELEGRAM_CHAT_ID, "text": body, "disable_web_page_preview": False},
        timeout=15,
    )
    if not response.ok:
        try:
            message = response.json().get("description", "Unknown Telegram error")
        except ValueError:
            message = f"HTTP {response.status_code}"
        raise RuntimeError(f"Telegram rejected the message: {message}")
    return str(response.json().get("result", {}).get("message_id", ""))
