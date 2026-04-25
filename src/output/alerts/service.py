"""
Alert Service
=============
Sends anomaly notifications via:
  1. Desktop popup (plyer) — instant, works on Windows/Mac/Linux
  2. Telegram bot           — push notification to your phone

Setup for Telegram:
  1. Open Telegram and search for @BotFather
  2. Send /newbot and follow the prompts — copy the bot token
  3. Start a chat with your new bot, then visit:
       https://api.telegram.org/bot<TOKEN>/getUpdates
     to find your chat_id
  4. Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in the project root `.env` (see `.env.example`)

Usage:
    from src.output.alerts.service import AlertService
    alerter = AlertService()
    alerter.send({"symbol": "AAPL", "ts": "...", "close": 185.0,
                  "error": 1.23, "threshold": 0.93})
"""

import logging
from src.process.config import (
    DESKTOP_ALERTS,
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID,
)

log = logging.getLogger(__name__)


class AlertService:
    def __init__(self):
        self._telegram_ok = bool(TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID)
        if self._telegram_ok:
            try:
                import telegram   # python-telegram-bot
                self._bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)
                log.info("Telegram alerts enabled.")
            except ImportError:
                log.warning("python-telegram-bot not installed — Telegram alerts disabled.")
                self._telegram_ok = False

        if DESKTOP_ALERTS:
            try:
                from plyer import notification as _n
                self._notify = _n
                log.info("Desktop alerts enabled.")
            except ImportError:
                log.warning("plyer not installed — desktop alerts disabled.")
                self._notify = None
        else:
            self._notify = None

    def send(self, event: dict):
        """Dispatch an anomaly alert through all enabled channels."""
        symbol    = event["symbol"]
        ts        = event["ts"]
        close     = event["close"]
        error     = event["error"]
        threshold = event["threshold"]

        title   = f"Anomaly detected: {symbol}"
        message = (
            f"{ts}\n"
            f"Close: ${close:.2f}\n"
            f"Reconstruction error: {error:.4f} (threshold: {threshold:.4f})"
        )

        self._desktop(title, message)
        self._telegram(title, message)

    # ── Desktop ────────────────────────────────────────────────────────────────

    def _desktop(self, title: str, message: str):
        if self._notify is None:
            return
        try:
            self._notify.notify(
                title=title,
                message=message,
                app_name="Market Anomaly Detector",
                timeout=10,
            )
        except Exception as e:
            log.error(f"Desktop notification failed: {e}")

    # ── Telegram ───────────────────────────────────────────────────────────────

    def _telegram(self, title: str, message: str):
        if not self._telegram_ok:
            return
        try:
            import asyncio
            text = f"*{title}*\n`{message}`"
            asyncio.run(
                self._bot.send_message(
                    chat_id=TELEGRAM_CHAT_ID,
                    text=text,
                    parse_mode="Markdown",
                )
            )
        except Exception as e:
            log.error(f"Telegram alert failed: {e}")
