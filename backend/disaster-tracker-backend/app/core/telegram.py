"""Telegram subscriptions: people message the bot /start to get alerts and /stop to leave.

Only TELEGRAM_BOT_TOKEN has to be configured. Subscribed chats live in the
telegram_subscribers table, so adding a recipient never means editing .env.
The listener long-polls Telegram's getUpdates, so it works without a public URL.
"""

import asyncio
import json
import logging

import httpx
import requests
from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert

from app.config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from app.core import history
from db.db import TelegramSubscriberRow

log = logging.getLogger(__name__)
# httpx logs every request URL at INFO, and Telegram URLs contain the bot token.
logging.getLogger("httpx").setLevel(logging.WARNING)

API = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"
LONG_POLL_SECONDS = 25

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


async def _handle(client: httpx.AsyncClient, message: dict | None) -> None:
    if not message or not message.get("text", "").strip():
        return
    # "/start@distrack2_bot extra words" -> "/start"
    command = message["text"].split()[0].split("@")[0].lower()
    reply = await asyncio.to_thread(_reply_to, command, message["chat"])
    if reply:
        await client.post(f"{API}/sendMessage", json={"chat_id": message["chat"]["id"], "text": reply})


async def listen_forever() -> None:
    """Answer /start and /stop for as long as the API runs."""
    offset = None
    async with httpx.AsyncClient(timeout=LONG_POLL_SECONDS + 10) as client:
        while True:
            try:
                params = {"timeout": LONG_POLL_SECONDS, "allowed_updates": json.dumps(["message"])}
                if offset is not None:
                    params["offset"] = offset  # also tells Telegram the earlier updates were handled
                body = (await client.get(f"{API}/getUpdates", params=params)).json()
                if not body.get("ok"):
                    # 409 means another process is polling this bot, or a webhook is set on it.
                    log.warning("Telegram getUpdates failed: %s", body.get("description"))
                    await asyncio.sleep(10)
                    continue
                for update in body["result"]:
                    offset = update["update_id"] + 1
                    await _handle(client, update.get("message"))
            except asyncio.CancelledError:
                raise
            except Exception:
                log.exception("Telegram listener error; retrying in 10 s")
                await asyncio.sleep(10)
