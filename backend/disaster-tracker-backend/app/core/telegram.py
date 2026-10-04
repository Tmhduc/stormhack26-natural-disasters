"""Telegram subscriptions: people message the bot /start to get alerts and /stop to leave.

Only TELEGRAM_BOT_TOKEN has to be configured. Subscribed chats live in the
telegram_subscribers table, so adding a recipient never means editing .env.

The bot's messages reach the backend one of two ways (see start()):
- Deployed with a public URL (Render sets RENDER_EXTERNAL_URL): Telegram pushes them to a
  webhook. Nothing polls, so overlapping deploys or several instances can't conflict.
- Locally: the backend long-polls getUpdates. Telegram allows one poller per bot, and none
  while a webhook is set, so a local listener steps aside when a deployment owns the bot.
"""

import asyncio
import hashlib
import hmac
import json
import logging

import httpx
import requests
from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert

from app.config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, TELEGRAM_WEBHOOK_BASE_URL
from app.core import history
from db.db import TelegramSubscriberRow

log = logging.getLogger(__name__)
# httpx logs every request URL at INFO, and Telegram URLs contain the bot token.
logging.getLogger("httpx").setLevel(logging.WARNING)

API = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"
LONG_POLL_SECONDS = 25
WEBHOOK_PATH = "/api/flood/alerts/telegram/webhook"  # served by app/routes/flood.py
# Telegram echoes this in a header on every webhook call, proving the call came from Telegram.
# Derived from the bot token, so every instance agrees on it without another setting.
WEBHOOK_SECRET = hashlib.sha256(f"webhook:{TELEGRAM_BOT_TOKEN}".encode()).hexdigest()

SUBSCRIBED = (
    "You're subscribed to DisTrack flood alerts for Vietnam. You'll get a message whenever "
    "a responder shares a flagged location from the dashboard.\n\nSend /stop to unsubscribe."
)
UNSUBSCRIBED = "You've unsubscribed from DisTrack flood alerts. Send /start to subscribe again."
HELP = "Send /start to get DisTrack flood alerts, or /stop to stop them."
NO_DATABASE = "Subscriptions aren't available right now: the DisTrack backend has no database configured."
FAILED = "Something went wrong saving that. Please try again in a minute."

_bot_username: str | None = None


def enabled() -> bool:
    return bool(TELEGRAM_BOT_TOKEN)


def bot_username() -> str | None:
    """The bot's @username (without the @), looked up once from Telegram."""
    global _bot_username
    if _bot_username is None and enabled():
        try:
            me = requests.get(f"{API}/getMe", timeout=10).json()
            if me.get("ok"):
                _bot_username = me["result"]["username"]
        except requests.RequestException:
            log.warning("Could not reach Telegram to look up the bot's username")
    return _bot_username


def subscribe_link() -> str | None:
    username = bot_username()
    return f"https://t.me/{username}" if username else None


def subscribe(chat_id: int, name: str | None) -> None:
    history.ensure_schema()
    stmt = insert(TelegramSubscriberRow).values(chat_id=chat_id, name=name)
    stmt = stmt.on_conflict_do_update(index_elements=[TelegramSubscriberRow.chat_id], set_={"name": stmt.excluded.name})
    with history._engine().begin() as conn:
        conn.execute(stmt)


def unsubscribe(chat_id: int | str) -> None:
    try:
        chat_id = int(chat_id)
    except ValueError:  # an @channel name from TELEGRAM_CHAT_ID; never stored
        return
    history.ensure_schema()
    with history._engine().begin() as conn:
        conn.execute(delete(TelegramSubscriberRow).where(TelegramSubscriberRow.chat_id == chat_id))


def recipients() -> list[int | str]:
    """Every chat an alert goes to: the subscribers, plus TELEGRAM_CHAT_ID if it's set."""
    chats: list[int | str] = []
    if history.enabled():
        try:
            history.ensure_schema()
            with history._engine().connect() as conn:
                chats = list(conn.execute(select(TelegramSubscriberRow.chat_id)).scalars())
        except Exception:
            # Still alert TELEGRAM_CHAT_ID when the database is down.
            log.exception("Could not read Telegram subscribers")
    if TELEGRAM_CHAT_ID and TELEGRAM_CHAT_ID not in {str(c) for c in chats}:
        chats.append(TELEGRAM_CHAT_ID)
    return chats


