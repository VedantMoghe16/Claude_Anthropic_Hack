"""
Adhikar-Aina | bot.py

Telegram bot — fully API-driven (no direct SQLite access).
All citizen lookups and data writes go through the backend REST API.

Features:
- Send 12-digit Aadhaar → auto-links Telegram ID → matched schemes → PDF certificate
- /language  — pick preferred language
- /start     — welcome
- /help      — usage guide
- /demo      — show sample Aadhaar numbers
- /myid      — show your Telegram chat ID
"""

from __future__ import annotations

import logging
import os
import sys
import tempfile
from pathlib import Path
from typing import Optional

import requests

sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env", override=False)

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application, CallbackQueryHandler, CommandHandler,
    ContextTypes, MessageHandler, filters,
)

logging.basicConfig(
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", os.getenv("TELEGRAM_BOT_TOKEN", ""))
BACKEND_URL    = os.getenv("BACKEND_URL", "http://localhost:8000").rstrip("/")
SARVAM_API_KEY = os.getenv("SARVAM_API_KEY", "")

# ── Language config ───────────────────────────────────────────────────────────

SUPPORTED_LANGS = {
    "en": "English",
    "hi": "हिंदी (Hindi)",
    "bn": "বাংলা (Bengali)",
    "mr": "मराठी (Marathi)",
    "ta": "தமிழ் (Tamil)",
    "te": "తెలుగు (Telugu)",
    "gu": "ગુજરાતી (Gujarati)",
    "kn": "ಕನ್ನಡ (Kannada)",
    "ml": "മലയാളം (Malayalam)",
    "pa": "ਪੰਜਾਬੀ (Punjabi)",
}

_USER_LANG: dict[int, str] = {}


def _get_lang(chat_id: int) -> str:
    return _USER_LANG.get(chat_id, "en")


def _translate(text: str, chat_id: int) -> str:
    lang = _get_lang(chat_id)
    if lang == "en":
        return text
    try:
        from sarvam import translate
        return translate(text, target_lang=lang, source_lang="en")
    except Exception:
        return text


def _lang_keyboard() -> InlineKeyboardMarkup:
    buttons, row = [], []
    for code, label in SUPPORTED_LANGS.items():
        row.append(InlineKeyboardButton(label, callback_data=f"lang:{code}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    return InlineKeyboardMarkup(buttons)


# ── Message templates ─────────────────────────────────────────────────────────

_WELCOME_EN = (
    "Namaste! Welcome to ADHIKAR\n"
    "Aapka Adhikar, Aapki Pehchaan\n\n"
    "I help you discover government welfare schemes you are legally entitled to "
    "and generate an Adhikar Certificate you can show to any official.\n\n"
    "How to use:\n"
    "1. Send your 12-digit Aadhaar number\n"
    "2. Your account is automatically linked\n"
    "3. Receive your certificate as a PDF\n\n"
    "Send /language to choose your preferred language first."
)

_HELP_EN = (
    "ADHIKAR Bot — Help\n\n"
    "Commands:\n"
    "/start    — Start the bot\n"
    "/language — Choose your language\n"
    "/demo     — Show sample Aadhaar numbers to try\n"
    "/myid     — Show your Telegram chat ID\n"
    "/help     — Show this message\n\n"
    "Usage:\n"
    "Send your 12-digit Aadhaar number (digits only, no spaces).\n"
    "Your Telegram account is automatically linked to your profile.\n"
    "You will receive notifications when new schemes match you.\n\n"
    "Emergency Helplines:\n"
    "National: 1800-11-0001 (Free)\n"
    "Legal Aid: 1800-233-4415 (Free)"
)

_LANG_PROMPT_EN    = "Please choose your preferred language / अपनी भाषा चुनें:"
_INVALID_AADHAAR_EN = (
    "Please send a valid 12-digit Aadhaar number (digits only).\n"
    "Example: 999900001234\n\n"
    "Send /demo to see sample Aadhaar numbers."
)
_NOT_FOUND_EN = (
    "Aadhaar not found in our database.\n\n"
    "Please register at your nearest Jan Seva Kendra (CSC).\n"
    "Apne najdiki Jan Seva Kendra par panjikaran karein."
)
_NO_SCHEMES_EN = (
    "Namaste {name}!\n\n"
    "No government schemes matched your current profile.\n\n"
    "This may change if your income or circumstances change. "
    "Visit your local District Welfare Office for more assistance."
)
_PROCESSING_EN = "Processing Aadhaar {masked}... please wait."
_DEMO_EN = (
    "Demo Aadhaar numbers you can test with:\n\n"
    "{entries}\n\n"
    "Send any of these 12-digit numbers to see their eligible schemes."
)
_MYID_EN = (
    "Your Telegram Chat ID is: {chat_id}\n\n"
    "You are automatically linked when you send your Aadhaar number."
)
_BACKEND_DOWN_EN = (
    "The server is starting up. Please try again in 30 seconds.\n"
    "Server: {url}"
)


# ── Backend API helpers ───────────────────────────────────────────────────────

def _api_get_citizen(aadhar: str) -> Optional[dict]:
    """Returns {found, citizen, schemes} or None on network error."""
    try:
        resp = requests.get(
            f"{BACKEND_URL}/api/citizen/by-aadhaar/{aadhar}",
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        logger.error("Backend GET citizen error: %s", e)
        return None


def _api_link_telegram(citizen_id: str, chat_id: int, username: str) -> None:
    """Auto-link Telegram chat to citizen profile (fire-and-forget)."""
    try:
        requests.post(
            f"{BACKEND_URL}/api/link-telegram",
            json={
                "citizen_id":        citizen_id,
                "telegram_chat_id":  str(chat_id),
                "telegram_username": username or "",
            },
            timeout=10,
        )
    except Exception as e:
        logger.warning("Telegram link error (non-fatal): %s", e)


def _api_demo_citizens() -> list:
    """Fetch demo citizen list from backend."""
    try:
        resp = requests.get(f"{BACKEND_URL}/api/demo-citizens", timeout=10)
        resp.raise_for_status()
        return resp.json().get("citizens", [])
    except Exception:
        return []


# ── Handlers ──────────────────────────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    await update.message.reply_text(_translate(_WELCOME_EN, chat_id))
    await update.message.reply_text(_LANG_PROMPT_EN, reply_markup=_lang_keyboard())


async def cmd_language(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(_LANG_PROMPT_EN, reply_markup=_lang_keyboard())


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    await update.message.reply_text(_translate(_HELP_EN, chat_id))


async def cmd_myid(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    await update.message.reply_text(
        _translate(_MYID_EN.format(chat_id=chat_id), chat_id)
    )


async def cmd_demo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    citizens = _api_demo_citizens()
    if not citizens:
        await update.message.reply_text(_translate(
            "Could not load demo citizens. Try /start and send any 12-digit Aadhaar.", chat_id
        ))
        return
    lines = []
    for c in citizens:
        income = c.get("annual_income", 0)
        try:
            income = f"Rs {int(float(income)):,}"
        except Exception:
            income = str(income)
        lines.append(
            f"  {c['aadhar']}  —  {c['name']}, {c.get('district','')}\n"
            f"     {str(c.get('occupation','')).title()}, {income}, {c.get('caste_category','')}"
        )
    entries = "\n\n".join(lines)
    await update.message.reply_text(_translate(_DEMO_EN.format(entries=entries), chat_id))


async def callback_lang(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    code    = query.data.split(":", 1)[1]
    chat_id = update.effective_chat.id
    _USER_LANG[chat_id] = code
    lang_name  = SUPPORTED_LANGS.get(code, code)
    confirm_en = f"Language set to {lang_name}. Now send your 12-digit Aadhaar number."
    await query.edit_message_text(_translate(confirm_en, chat_id))


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id  = update.effective_chat.id
    username = getattr(update.effective_user, "username", None) or ""
    raw      = (update.message.text or "").strip()
    text     = raw.replace(" ", "").replace("-", "")

    if not text.isdigit() or len(text) != 12:
        await update.message.reply_text(_translate(_INVALID_AADHAAR_EN, chat_id))
        return

    masked = text[:4] + "XXXX" + text[-4:]
    await update.message.reply_text(
        _translate(_PROCESSING_EN.format(masked=masked), chat_id)
    )

    try:
        data = _api_get_citizen(text)

        if data is None:
            # Backend unreachable
            await update.message.reply_text(
                _translate(_BACKEND_DOWN_EN.format(url=BACKEND_URL), chat_id)
            )
            return

        if not data.get("found"):
            await update.message.reply_text(_translate(_NOT_FOUND_EN, chat_id))
            return

        citizen = data["citizen"]
        schemes  = data.get("schemes", [])

        # ── Auto-link Telegram chat ID to this citizen ────────────────────────
        _api_link_telegram(citizen["citizen_id"], chat_id, username)
        logger.info(
            "Auto-linked chat_id=%s → citizen_id=%s (%s)",
            chat_id, citizen["citizen_id"], citizen.get("name"),
        )

        if not schemes:
            await update.message.reply_text(
                _translate(_NO_SCHEMES_EN.format(name=citizen["name"]), chat_id)
            )
            return

        # ── Generate PDF certificate ──────────────────────────────────────────
        from certificate import generate_pdf

        scheme_lines = "\n".join(
            f"  {i}. {s['scheme_name']}" for i, s in enumerate(schemes, 1)
        )
        summary_en = (
            f"Namaste {citizen['name']}!\n\n"
            f"You are eligible for {len(schemes)} government scheme(s):\n"
            f"{scheme_lines}\n\n"
            "Your Aadhaar is now linked to your Adhikar account.\n"
            "You will be notified when new schemes match your profile.\n\n"
            "Your certificate (with legal rights and claim script) is attached below.\n"
            "Agar koi inkaar kare — yeh certificate legal proof hai."
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = generate_pdf(
                citizen, schemes,
                output_path=Path(tmpdir) / "adhikar_certificate.pdf",
                language=_get_lang(chat_id),
            )
            await update.message.reply_text(_translate(summary_en, chat_id))
            with open(pdf_path, "rb") as pdf:
                await update.message.reply_document(
                    document=pdf,
                    filename=f"Adhikar_Certificate_{text[-4:]}.pdf",
                    caption="ADHIKAR Certificate — Your Rights Document",
                )

    except Exception as exc:
        logger.error("Error for Aadhaar %s: %s", text, exc, exc_info=True)
        await update.message.reply_text(
            _translate(
                f"An error occurred. Please try again or contact support.\nError: {exc}",
                chat_id,
            )
        )


# ── Error handler ─────────────────────────────────────────────────────────────

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("Exception while handling update %s", update, exc_info=context.error)
    if isinstance(update, Update) and update.effective_message:
        try:
            await update.effective_message.reply_text(
                f"An internal error occurred: {context.error}"
            )
        except Exception:
            pass


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    if not TELEGRAM_TOKEN:
        raise ValueError(
            "TELEGRAM_TOKEN is not set.\n"
            "Set it as an environment variable or in the .env file."
        )
    logger.info("Backend URL: %s", BACKEND_URL)

    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start",    cmd_start))
    app.add_handler(CommandHandler("language", cmd_language))
    app.add_handler(CommandHandler("help",     cmd_help))
    app.add_handler(CommandHandler("demo",     cmd_demo))
    app.add_handler(CommandHandler("myid",     cmd_myid))
    app.add_handler(CallbackQueryHandler(callback_lang, pattern=r"^lang:"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_error_handler(error_handler)

    logger.info("ADHIKAR Bot started. Ctrl+C to stop.")
    app.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
    )


if __name__ == "__main__":
    main()