def _chat_name(chat: dict) -> str | None:
    full_name = " ".join(filter(None, [chat.get("first_name"), chat.get("last_name")]))
    return chat.get("title") or full_name or chat.get("username")


def _reply_to(command: str, chat: dict) -> str | None:
    """What the bot answers. Runs in a worker thread because it touches the database."""
    if command not in ("/start", "/stop"):
        # In groups the bot only answers its own commands, so it doesn't chatter.
        return HELP if chat.get("type") == "private" else None
    if not history.enabled():
        return NO_DATABASE
    try:
        if command == "/start":
            subscribe(chat["id"], _chat_name(chat))
            log.info("Telegram chat %s subscribed", chat["id"])
            return SUBSCRIBED
        unsubscribe(chat["id"])
        log.info("Telegram chat %s unsubscribed", chat["id"])
        return UNSUBSCRIBED
    except Exception:
        log.exception("Could not update Telegram subscription for chat %s", chat["id"])
        return FAILED


async def handle_update(update: dict) -> dict | None:
    """Work out the bot's answer to one update: sendMessage parameters, or None to stay quiet."""
    message = update.get("message")
    if not message or not message.get("text", "").strip():
        return None
    # "/start@distrack2_bot extra words" -> "/start"
    command = message["text"].split()[0].split("@")[0].lower()
    reply = await asyncio.to_thread(_reply_to, command, message["chat"])
    return {"chat_id": message["chat"]["id"], "text": reply} if reply else None


def webhook_url() -> str | None:
    return TELEGRAM_WEBHOOK_BASE_URL.rstrip("/") + WEBHOOK_PATH if TELEGRAM_WEBHOOK_BASE_URL else None


def is_from_telegram(secret_header: str | None) -> bool:
    return hmac.compare_digest(secret_header or "", WEBHOOK_SECRET)


async def register_webhook(url: str) -> None:
    """Have Telegram push the bot's messages to `url`. Safe to repeat, e.g. on every deploy."""
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post(
            f"{API}/setWebhook",
            json={"url": url, "secret_token": WEBHOOK_SECRET, "allowed_updates": ["message"]},
        )
    body = response.json()
    if not body.get("ok"):
        raise RuntimeError(f"Telegram refused the webhook: {body.get('description')}")
    log.info("Telegram webhook set to %s", url)


async def listen_forever() -> None:
    """Long-poll for /start and /stop for as long as the API runs (local development)."""
    offset = None
    async with httpx.AsyncClient(timeout=LONG_POLL_SECONDS + 10) as client:
        while True:
            try:
                params = {"timeout": LONG_POLL_SECONDS, "allowed_updates": json.dumps(["message"])}
                if offset is not None:
                    params["offset"] = offset  # also tells Telegram the earlier updates were handled
                body = (await client.get(f"{API}/getUpdates", params=params)).json()
                if not body.get("ok"):
                    description = body.get("description", "")
                    if "webhook is active" in description:
                        # A deployed backend receives this bot's messages; don't take them over.
                        log.info("Telegram bot is in webhook mode, so a deployed backend answers /start; "
                                 "local listener stopped. Sending alerts still works.")
                        return
                    # Most likely 409: another process is long-polling this bot.
                    log.warning("Telegram getUpdates failed: %s", description)
                    await asyncio.sleep(30)
                    continue
                for update in body["result"]:
                    offset = update["update_id"] + 1
                    reply = await handle_update(update)
                    if reply:
                        await client.post(f"{API}/sendMessage", json=reply)
            except asyncio.CancelledError:
                raise
            except Exception:
                log.exception("Telegram listener error; retrying in 10 s")
                await asyncio.sleep(10)


async def start() -> asyncio.Task | None:
    """Begin answering /start and /stop. Returns the long-polling task to cancel at shutdown, if any."""
    url = webhook_url()
    if url is None:
        return asyncio.create_task(listen_forever())
    try:
        await register_webhook(url)
    except Exception:
        log.exception("Could not register the Telegram webhook; /start and /stop won't be answered")
    return None
